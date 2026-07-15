from metisone_ai_platform.semantic_layer.cube_yaml.auto_complete import (
    ColumnMetadata,
    CubeYamlAutoCompleter,
    ForeignKeyMetadata,
    SchemaMetadata,
    TableMetadata,
)
from metisone_ai_platform.semantic_layer.cube_yaml.repository import CubeYamlRepository
from metisone_ai_platform.semantic_layer.edit_service.app import create_app
from metisone_ai_platform.semantic_layer.edit_service.config import EditServiceConfig


def test_auto_complete_enriches_dvdrental_keys_and_bidirectional_joins(tmp_path) -> None:
    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    _write_cube(cube_dir, "film", ["film_id", "title"])
    _write_cube(cube_dir, "category", ["category_id", "name"])
    _write_cube(cube_dir, "film_category", ["film_id", "category_id"])

    report = CubeYamlAutoCompleter(CubeYamlRepository(cube_dir)).complete(
        _dvdrental_metadata(),
        apply=True,
    )

    repository = CubeYamlRepository(cube_dir)
    film = repository.find_by_cube("film").data["cubes"][0]
    category = repository.find_by_cube("category").data["cubes"][0]
    link = repository.find_by_cube("film_category").data["cubes"][0]

    assert report.complete is True
    assert report.applied is True
    assert _dimension(film, "film_id")["primary_key"] is True
    assert _dimension(film, "film_id")["sql"] == "{CUBE}.film_id"
    assert _dimension(film, "title")["sql"] == "{CUBE}.title"
    assert _dimension(category, "category_id")["primary_key"] is True
    assert _dimension(link, "film_id")["primary_key"] is True
    assert _dimension(link, "category_id")["primary_key"] is True
    assert _join(film, "film_category")["relationship"] == "one_to_many"
    assert _join(category, "film_category")["relationship"] == "one_to_many"
    assert _join(link, "film")["relationship"] == "many_to_one"
    assert _join(link, "category")["relationship"] == "many_to_one"
    assert _measure(film, "count")["type"] == "count"


def test_auto_complete_dry_run_does_not_write_files(tmp_path) -> None:
    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    film_path = _write_cube(cube_dir, "film", ["film_id", "title"])
    before = film_path.read_text(encoding="utf-8")
    metadata = SchemaMetadata(
        (
            TableMetadata(
                schema="public",
                name="film",
                primary_key=("film_id",),
                unique_keys=(("film_id",),),
            ),
        )
    )

    report = CubeYamlAutoCompleter(CubeYamlRepository(cube_dir)).complete(metadata)

    assert report.applied is False
    assert report.changes
    assert film_path.read_text(encoding="utf-8") == before


def test_auto_complete_creates_primary_key_dimension_omitted_by_cube(tmp_path) -> None:
    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    _write_cube(cube_dir, "film", ["title"])
    metadata = SchemaMetadata(
        (
            TableMetadata(
                schema="public",
                name="film",
                primary_key=("film_id",),
                unique_keys=(("film_id",),),
                columns=(ColumnMetadata("film_id", "integer", "int4"),),
            ),
        )
    )

    report = CubeYamlAutoCompleter(CubeYamlRepository(cube_dir)).complete(
        metadata,
        apply=True,
    )

    film = CubeYamlRepository(cube_dir).find_by_cube("film").data["cubes"][0]
    primary_key = _dimension(film, "film_id")
    assert primary_key == {
        "name": "film_id",
        "sql": "{CUBE}.film_id",
        "type": "number",
        "primary_key": True,
        "public": True,
    }
    assert any(change.action == "create_primary_key" for change in report.changes)


def test_auto_complete_qualifies_measure_columns_for_joined_queries(tmp_path) -> None:
    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    path = _write_cube(cube_dir, "film_actor", ["actor_id", "film_id"])
    document = CubeYamlRepository(cube_dir).read(path)
    document.data["cubes"][0]["measures"] = [
        {"name": "actors_count", "sql": "actor_id", "type": "count_distinct"}
    ]
    CubeYamlRepository(cube_dir).save(document)
    metadata = SchemaMetadata(
        (
            TableMetadata(
                schema="public",
                name="film_actor",
                primary_key=("actor_id", "film_id"),
                unique_keys=(("actor_id", "film_id"),),
            ),
        )
    )

    CubeYamlAutoCompleter(CubeYamlRepository(cube_dir)).complete(metadata, apply=True)

    cube = CubeYamlRepository(cube_dir).find_by_cube("film_actor").data["cubes"][0]
    assert _measure(cube, "actors_count")["sql"] == "{CUBE}.actor_id"


def test_auto_complete_reports_ambiguous_multiple_foreign_keys(tmp_path) -> None:
    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    _write_cube(cube_dir, "film", ["film_id"])
    _write_cube(cube_dir, "category", ["category_id", "backup_category_id"])
    metadata = SchemaMetadata(
        (
            TableMetadata(
                schema="public",
                name="film",
                primary_key=("film_id",),
                unique_keys=(("film_id",),),
            ),
            TableMetadata(
                schema="public",
                name="category",
                primary_key=("category_id",),
                unique_keys=(("category_id",),),
                foreign_keys=(
                    ForeignKeyMetadata("fk_primary", ("category_id",), "public", "film", ("film_id",)),
                    ForeignKeyMetadata("fk_backup", ("backup_category_id",), "public", "film", ("film_id",)),
                ),
            ),
        )
    )

    report = CubeYamlAutoCompleter(CubeYamlRepository(cube_dir)).complete(metadata)

    assert report.complete is False
    assert any("Multiple foreign keys" in warning for warning in report.warnings)


def test_auto_complete_endpoint_requires_postgres_dsn(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cubes"
    cube_dir.mkdir()
    app = create_app(EditServiceConfig(cube_model_dir=cube_dir))

    response = TestClient(app).post("/v1/auto-complete", json={})

    assert response.status_code == 400
    assert "METISONE_POSTGRES_DSN" in response.json()["detail"]


def _dvdrental_metadata() -> SchemaMetadata:
    return SchemaMetadata(
        (
            TableMetadata("public", "film", ("film_id",), (("film_id",),)),
            TableMetadata("public", "category", ("category_id",), (("category_id",),)),
            TableMetadata(
                "public",
                "film_category",
                ("film_id", "category_id"),
                (("film_id", "category_id"),),
                (
                    ForeignKeyMetadata("fk_film", ("film_id",), "public", "film", ("film_id",)),
                    ForeignKeyMetadata("fk_category", ("category_id",), "public", "category", ("category_id",)),
                ),
            ),
        )
    )


def _write_cube(cube_dir, name, dimensions):
    path = cube_dir / f"{name}.yml"
    lines = ["cubes:", f"  - name: {name}", f"    sql_table: public.{name}", "    joins: []", "    dimensions:"]
    for dimension in dimensions:
        lines.extend(
            [
                f"      - name: {dimension}",
                f"        sql: {dimension}",
                "        type: number" if dimension.endswith("_id") else "        type: string",
            ]
        )
    lines.extend(["    measures: []", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _dimension(cube, name):
    return next(item for item in cube["dimensions"] if item["name"] == name)


def _join(cube, name):
    return next(item for item in cube["joins"] if item["name"] == name)


def _measure(cube, name):
    return next(item for item in cube["measures"] if item["name"] == name)
