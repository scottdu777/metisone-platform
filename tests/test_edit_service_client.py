import json
import urllib.request

from metisone_ai_platform.semantic_layer.edit_service.client import (
    SemanticEditServiceClient,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_edit_service_client_uses_service_url_from_env(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization")
        captured["timeout"] = timeout
        return FakeResponse([{"cube": "payment"}])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("SEMANTIC_EDIT_SERVICE_URL", "http://example.test:18088")

    client = SemanticEditServiceClient(api_token="change-me")
    result = client.list_cubes()

    assert captured["url"] == "http://example.test:18088/v1/cubes"
    assert captured["authorization"] == "Bearer change-me"
    assert captured["timeout"] == 30
    assert result == [{"cube": "payment"}]


def test_edit_service_client_create_measure_payload(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"success": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = SemanticEditServiceClient(
        base_url="http://example.test:18088",
        api_token="change-me",
    )
    result = client.create_measure(
        "payment",
        name="revenue",
        sql="amount",
        measure_type="sum",
        extra_fields={"title": "Revenue"},
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test:18088/v1/cubes/payment/measures"
    assert captured["body"] == {
        "name": "revenue",
        "sql": "amount",
        "type": "sum",
        "extra_fields": {"title": "Revenue"},
    }
    assert result == {"success": True}


def test_edit_service_client_chat_payload(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"success": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    client = SemanticEditServiceClient(
        base_url="http://example.test:18088",
        api_token="change-me",
    )
    result = client.chat("create measure revenue on payment sql amount type sum")

    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test:18088/v1/chat"
    assert captured["body"] == {
        "message": "create measure revenue on payment sql amount type sum"
    }
    assert result == {"success": True}
