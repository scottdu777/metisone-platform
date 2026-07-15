from metisone_ai_platform.data_query.contracts import DataQueryClient, DataQueryPlanner
from metisone_ai_platform.data_query.models import (
    CubeFilter,
    CubeQuery,
    DataQueryPlan,
    DataQueryRequest,
)
from metisone_ai_platform.data_query.orchestrator import DataQueryOrchestrator
from metisone_ai_platform.data_query.planner import OpenAIDataQueryPlanner


class FakePlanner(DataQueryPlanner):
    def plan(self, request, cube_metadata):
        return DataQueryPlan(
            cube_query=CubeQuery(
                dimensions=["film.title"],
                filters=[
                    CubeFilter(
                        member="film.title",
                        operator="equals",
                        values=["Academy Dinosaur"],
                    )
                ],
                limit=1,
            ),
            response_hint="Found matching films.",
        )


class InvalidPlanner(DataQueryPlanner):
    def plan(self, request, cube_metadata):
        return DataQueryPlan(
            cube_query=CubeQuery(dimensions=["film.missing_title"]),
        )


class FakeCubeClient(DataQueryClient):
    def __init__(self) -> None:
        self.loaded_query = None

    def meta(self):
        return {
            "cubes": [
                {
                    "name": "film",
                    "dimensions": [
                        {"name": "film.title", "type": "string"},
                    ],
                    "measures": [
                        {"name": "film.count", "type": "number"},
                    ],
                }
            ]
        }

    def load(self, query):
        self.loaded_query = query
        return {
            "data": [{"film.title": "Academy Dinosaur"}],
            "annotation": {"dimensions": {"film.title": {"type": "string"}}},
        }


def test_data_query_orchestrator_executes_valid_cube_query() -> None:
    client = FakeCubeClient()
    orchestrator = DataQueryOrchestrator(planner=FakePlanner(), client=client)

    response = orchestrator.ask(
        DataQueryRequest(question="Is there a film called Academy Dinosaur?")
    )

    assert response.status == "success"
    assert client.loaded_query == {
        "measures": [],
        "dimensions": ["film.title"],
        "filters": [
            {
                "member": "film.title",
                "operator": "equals",
                "values": ["Academy Dinosaur"],
            }
        ],
        "timeDimensions": [],
        "segments": [],
        "limit": 1,
    }
    assert response.result.rows == [{"film.title": "Academy Dinosaur"}]


def test_data_query_orchestrator_rejects_unknown_members() -> None:
    orchestrator = DataQueryOrchestrator(
        planner=InvalidPlanner(),
        client=FakeCubeClient(),
    )

    response = orchestrator.ask(DataQueryRequest(question="bad query"))

    assert response.status == "error"
    assert "Unknown Cube dimension" in response.error


def test_openai_planner_normalizes_duplicate_cube_prefix(monkeypatch) -> None:
    planner = OpenAIDataQueryPlanner(api_key="test")
    metadata = {
        "cubes": [
            {
                "name": "actor",
                "measures": [{"name": "actor.count", "type": "number"}],
                "dimensions": [{"name": "actor.actor_id", "type": "number"}],
            }
        ]
    }
    monkeypatch.setattr(
        planner,
        "_call_openai",
        lambda request, compact_metadata: (
            '{"query":{"measures":["actor.actor.count"],"limit":100}}'
        ),
    )

    plan = planner.plan(DataQueryRequest(question="How many actors?"), metadata)

    assert plan.cube_query.measures == ["actor.count"]
