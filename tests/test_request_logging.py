import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from metisone_ai_platform.observability import (
    JsonRequestLogConfig,
    install_json_request_logging,
)
from metisone_ai_platform.semantic_client.app import create_app


class FakeQueryServiceClient:
    def query(self, question, limit=100):
        return {"answer": "Query result: 64", "internal": {"sql": "hidden"}}


def test_json_request_logging_redacts_secrets_and_preserves_response(tmp_path) -> None:
    log_file = tmp_path / "requests.jsonl"
    app = FastAPI()
    install_json_request_logging(
        app,
        service_name="test_service",
        paths=("/v1/",),
        config=JsonRequestLogConfig(file_path=log_file),
    )

    @app.post("/v1/example")
    def example(payload: dict) -> dict:
        return {
            "received": payload["message"],
            "credentials": {"api_key": "response-secret"},
        }

    response = TestClient(app).post(
        "/v1/example",
        headers={"X-Request-ID": "analysis-123"},
        json={
            "message": "inspect this request",
            "api_token": "request-secret",
            "nested": {"password": "password-secret"},
        },
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "analysis-123"
    assert response.json()["received"] == "inspect this request"

    record = json.loads(log_file.read_text(encoding="utf-8"))
    assert record["request_id"] == "analysis-123"
    assert record["status_code"] == 200
    assert record["request"]["message"] == "inspect this request"
    assert record["request"]["api_token"] == "***REDACTED***"
    assert record["request"]["nested"]["password"] == "***REDACTED***"
    assert record["response"]["credentials"]["api_key"] == "***REDACTED***"


def test_semantic_client_logs_original_request_and_concise_response(tmp_path) -> None:
    log_file = tmp_path / "client-requests.jsonl"
    app = create_app(
        query_client=FakeQueryServiceClient(),
        request_log_config=JsonRequestLogConfig(file_path=log_file),
    )

    response = TestClient(app).post(
        "/local-chat",
        json={"mode": "query", "message": "How many action films?"},
    )

    assert response.json() == {
        "success": True,
        "mode": "query",
        "message": "Query result: 64",
    }
    record = json.loads(log_file.read_text(encoding="utf-8"))
    assert record["service"] == "semantic_client"
    assert record["request"]["message"] == "How many action films?"
    assert record["response"] == response.json()


def test_json_request_log_rotates_by_size(tmp_path) -> None:
    log_file = tmp_path / "rotating.jsonl"
    app = FastAPI()
    install_json_request_logging(
        app,
        service_name="rotation_test",
        paths=("/v1/",),
        config=JsonRequestLogConfig(
            file_path=log_file,
            max_bytes=300,
            backup_count=2,
        ),
    )

    @app.post("/v1/example")
    def example(payload: dict) -> dict:
        return payload

    client = TestClient(app)
    for index in range(4):
        response = client.post(
            "/v1/example",
            json={"index": index, "content": "x" * 200},
        )
        assert response.status_code == 200

    assert log_file.exists()
    assert (tmp_path / "rotating.jsonl.1").exists()
