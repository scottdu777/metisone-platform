from metisone_ai_platform.semantic_edit.cube_yaml import (
    CubeSemanticLayerEditor,
    CubeYamlRepository,
)


def test_cube_yaml_editor_creates_modifies_and_deletes_measure(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    payment = cube_dir / "payment.yml"
    payment.write_text(
        "\n".join(
            [
                "cube: payment",
                "sql_table: public.payment",
                "measures:",
                "  - name: count",
                "    type: count",
                "dimensions:",
                "  - name: id",
                "    sql: payment_id",
                "    type: number",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))

    created = editor.create_measure(
        "payment",
        name="revenue",
        sql="amount",
        measure_type="sum",
    )
    modified = editor.modify_measure("payment", "revenue", title="Revenue")
    deleted = editor.delete_measure("payment", "revenue")

    text = payment.read_text(encoding="utf-8")
    assert created.success is True
    assert modified.success is True
    assert deleted.success is True
    assert "revenue" not in text
    assert "count" in text


def test_cube_yaml_editor_creates_dimension_and_join(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    rental = cube_dir / "rental.yml"
    rental.write_text(
        "\n".join(
            [
                "cube: rental",
                "sql_table: public.rental",
                "measures:",
                "dimensions:",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))

    editor.create_dimension(
        "rental",
        name="rental_date",
        sql="rental_date",
        dimension_type="time",
    )
    editor.create_join(
        "rental",
        name="customer",
        sql="{CUBE}.customer_id = {customer}.customer_id",
        relationship="many_to_one",
    )

    text = rental.read_text(encoding="utf-8")
    assert "rental_date" in text
    assert "customer" in text
    assert "many_to_one" in text


def test_cube_yaml_editor_qualifies_dimension_sql_with_cube_reference(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    actor = cube_dir / "actor.yml"
    actor.write_text(
        "\n".join(
            [
                "cube: actor",
                "sql_table: public.actor",
                "measures:",
                "dimensions:",
                "  - name: first_name",
                "    sql: first_name",
                "    type: string",
                "  - name: last_name",
                "    sql: last_name",
                "    type: string",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))
    editor.create_dimension(
        "actor",
        name="full_name",
        sql="CONCAT(${actor.first_name}, ' ', ${actor.last_name})",
        dimension_type="string",
    )

    document = CubeYamlRepository(cube_dir).read(actor)
    full_name = next(item for item in document.data["dimensions"] if item["name"] == "full_name")

    assert full_name["sql"] == "CONCAT({CUBE}.first_name, ' ', {CUBE}.last_name)"


def test_cube_yaml_editor_qualifies_known_bare_dimension_columns(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    actor = cube_dir / "actor.yml"
    actor.write_text(
        "\n".join(
            [
                "cube: actor",
                "sql_table: public.actor",
                "measures:",
                "dimensions:",
                "  - name: first_name",
                "    sql: first_name",
                "    type: string",
                "  - name: last_name",
                "    sql: last_name",
                "    type: string",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))
    editor.create_dimension(
        "actor",
        name="full_name",
        sql="first_name || ' ' || last_name",
        dimension_type="string",
    )

    document = CubeYamlRepository(cube_dir).read(actor)
    full_name = next(item for item in document.data["dimensions"] if item["name"] == "full_name")

    assert full_name["sql"] == "{CUBE}.first_name || ' ' || {CUBE}.last_name"


def test_cube_yaml_editor_updates_nested_cubes_list_model(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    payment = cube_dir / "payment.yml"
    payment.write_text(
        "\n".join(
            [
                "cubes:",
                "- name: payment",
                "  sql_table: public.payment",
                "  dimensions:",
                "  - name: payment_id",
                "    sql: payment_id",
                "    type: number",
                "  measures:",
                "  - name: count",
                "    type: count",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))
    editor.create_measure(
        "payment",
        name="revenue",
        sql="amount",
        measure_type="sum",
        title="Revenue",
    )

    document = CubeYamlRepository(cube_dir).read(payment)

    assert "measures" not in document.data
    assert document.data["cubes"][0]["measures"][-1] == {
        "name": "revenue",
        "sql": "amount",
        "type": "sum",
        "title": "Revenue",
    }


def test_cube_yaml_editor_creates_pre_aggregation(tmp_path) -> None:
    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    payment = cube_dir / "payment.yml"
    payment.write_text(
        "\n".join(
            [
                "cube: payment",
                "sql_table: public.payment",
                "measures:",
                "  - name: count",
                "    type: count",
                "dimensions:",
                "  - name: payment_date",
                "    sql: payment_date",
                "    type: time",
                "pre_aggregations: null",
                "",
            ]
        ),
        encoding="utf-8",
    )

    editor = CubeSemanticLayerEditor(CubeYamlRepository(cube_dir))
    result = editor.create_pre_aggregation(
        "payment",
        name="pay_by_month",
        measures=["payment.count"],
        time_dimension="payment.payment_date",
        granularity="month",
        partitionGranularity="month",
    )

    document = CubeYamlRepository(cube_dir).read(payment)

    assert result.success is True
    assert document.data["pre_aggregations"] == [
        {
            "name": "pay_by_month",
            "type": "rollup",
            "measures": ["payment.count"],
            "time_dimension": "payment.payment_date",
            "granularity": "month",
            "partition_granularity": "month",
        }
    ]
