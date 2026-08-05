from metisone_ai_platform.semantic_query.contracts import DataQueryClient, DataQueryPlanner
from metisone_ai_platform.semantic_query.models import (
    CubeFilter,
    CubeQuery,
    DataQueryPlan,
    DataQueryRequest,
)
from metisone_ai_platform.semantic_query.orchestrator import DataQueryOrchestrator
from metisone_ai_platform.semantic_query.planner import OpenAIDataQueryPlanner


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
            '{"query":{"measures":["actor.actor.count"],"limit":100}}',
            {},
        ),
    )

    plan = planner.plan(DataQueryRequest(question="How many actors?"), metadata)

    assert plan.cube_query.measures == ["actor.count"]


def test_openai_planner_normalizes_count_measure_from_metadata(monkeypatch) -> None:
    planner = OpenAIDataQueryPlanner(api_key="test")
    metadata = {
        "cubes": [
            {
                "name": "rental",
                "measures": [{"name": "rental.count", "type": "number"}],
                "dimensions": [{"name": "rental.rental_id", "type": "number"}],
            },
            {
                "name": "film",
                "title": "Films",
                "measures": [{"name": "film.count", "type": "number"}],
                "dimensions": [{"name": "film.title", "type": "string"}],
            },
            {
                "name": "category",
                "measures": [{"name": "category.count", "type": "number"}],
                "dimensions": [{"name": "category.name", "type": "string"}],
            },
            {
                "name": "city",
                "measures": [{"name": "city.count", "type": "number"}],
                "dimensions": [{"name": "city.city", "type": "string"}],
            },
            {
                "name": "address",
                "measures": [{"name": "address.count", "type": "number"}],
                "dimensions": [{"name": "address.address", "type": "string"}],
            },
        ]
    }
    monkeypatch.setattr(
        planner,
        "_call_openai",
        lambda request, compact_metadata: (
            '{"query":{"measures":["rental.count"],"filters":['
            '{"member":"category.name","operator":"contains","values":["sports"]},'
            '{"member":"address.address","operator":"contains","values":["Woodridge"]}'
            '],"joins":[{"from":"rental","to":"inventory"}],"limit":100}}',
            {},
        ),
    )

    plan = planner.plan(
        DataQueryRequest(
            question="Please show me how many sports movies were rented in Woodridge"
        ),
        metadata,
    )

    assert plan.cube_query.to_cube_payload() == {
        "measures": ["film.count"],
        "dimensions": ["category.name", "city.city"],
        "filters": [
            {
                "member": "category.name",
                "operator": "equals",
                "values": ["Sports"],
            },
            {
                "member": "city.city",
                "operator": "equals",
                "values": ["Woodridge"],
            },
        ],
        "timeDimensions": [],
        "segments": [],
        "limit": 100,
    }


def test_openai_planner_uses_generic_metadata_for_other_business_domains(monkeypatch) -> None:
    planner = OpenAIDataQueryPlanner(api_key="test")
    metadata = {
        "cubes": [
            {
                "name": "payment_event",
                "title": "Payment Events",
                "measures": [{"name": "payment_event.count", "type": "number"}],
                "dimensions": [{"name": "payment_event.status", "type": "string"}],
            },
            {
                "name": "invoice",
                "title": "Invoices",
                "description": "Customer invoices",
                "measures": [{"name": "invoice.count", "type": "number"}],
                "dimensions": [{"name": "invoice.invoice_id", "type": "number"}],
            },
            {
                "name": "region",
                "title": "Regions",
                "measures": [{"name": "region.count", "type": "number"}],
                "dimensions": [{"name": "region.region_name", "type": "string"}],
            },
        ]
    }
    monkeypatch.setattr(
        planner,
        "_call_openai",
        lambda request, compact_metadata: (
            '{"query":{"measures":["payment_event.count"],"filters":['
            '{"member":"region.region_name","operator":"contains","values":["west"]}'
            '],"limit":100}}',
            {},
        ),
    )

    plan = planner.plan(
        DataQueryRequest(question="How many invoices are in west region?"),
        metadata,
    )

    assert plan.cube_query.to_cube_payload() == {
        "measures": ["invoice.count"],
        "dimensions": ["region.region_name"],
        "filters": [
            {
                "member": "region.region_name",
                "operator": "equals",
                "values": ["West"],
            }
        ],
        "timeDimensions": [],
        "segments": [],
        "limit": 100,
    }
