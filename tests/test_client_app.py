from metisone_ai_platform.semantic_client.agent import (
    LocalSemanticEditAgent,
)
from metisone_ai_platform.semantic_client.app import create_app


class FakeRemoteClient:
    def __init__(self) -> None:
        self.calls = []

    def create_measure(self, cube, name, sql, measure_type, extra_fields=None):
        self.calls.append(("create_measure", cube, name, sql, measure_type, extra_fields))
        return {"success": True, "message": "Measure revenue created."}


class FakeQueryServiceClient:
    def query(self, question, limit=100):
        assert question == "Action 类型有多少部电影？"
        return {
            "answer": "查询结果：64",
            "plan": {"cube_query": {"measures": ["film_category.films_count"]}},
        }


def test_local_agent_calls_remote_edit_client() -> None:
    remote = FakeRemoteClient()
    agent = LocalSemanticEditAgent(remote)

    command, result = agent.handle(
        'create measure revenue on payment sql amount type sum title "Revenue"'
    )

    assert command.cube == "payment"
    assert command.member_kind == "measure"
    assert remote.calls == [
        (
            "create_measure",
            "payment",
            "revenue",
            "amount",
            "sum",
            {"title": "Revenue"},
        )
    ]
    assert result["success"] is True


def test_local_chat_ui_is_available() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    assert "MetisOne Semantic Client" in response.text
    assert "查询数据" in response.text
    assert "编辑模型" in response.text


def test_semantic_client_returns_only_a_concise_query_message() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(create_app(query_client=FakeQueryServiceClient()))
    response = client.post(
        "/local-chat",
        json={"mode": "query", "message": "Action 类型有多少部电影？"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "mode": "query",
        "message": "查询结果：64",
    }
