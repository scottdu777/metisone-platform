from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from metisone_ai_platform.semantic_edit.cube_yaml.repository import (
    CubeYamlDocument,
    CubeYamlRepository,
)


MemberKind = Literal["measure", "dimension", "join", "pre_aggregation"]


@dataclass(frozen=True)
class SemanticEditResult:
    success: bool
    message: str
    file_path: str
    cube: str
    member_kind: MemberKind
    member_name: str


class CubeSemanticLayerEditor:
    def __init__(self, repository: CubeYamlRepository) -> None:
        self.repository = repository

    def create_measure(
        self,
        cube: str,
        name: str,
        sql: str,
        measure_type: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        return self._create_member(
            cube,
            "measure",
            {"name": name, "sql": sql, "type": measure_type, **extra_fields},
        )

    def modify_measure(
        self,
        cube: str,
        name: str,
        **updates: Any,
    ) -> SemanticEditResult:
        return self._modify_member(cube, "measure", name, updates)

    def delete_measure(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "measure", name)

    def create_dimension(
        self,
        cube: str,
        name: str,
        sql: str,
        dimension_type: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        sql = self._normalize_dimension_sql(cube, sql)
        return self._create_member(
            cube,
            "dimension",
            {"name": name, "sql": sql, "type": dimension_type, **extra_fields},
        )

    def modify_dimension(
        self,
        cube: str,
        name: str,
        **updates: Any,
    ) -> SemanticEditResult:
        if isinstance(updates.get("sql"), str):
            updates["sql"] = self._normalize_dimension_sql(cube, updates["sql"])
        return self._modify_member(cube, "dimension", name, updates)

    def delete_dimension(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "dimension", name)

    def create_join(
        self,
        cube: str,
        name: str,
        sql: str,
        relationship: str,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        return self._create_member(
            cube,
            "join",
            {
                "name": name,
                "sql": sql,
                "relationship": relationship,
                **extra_fields,
            },
        )

    def modify_join(self, cube: str, name: str, **updates: Any) -> SemanticEditResult:
        return self._modify_member(cube, "join", name, updates)

    def delete_join(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "join", name)

    def create_pre_aggregation(
        self,
        cube: str,
        name: str,
        pre_aggregation_type: str = "rollup",
        measures: list[str] | None = None,
        dimensions: list[str] | None = None,
        segments: list[str] | None = None,
        time_dimension: str | None = None,
        granularity: str | None = None,
        **extra_fields: Any,
    ) -> SemanticEditResult:
        payload = self._pre_aggregation_payload(
            name=name,
            pre_aggregation_type=pre_aggregation_type,
            measures=measures,
            dimensions=dimensions,
            segments=segments,
            time_dimension=time_dimension,
            granularity=granularity,
            extra_fields=extra_fields,
        )
        return self._create_member(cube, "pre_aggregation", payload)

    def modify_pre_aggregation(
        self,
        cube: str,
        name: str,
        **updates: Any,
    ) -> SemanticEditResult:
        updates = self._normalize_pre_aggregation_fields(updates)
        return self._modify_member(cube, "pre_aggregation", name, updates)

    def delete_pre_aggregation(self, cube: str, name: str) -> SemanticEditResult:
        return self._delete_member(cube, "pre_aggregation", name)

    def _create_member(
        self,
        cube: str,
        kind: MemberKind,
        payload: dict[str, Any],
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        name = payload["name"]

        if self._find_index(collection, name) is not None:
            raise ValueError(f"{kind.title()} already exists in {cube}: {name}")

        collection.append(payload)
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} created.", document, cube, kind, name)

    def _modify_member(
        self,
        cube: str,
        kind: MemberKind,
        name: str,
        updates: dict[str, Any],
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        index = self._find_index(collection, name)

        if index is None:
            raise ValueError(f"{kind.title()} not found in {cube}: {name}")

        collection[index].update({key: value for key, value in updates.items() if value is not None})
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} modified.", document, cube, kind, name)

    def _delete_member(
        self,
        cube: str,
        kind: MemberKind,
        name: str,
    ) -> SemanticEditResult:
        document = self.repository.find_by_cube(cube)
        collection = self._collection(document, cube, kind)
        index = self._find_index(collection, name)

        if index is None:
            raise ValueError(f"{kind.title()} not found in {cube}: {name}")

        del collection[index]
        self.repository.save(document)
        return self._result(True, f"{kind.title()} {name} deleted.", document, cube, kind, name)

    def _collection(
        self,
        document: CubeYamlDocument,
        cube: str,
        kind: MemberKind,
    ) -> list[dict[str, Any]]:
        key = self._collection_key(kind)
        target = self._cube_data(document, cube)
        value = target.setdefault(key, [])
        if value is None:
            value = []
            target[key] = value
        if kind == "pre_aggregation" and isinstance(value, dict):
            value = self._pre_aggregations_dict_to_list(value)
            target[key] = value
        if not isinstance(value, list):
            raise ValueError(f"Cube YAML field must be a list: {key}")
        return value

    def _cube_data(self, document: CubeYamlDocument, cube_name: str) -> dict[str, Any]:
        cubes = document.data.get("cubes")
        if isinstance(cubes, list):
            for cube in cubes:
                if isinstance(cube, dict) and cube.get("name") == cube_name:
                    return cube
            raise ValueError(f"Cube not found in YAML document: {cube_name}")

        return document.data

    def _collection_key(self, kind: MemberKind) -> str:
        return {
            "measure": "measures",
            "dimension": "dimensions",
            "join": "joins",
            "pre_aggregation": "pre_aggregations",
        }[kind]

    def _pre_aggregation_payload(
        self,
        *,
        name: str,
        pre_aggregation_type: str,
        measures: list[str] | None,
        dimensions: list[str] | None,
        segments: list[str] | None,
        time_dimension: str | None,
        granularity: str | None,
        extra_fields: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "type": pre_aggregation_type or "rollup",
        }
        if measures:
            payload["measures"] = measures
        if dimensions:
            payload["dimensions"] = dimensions
        if segments:
            payload["segments"] = segments
        if time_dimension:
            payload["time_dimension"] = time_dimension
        if granularity:
            payload["granularity"] = granularity
        payload.update(extra_fields)
        return self._normalize_pre_aggregation_fields(payload)

    def _normalize_pre_aggregation_fields(
        self,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
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
        return {
            key_map.get(str(key), key): value
            for key, value in fields.items()
            if value is not None
        }

    def _pre_aggregations_dict_to_list(
        self,
        value: dict[str, Any],
    ) -> list[dict[str, Any]]:
        definition_keys = {
            "name",
            "type",
            "measures",
            "dimensions",
            "segments",
            "timeDimension",
            "time_dimension",
            "granularity",
        }
        if any(key in value for key in definition_keys):
            return [self._normalize_pre_aggregation_fields(value)]

        normalized = []
        for name, definition in value.items():
            if not isinstance(definition, dict):
                raise ValueError("Cube YAML field must be a list: pre_aggregations")
            normalized.append(
                self._normalize_pre_aggregation_fields({"name": name, **definition})
            )
        return normalized

    def _normalize_dimension_sql(self, cube: str, sql: str) -> str:
        normalized = sql.strip()
        document = self.repository.find_by_cube(cube)
        cube_data = self._cube_data(document, cube)
        known_columns = self._known_current_cube_columns(cube_data)

        normalized = re.sub(
            rf"\$\{{\s*{re.escape(cube)}\.([A-Za-z_][A-Za-z0-9_]*)\s*\}}",
            r"{CUBE}.\1",
            normalized,
        )
        normalized = re.sub(
            r"\$\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}",
            r"{CUBE}.\1",
            normalized,
        )
        normalized = re.sub(
            rf"(?<![\w{{]){re.escape(cube)}\.([A-Za-z_][A-Za-z0-9_]*)(?![\w}}])",
            r"{CUBE}.\1",
            normalized,
        )

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", normalized):
            return f"{{CUBE}}.{normalized}"

        for column in sorted(known_columns, key=len, reverse=True):
            normalized = self._replace_identifier_outside_literals(
                normalized,
                column,
                f"{{CUBE}}.{column}",
            )

        return normalized

    def _known_current_cube_columns(self, cube_data: dict[str, Any]) -> set[str]:
        columns: set[str] = set()
        for key in ("dimensions", "measures"):
            members = cube_data.get(key) or []
            if not isinstance(members, list):
                continue
            for member in members:
                if not isinstance(member, dict):
                    continue
                name = member.get("name")
                if isinstance(name, str):
                    columns.add(name)
                member_sql = member.get("sql")
                if not isinstance(member_sql, str):
                    continue
                match = re.fullmatch(
                    r"(?:\{CUBE\}\.)?([A-Za-z_][A-Za-z0-9_]*)",
                    member_sql.strip(),
                )
                if match:
                    columns.add(match.group(1))
        return columns

    def _replace_identifier_outside_literals(
        self,
        sql: str,
        identifier: str,
        replacement: str,
    ) -> str:
        pieces = re.split(r"('(?:''|[^'])*')", sql)
        pattern = re.compile(
            rf"(?<![\w.}}]){re.escape(identifier)}(?![\w])"
        )
        for index in range(0, len(pieces), 2):
            pieces[index] = pattern.sub(replacement, pieces[index])
        return "".join(pieces)

    def _find_index(
        self,
        collection: list[dict[str, Any]],
        name: str,
    ) -> int | None:
        for index, item in enumerate(collection):
            if item.get("name") == name:
                return index
        return None

    def _result(
        self,
        success: bool,
        message: str,
        document: CubeYamlDocument,
        cube: str,
        kind: MemberKind,
        name: str,
    ) -> SemanticEditResult:
        return SemanticEditResult(
            success=success,
            message=message,
            file_path=str(document.path),
            cube=cube,
            member_kind=kind,
            member_name=name,
        )
