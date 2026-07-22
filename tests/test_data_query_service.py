import json

from metisone_ai_platform.observability import JsonRequestLogConfig
from metisone_ai_platform.semantic_query.app import create_app
from metisone_ai_platform.semantic_query.config import DataQueryServiceConfig
from metisone_ai_platform.semantic_query.contracts import DataQueryClient, DataQueryPlanner
from metisone_ai_platform.semantic_query.models import (
    CubeQuery,
    DataQueryPlan,
)
from metisone_ai_platform.semantic_query.orchestrator import DataQueryOrchestrator


class CountPlanner(DataQueryPlanner):
    def plan(self, request, cube_metadata):
        return DataQueryPlan(
            cube_query=CubeQuery(measures=["actor.count"], limit=request.limit),
            response_hint="Actor count.",
        )


class CountClient(DataQueryClient):
    def meta(self):
        return {
            "cubes": [
                {
                    "name": "actor",
                    "measures": [{"name": "actor.count", "type": "number"}],
                    "dimensions": [],
                }
            ]
        }

    def load(self, query):
        return {"data": [{"actor.count": "200"}], "annotation": {}}


def test_semantic_data_query_service_is_independently_authenticated(tmp_path) -> None:
    from fastapi.testclient import TestClient

    log_file = tmp_path / "query-requests.jsonl"
    app = create_app(
        DataQueryServiceConfig(
            cube_api_url="http://cube.invalid/cubejs-api/v1",
            api_token="query-secret",
        ),
        DataQueryOrchestrator(CountPlanner(), CountClient()),
        JsonRequestLogConfig(file_path=log_file),
    )
    client = TestClient(app)

    unauthorized = client.post(
        "/v1/query",
        json={"question": "How many actors?"},
    )
    response = client.post(
        "/v1/query",
        headers={"Authorization": "Bearer query-secret"},
        json={"question": "How many actors?"},
    )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["answer"] == "There are 200 actors."
    assert response.json()["cube_request"]["query"]["measures"] == ["actor.count"]
    assert response.json()["cube_response"]["data"] == [{"actor.count": "200"}]
    assert response.json()["result"]["rows"] == [{"actor.count": "200"}]
    records = [
        json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 2
    assert records[-1]["service"] == "semantic_data_query_service"
    assert records[-1]["request"]["question"] == "How many actors?"
    assert records[-1]["response"]["cube_request"] == {
        "endpoint": "/load",
        "method": "POST",
        "query": {
            "measures": ["actor.count"],
            "dimensions": [],
            "filters": [],
            "timeDimensions": [],
            "segments": [],
            "limit": 100,
        },
    }
    assert records[-1]["response"]["cube_response"]["data"] == [
        {"actor.count": "200"}
    ]
    assert records[-1]["response"]["result"]["rows"] == [{"actor.count": "200"}]


def test_semantic_data_query_service_has_no_standalone_ui() -> None:
    from fastapi.testclient import TestClient

    app = create_app(
        DataQueryServiceConfig(cube_api_url="http://cube.invalid"),
        DataQueryOrchestrator(CountPlanner(), CountClient()),
    )

    response = TestClient(app).get("/")

    assert response.status_code == 404
