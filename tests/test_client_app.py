from metisone_ai_platform.semantic_layer.client_app.agent import (
    LocalSemanticEditAgent,
)
from metisone_ai_platform.semantic_layer.client_app.app import create_app


class FakeRemoteClient:
    def __init__(self) -> None:
        self.calls = []

    def create_measure(self, cube, name, sql, measure_type, extra_fields=None):
        self.calls.append(("create_measure", cube, name, sql, measure_type, extra_fields))
        return {"success": True, "message": "Measure revenue created."}


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
    assert "MetisOne Local Semantic Chat Client" in response.text
