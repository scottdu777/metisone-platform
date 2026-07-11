from metisone_ai_platform.core.models import QueryIntent
from metisone_ai_platform.semantic_layer.cube_core import (
    CubeDataProvider,
    CubeSemanticProvider,
)


class FakeCubeClient:
    def meta(self):
        return {
            "cubes": [
                {
                    "name": "Orders",
                    "measures": [
                        {
                            "name": "Orders.revenue",
                            "type": "sum",
                            "title": "Revenue",
                        }
                    ],
                    "dimensions": [
                        {
                            "name": "Orders.region",
                            "type": "string",
                            "title": "Region",
                        }
                    ],
                }
            ]
        }

    def load(self, query):
        return {
            "data": [
                {
                    "Orders.region": "East",
                    "Orders.revenue": 1000,
                }
            ]
        }


def test_cube_semantic_provider_reads_metadata_and_compiles_query() -> None:
    provider = CubeSemanticProvider(FakeCubeClient())

    models = provider.list_models()
    compiled = provider.compile(
        QueryIntent(
            model_name="Orders",
            metrics=["revenue"],
            dimensions=["region"],
            limit=100,
        )
    )

    assert models[0].name == "Orders"
    assert models[0].metrics["revenue"].expression == "Orders.revenue"
    assert compiled.dialect == "cube"
    assert compiled.parameters["query"] == {
        "measures": ["Orders.revenue"],
        "dimensions": ["Orders.region"],
        "filters": [],
        "limit": 100,
    }


def test_cube_data_provider_returns_structured_result() -> None:
    semantic_provider = CubeSemanticProvider(FakeCubeClient())
    data_provider = CubeDataProvider(FakeCubeClient())
    compiled = semantic_provider.compile(
        QueryIntent(
            model_name="Orders",
            metrics=["revenue"],
            dimensions=["region"],
        )
    )

    result = data_provider.execute(compiled)

    assert result.columns == ["Orders.region", "Orders.revenue"]
    assert result.rows == [{"Orders.region": "East", "Orders.revenue": 1000}]
    assert result.row_count == 1
