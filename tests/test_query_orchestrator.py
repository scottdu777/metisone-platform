from metisone_ai_platform.core.models import (
    Dimension,
    Metric,
    QueryRequest,
    QueryResult,
    SemanticModel,
)
from metisone_ai_platform.orchestrator.query_orchestrator import QueryOrchestrator
from metisone_ai_platform.providers.data import InMemoryDataProvider
from metisone_ai_platform.providers.llm import RuleBasedLLMProvider
from metisone_ai_platform.semantic_layer.native_provider import NativeSemanticProvider


def test_query_orchestrator_returns_structured_result() -> None:
    model = SemanticModel(
        name="sales",
        table="sales_orders",
        metrics={
            "revenue": Metric(
                name="revenue",
                expression="amount",
                aggregation="sum",
                description="sales revenue",
            )
        },
        dimensions={
            "region": Dimension(
                name="region",
                expression="region",
                description="sales region",
            )
        },
    )
    semantic_provider = NativeSemanticProvider([model])
    compiled = semantic_provider.compile(
        RuleBasedLLMProvider().generate_intent(
            QueryRequest(question="revenue by region", model_name="sales"),
            [model],
        )
    )
    result = QueryResult(
        columns=["region", "revenue"],
        rows=[{"region": "East", "revenue": 1000}],
        row_count=1,
    )
    orchestrator = QueryOrchestrator(
        llm_provider=RuleBasedLLMProvider(),
        semantic_provider=semantic_provider,
        data_provider=InMemoryDataProvider({compiled.sql: result}),
    )

    response = orchestrator.ask(
        QueryRequest(question="revenue by region", model_name="sales")
    )

    assert response.status == "success"
    assert response.intent is not None
    assert response.intent.metrics == ["revenue"]
    assert response.intent.dimensions == ["region"]
    assert response.result == result
