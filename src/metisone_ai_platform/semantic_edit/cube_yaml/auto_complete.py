from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from metisone_ai_platform.semantic_edit.cube_yaml.repository import (
    CubeYamlDocument,
    CubeYamlRepository,
)


@dataclass(frozen=True)
class ForeignKeyMetadata:
    name: str
    columns: tuple[str, ...]
    referenced_schema: str
    referenced_table: str
    referenced_columns: tuple[str, ...]


@dataclass(frozen=True)
class ColumnMetadata:
    name: str
    data_type: str
    udt_name: str


@dataclass(frozen=True)
class TableMetadata:
    schema: str
    name: str
    primary_key: tuple[str, ...] = ()
    unique_keys: tuple[tuple[str, ...], ...] = ()
    foreign_keys: tuple[ForeignKeyMetadata, ...] = ()
    columns: tuple[ColumnMetadata, ...] = ()


@dataclass(frozen=True)
class SchemaMetadata:
    tables: tuple[TableMetadata, ...]


@dataclass(frozen=True)
class AutoCompleteChange:
    cube: str
    kind: str
    name: str
    action: str


@dataclass(frozen=True)
class AutoCompleteReport:
    applied: bool
    complete: bool
    changes: tuple[AutoCompleteChange, ...]
    warnings: tuple[str, ...]


class PostgresSchemaInspector:
    """Read PK, unique-key, and FK evidence from PostgreSQL catalogs."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def inspect(self, schemas: list[str] | None = None) -> SchemaMetadata:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                'PostgreSQL inspection requires: pip install ".[postgres]"'
            ) from exc

        selected_schemas = schemas or ["public"]
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(_KEY_SQL, (selected_schemas,))
                key_rows = list(cursor.fetchall())
                cursor.execute(_FOREIGN_KEY_SQL, (selected_schemas,))
                foreign_key_rows = list(cursor.fetchall())
                cursor.execute(_COLUMN_SQL, (selected_schemas,))
                column_rows = list(cursor.fetchall())

        return _to_schema_metadata(key_rows, foreign_key_rows, column_rows)


class CubeYamlAutoCompleter:
    """Enrich Cube-generated YAML using database constraint evidence only."""

    def __init__(self, repository: CubeYamlRepository) -> None:
        self.repository = repository

    def normalize_models(self, *, apply: bool = False) -> AutoCompleteReport:
        documents = self.repository.read_all()
        cubes = self._cube_index(documents)
        changes: list[AutoCompleteChange] = []
        dirty_documents: set[str] = set()

        for cube_name, (document, cube_data) in cubes.items():
            if self._normalize_pre_aggregations(cube_name, cube_data, changes):
                dirty_documents.add(str(document.path))

        if apply:
            for document in documents:
                if str(document.path) in dirty_documents:
                    self.repository.save(document)

        return AutoCompleteReport(
            applied=apply,
            complete=True,
            changes=tuple(changes),
            warnings=(),
        )

    def complete(
        self,
        metadata: SchemaMetadata,
        *,
        apply: bool = False,
        bidirectional_joins: bool = True,
    ) -> AutoCompleteReport:
        documents = self.repository.read_all()
        cubes = self._cube_index(documents)
        tables = {(table.schema, table.name): table for table in metadata.tables}
        cube_tables = {
            cube_name: self._table_ref(cube_data.get("sql_table"))
            for cube_name, (_, cube_data) in cubes.items()
        }
        table_cubes = {
            table_ref: cube_name
            for cube_name, table_ref in cube_tables.items()
            if table_ref is not None
        }
        changes: list[AutoCompleteChange] = []
        warnings: list[str] = []
        dirty_documents: set[str] = set()

        for cube_name, (document, cube_data) in cubes.items():
            if self._normalize_pre_aggregations(cube_name, cube_data, changes):
                dirty_documents.add(str(document.path))
            self._qualify_member_sql(cube_name, cube_data, changes)
            table_ref = cube_tables[cube_name]
            table = tables.get(table_ref) if table_ref else None
            if table is None:
                warnings.append(
                    f"Cube {cube_name} has no matching inspected table: {cube_data.get('sql_table')}"
                )
                continue
            self._complete_primary_key(cube_name, cube_data, table, changes, warnings)
            self._ensure_count(cube_name, cube_data, changes)
            if changes and any(change.cube == cube_name for change in changes):
                dirty_documents.add(str(document.path))

        ambiguous_pairs = self._ambiguous_fk_pairs(metadata)
        for table in metadata.tables:
            source_cube = table_cubes.get((table.schema, table.name))
            if source_cube is None:
                continue
            for foreign_key in table.foreign_keys:
                target_ref = (
                    foreign_key.referenced_schema,
                    foreign_key.referenced_table,
                )
                target_cube = table_cubes.get(target_ref)
                if target_cube is None:
                    warnings.append(
                        f"FK {foreign_key.name} target has no Cube model: "
                        f"{foreign_key.referenced_schema}.{foreign_key.referenced_table}"
                    )
                    continue
                pair = ((table.schema, table.name), target_ref)
                if pair in ambiguous_pairs:
                    warnings.append(
                        f"Multiple foreign keys connect {source_cube} to {target_cube}; "
                        "automatic join naming would be ambiguous."
                    )
                    continue

                source_unique = foreign_key.columns in table.unique_keys
                relationship = "one_to_one" if source_unique else "many_to_one"
                self._ensure_join(
                    cubes,
                    source_cube,
                    target_cube,
                    foreign_key.columns,
                    foreign_key.referenced_columns,
                    relationship,
                    changes,
                    warnings,
                    dirty_documents,
                )
                if bidirectional_joins:
                    reverse_relationship = "one_to_one" if source_unique else "one_to_many"
                    self._ensure_join(
                        cubes,
                        target_cube,
                        source_cube,
                        foreign_key.referenced_columns,
                        foreign_key.columns,
                        reverse_relationship,
                        changes,
                        warnings,
                        dirty_documents,
                    )

        if apply:
            for document in documents:
                if str(document.path) in dirty_documents:
                    self.repository.save(document)

        return AutoCompleteReport(
            applied=apply,
            complete=not warnings,
            changes=tuple(changes),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def _cube_index(
        self,
        documents: list[CubeYamlDocument],
    ) -> dict[str, tuple[CubeYamlDocument, dict[str, Any]]]:
        result: dict[str, tuple[CubeYamlDocument, dict[str, Any]]] = {}
        for document in documents:
            items = document.data.get("cubes")
            if isinstance(items, list):
                for cube in items:
                    if isinstance(cube, dict) and isinstance(cube.get("name"), str):
                        result[cube["name"]] = (document, cube)
                continue
            name = document.data.get("cube") or document.data.get("name")
            if isinstance(name, str):
                result[name] = (document, document.data)
        return result

    def _table_ref(self, sql_table: Any) -> tuple[str, str] | None:
        if not isinstance(sql_table, str):
            return None
        parts = [part.strip().strip('"') for part in sql_table.split(".")]
        if len(parts) == 1:
            return ("public", parts[0])
        if len(parts) == 2:
            return (parts[0], parts[1])
        return None

    def _complete_primary_key(
        self,
        cube_name: str,
        cube: dict[str, Any],
        table: TableMetadata,
        changes: list[AutoCompleteChange],
        warnings: list[str],
    ) -> None:
        if not table.primary_key:
            warnings.append(f"Table {table.schema}.{table.name} has no primary key.")
            return
        dimensions = cube.setdefault("dimensions", [])
        if dimensions is None:
            dimensions = []
            cube["dimensions"] = dimensions
        if not isinstance(dimensions, list):
            warnings.append(f"Cube {cube_name} dimensions is not a list.")
            return
        if any(
            isinstance(item, dict) and item.get("primary_key") is True
            for item in dimensions
        ):
            return
        for column in table.primary_key:
            dimension = next(
                (
                    item
                    for item in dimensions
                    if isinstance(item, dict) and self._dimension_column(item) == column
                ),
                None,
            )
            if dimension is None:
                column_metadata = next(
                    (item for item in table.columns if item.name == column),
                    None,
                )
                if column_metadata is None:
                    warnings.append(
                        f"Cube {cube_name} has no dimension or type metadata for "
                        f"primary-key column {column}."
                    )
                    continue
                dimension = {
                    "name": column,
                    "sql": f"{{CUBE}}.{column}",
                    "type": self._cube_type(column_metadata),
                    "primary_key": True,
                    "public": True,
                }
                dimensions.append(dimension)
                changes.append(
                    AutoCompleteChange(cube_name, "dimension", column, "create_primary_key")
                )
                continue
            if dimension.get("primary_key") is not True:
                dimension["primary_key"] = True
                changes.append(AutoCompleteChange(cube_name, "dimension", str(dimension.get("name")), "set_primary_key"))

    def _qualify_member_sql(
        self,
        cube_name: str,
        cube: dict[str, Any],
        changes: list[AutoCompleteChange],
    ) -> None:
        for kind, key in (("dimension", "dimensions"), ("measure", "measures")):
            members = cube.get(key) or []
            if not isinstance(members, list):
                continue
            for member in members:
                if not isinstance(member, dict):
                    continue
                sql = member.get("sql")
                if not isinstance(sql, str):
                    continue
                column = sql.strip().strip('"')
                if not column.replace("_", "").isalnum():
                    continue
                member["sql"] = f"{{CUBE}}.{column}"
                changes.append(
                    AutoCompleteChange(
                        cube_name,
                        kind,
                        str(member.get("name")),
                        "qualify_sql",
                    )
                )

    def _cube_type(self, column: ColumnMetadata) -> str:
        if column.data_type in {
            "smallint",
            "integer",
            "bigint",
            "decimal",
            "numeric",
            "real",
            "double precision",
        }:
            return "number"
        if column.data_type in {
            "date",
            "time without time zone",
            "time with time zone",
            "timestamp without time zone",
            "timestamp with time zone",
        }:
            return "time"
        if column.data_type == "boolean":
            return "boolean"
        return "string"

    def _dimension_column(self, dimension: dict[str, Any]) -> str | None:
        sql = dimension.get("sql")
        if not isinstance(sql, str):
            return None
        value = sql.strip().replace("{CUBE}.", "").strip('"')
        return value if value.replace("_", "").isalnum() else None

    def _ensure_count(
        self,
        cube_name: str,
        cube: dict[str, Any],
        changes: list[AutoCompleteChange],
    ) -> None:
        measures = cube.setdefault("measures", [])
        if measures is None:
            measures = []
            cube["measures"] = measures
        if not isinstance(measures, list):
            return
        if not any(isinstance(item, dict) and item.get("name") == "count" for item in measures):
            measures.append({"name": "count", "type": "count"})
            changes.append(AutoCompleteChange(cube_name, "measure", "count", "create"))

    def _normalize_pre_aggregations(
        self,
        cube_name: str,
        cube: dict[str, Any],
        changes: list[AutoCompleteChange],
    ) -> bool:
        if "pre_aggregations" not in cube:
            return False

        current = cube["pre_aggregations"]
        if current is None:
            cube["pre_aggregations"] = []
            changes.append(
                AutoCompleteChange(
                    cube_name,
                    "pre_aggregations",
                    "pre_aggregations",
                    "null_to_empty_sequence",
                )
            )
            return True

        normalized = self._pre_aggregations_as_list(current)
        if normalized is None:
            return False

        changed = normalized != current
        if changed:
            cube["pre_aggregations"] = normalized
            changes.append(
                AutoCompleteChange(
                    cube_name,
                    "pre_aggregations",
                    "pre_aggregations",
                    "normalize_js_like_format",
                )
            )
        return changed

    def _pre_aggregations_as_list(self, value: Any) -> list[dict[str, Any]] | None:
        if isinstance(value, list):
            normalized: list[dict[str, Any]] = []
            for item in value:
                if not isinstance(item, dict):
                    return None
                normalized.append(self._normalize_pre_aggregation_item(item))
            return normalized

        if isinstance(value, dict):
            if self._looks_like_pre_aggregation_definition(value):
                return [self._normalize_pre_aggregation_item(value)]
            normalized = []
            for name, definition in value.items():
                if not isinstance(definition, dict):
                    return None
                item = {"name": name, **definition}
                normalized.append(self._normalize_pre_aggregation_item(item))
            return normalized

        return None

    def _looks_like_pre_aggregation_definition(self, value: dict[str, Any]) -> bool:
        return any(
            key in value
            for key in (
                "name",
                "type",
                "measures",
                "dimensions",
                "segments",
                "timeDimension",
                "time_dimension",
                "granularity",
            )
        )

    def _normalize_pre_aggregation_item(self, item: dict[str, Any]) -> dict[str, Any]:
        key_map = {
            "timeDimension": "time_dimension",
            "partitionGranularity": "partition_granularity",
            "refreshKey": "refresh_key",
            "scheduledRefresh": "scheduled_refresh",
            "updateWindow": "update_window",
            "buildRangeStart": "build_range_start",
            "buildRangeEnd": "build_range_end",
            "rollupLambda": "rollup_lambda",
            "useOriginalSqlPreAggregations": "use_original_sql_pre_aggregations",
        }
        normalized = {
            key_map.get(str(key), key): value
            for key, value in item.items()
        }
        if "type" not in normalized and self._looks_like_rollup(normalized):
            ordered = {"name": normalized.get("name"), "type": "rollup"}
            for key, value in normalized.items():
                if key != "name":
                    ordered[key] = value
            return ordered
        return normalized

    def _looks_like_rollup(self, item: dict[str, Any]) -> bool:
        return any(
            key in item
            for key in (
                "measures",
                "dimensions",
                "segments",
                "time_dimension",
                "granularity",
            )
        )

    def _ensure_join(
        self,
        cubes: dict[str, tuple[CubeYamlDocument, dict[str, Any]]],
        source: str,
        target: str,
        source_columns: tuple[str, ...],
        target_columns: tuple[str, ...],
        relationship: str,
        changes: list[AutoCompleteChange],
        warnings: list[str],
        dirty_documents: set[str],
    ) -> None:
        document, cube = cubes[source]
        joins = cube.setdefault("joins", [])
        if joins is None:
            joins = []
            cube["joins"] = joins
        if not isinstance(joins, list):
            warnings.append(f"Cube {source} joins is not a list.")
            return
        sql = " AND ".join(
            f"{{CUBE}}.{left} = {{{target}}}.{right}"
            for left, right in zip(source_columns, target_columns)
        )
        existing = next(
            (item for item in joins if isinstance(item, dict) and item.get("name") == target),
            None,
        )
        expected = {"name": target, "sql": sql, "relationship": relationship}
        if existing is None:
            joins.append(expected)
            changes.append(AutoCompleteChange(source, "join", target, "create"))
            dirty_documents.add(str(document.path))
        elif existing.get("sql") != sql or existing.get("relationship") != relationship:
            warnings.append(
                f"Cube {source} already has a conflicting join to {target}; kept existing definition."
            )

    def _ambiguous_fk_pairs(
        self,
        metadata: SchemaMetadata,
    ) -> set[tuple[tuple[str, str], tuple[str, str]]]:
        counts: dict[tuple[tuple[str, str], tuple[str, str]], int] = {}
        for table in metadata.tables:
            source = (table.schema, table.name)
            for foreign_key in table.foreign_keys:
                pair = (
                    source,
                    (foreign_key.referenced_schema, foreign_key.referenced_table),
                )
                counts[pair] = counts.get(pair, 0) + 1
        return {pair for pair, count in counts.items() if count > 1}


def _to_schema_metadata(
    key_rows: list[dict[str, Any]],
    foreign_key_rows: list[dict[str, Any]],
    column_rows: list[dict[str, Any]],
) -> SchemaMetadata:
    keys: dict[tuple[str, str, str, str], list[tuple[int, str]]] = {}
    for row in key_rows:
        key = (
            row["table_schema"],
            row["table_name"],
            row["constraint_name"],
            row["constraint_type"],
        )
        keys.setdefault(key, []).append((row["ordinal_position"], row["column_name"]))

    foreign_keys: dict[tuple[str, str, str, str, str], list[tuple[int, str, str]]] = {}
    for row in foreign_key_rows:
        key = (
            row["table_schema"],
            row["table_name"],
            row["constraint_name"],
            row["referenced_table_schema"],
            row["referenced_table_name"],
        )
        foreign_keys.setdefault(key, []).append(
            (row["ordinal_position"], row["column_name"], row["referenced_column_name"])
        )

    table_refs = {(key[0], key[1]) for key in keys}
    table_refs.update((key[0], key[1]) for key in foreign_keys)
    table_refs.update((row["table_schema"], row["table_name"]) for row in column_rows)
    tables: list[TableMetadata] = []
    for schema, table_name in sorted(table_refs):
        primary_key: tuple[str, ...] = ()
        unique_keys: list[tuple[str, ...]] = []
        for key, columns in keys.items():
            if key[0:2] != (schema, table_name):
                continue
            ordered = tuple(column for _, column in sorted(columns))
            if key[3] == "PRIMARY KEY":
                primary_key = ordered
            if key[3] in {"PRIMARY KEY", "UNIQUE"}:
                unique_keys.append(ordered)
        fks: list[ForeignKeyMetadata] = []
        for key, columns in foreign_keys.items():
            if key[0:2] != (schema, table_name):
                continue
            ordered = sorted(columns)
            fks.append(
                ForeignKeyMetadata(
                    name=key[2],
                    columns=tuple(item[1] for item in ordered),
                    referenced_schema=key[3],
                    referenced_table=key[4],
                    referenced_columns=tuple(item[2] for item in ordered),
                )
            )
        columns = tuple(
            ColumnMetadata(
                name=row["column_name"],
                data_type=row["data_type"],
                udt_name=row["udt_name"],
            )
            for row in column_rows
            if (row["table_schema"], row["table_name"]) == (schema, table_name)
        )
        tables.append(
            TableMetadata(
                schema=schema,
                name=table_name,
                primary_key=primary_key,
                unique_keys=tuple(unique_keys),
                foreign_keys=tuple(fks),
                columns=columns,
            )
        )
    return SchemaMetadata(tuple(tables))


_KEY_SQL = """
SELECT tc.table_schema, tc.table_name, tc.constraint_name, tc.constraint_type,
       kcu.column_name, kcu.ordinal_position
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_schema = kcu.constraint_schema
 AND tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = ANY(%s)
  AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
ORDER BY tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position
"""


_FOREIGN_KEY_SQL = """
SELECT fk.table_schema, fk.table_name, fk.constraint_name,
       fk.column_name, fk.ordinal_position,
       pk.table_schema AS referenced_table_schema,
       pk.table_name AS referenced_table_name,
       pk.column_name AS referenced_column_name
FROM information_schema.referential_constraints AS rc
JOIN information_schema.key_column_usage AS fk
  ON rc.constraint_schema = fk.constraint_schema
 AND rc.constraint_name = fk.constraint_name
JOIN information_schema.key_column_usage AS pk
  ON rc.unique_constraint_schema = pk.constraint_schema
 AND rc.unique_constraint_name = pk.constraint_name
 AND fk.position_in_unique_constraint = pk.ordinal_position
WHERE fk.table_schema = ANY(%s)
ORDER BY fk.table_schema, fk.table_name, fk.constraint_name, fk.ordinal_position
"""


_COLUMN_SQL = """
SELECT table_schema, table_name, column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_schema = ANY(%s)
ORDER BY table_schema, table_name, ordinal_position
"""
