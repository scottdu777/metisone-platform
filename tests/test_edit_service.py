from metisone_ai_platform.semantic_layer.edit_service.app import create_app
from metisone_ai_platform.semantic_layer.edit_service.config import EditServiceConfig


def test_edit_service_crud_and_auth(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    (cube_dir / "payment.yml").write_text(
        "\n".join(
            [
                "cube: payment",
                "sql_table: public.payment",
                "measures:",
                "dimensions:",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app(
        EditServiceConfig(
            cube_model_dir=cube_dir,
            api_token="secret",
        )
    )
    client = TestClient(app)

    unauthorized = client.get("/v1/cubes")
    assert unauthorized.status_code == 401

    headers = {"Authorization": "Bearer secret"}
    listed = client.get("/v1/cubes", headers=headers)
    created = client.post(
        "/v1/cubes/payment/measures",
        headers=headers,
        json={
            "name": "revenue",
            "sql": "amount",
            "type": "sum",
            "extra_fields": {"title": "Revenue"},
        },
    )
    measures = client.get("/v1/cubes/payment/measures", headers=headers)
    modified = client.patch(
        "/v1/cubes/payment/measures/revenue",
        headers=headers,
        json={"fields": {"description": "Total revenue"}},
    )
    deleted = client.delete("/v1/cubes/payment/measures/revenue", headers=headers)

    assert listed.status_code == 200
    assert listed.json()[0]["cube"] == "payment"
    assert created.status_code == 200
    assert created.json()["success"] is True
    assert measures.json()[0]["name"] == "revenue"
    assert modified.json()["message"] == "Measure revenue modified."
    assert deleted.json()["message"] == "Measure revenue deleted."


def test_edit_service_compile_requires_configured_command(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    (cube_dir / "payment.yml").write_text("cube: payment\n", encoding="utf-8")

    app = create_app(EditServiceConfig(cube_model_dir=cube_dir))
    client = TestClient(app)

    response = client.post("/v1/compile")

    assert response.status_code == 400
    assert "METISONE_CUBE_COMPILE_COMMAND" in response.json()["detail"]


def test_edit_service_chat_creates_measure(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    payment = cube_dir / "payment.yml"
    payment.write_text(
        "\n".join(
            [
                "cube: payment",
                "sql_table: public.payment",
                "measures:",
                "dimensions:",
                "joins:",
                "",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app(
        EditServiceConfig(
            cube_model_dir=cube_dir,
            api_token="secret",
        )
    )
    client = TestClient(app)
    response = client.post(
        "/v1/chat",
        headers={"Authorization": "Bearer secret"},
        json={
            "message": 'create measure revenue on payment sql amount type sum title "Revenue"'
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["command"]["member_kind"] == "measure"
    assert "revenue" in payment.read_text(encoding="utf-8")


def test_edit_service_chat_ui_is_available(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    (cube_dir / "payment.yml").write_text("cube: payment\n", encoding="utf-8")

    app = create_app(EditServiceConfig(cube_model_dir=cube_dir))
    client = TestClient(app)

    response = client.get("/ui")

    assert response.status_code == 200
    assert "MetisOne Semantic Layer Assistant" in response.text


def test_edit_service_lists_members_from_nested_cube_document(tmp_path) -> None:
    from fastapi.testclient import TestClient

    cube_dir = tmp_path / "cube"
    cube_dir.mkdir()
    (cube_dir / "actor.yml").write_text(
        "\n".join(
            [
                "cubes:",
                "- name: actor",
                "  sql_table: public.actor",
                "  dimensions:",
                "  - name: first_name",
                "    sql: first_name",
                "    type: string",
                "  - name: last_name",
                "    sql: last_name",
                "    type: string",
                "",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app(EditServiceConfig(cube_model_dir=cube_dir))
    client = TestClient(app)

    listed = client.get("/v1/cubes")
    cube = client.get("/v1/cubes/actor")
    dimensions = client.get("/v1/cubes/actor/dimensions")

    assert listed.json()[0]["dimensions_count"] == 2
    assert listed.json()[0]["sql_table"] == "public.actor"
    assert cube.json()["data"]["sql_table"] == "public.actor"
    assert [dimension["name"] for dimension in dimensions.json()] == [
        "first_name",
        "last_name",
    ]
