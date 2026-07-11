from metisone_ai_platform.semantic_layer.cube_yaml import (
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
