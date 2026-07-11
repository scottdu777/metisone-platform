from __future__ import annotations

from metisone_ai_platform.core.models import QueryRequest, QueryResponse
from metisone_ai_platform.providers.base import DataProvider, LLMProvider, SemanticProvider


class QueryOrchestrator:
    def __init__(
        self,
        llm_provider: LLMProvider,
        semantic_provider: SemanticProvider,
        data_provider: DataProvider,
    ) -> None:
        self.llm_provider = llm_provider
        self.semantic_provider = semantic_provider
        self.data_provider = data_provider

    def ask(self, request: QueryRequest) -> QueryResponse:
        try:
            models = self.semantic_provider.list_models()
            intent = self.llm_provider.generate_intent(request, models)
            compiled_query = self.semantic_provider.compile(intent)
            result = self.data_provider.execute(compiled_query)

            return QueryResponse(
                status="success",
                request=request,
                intent=intent,
                compiled_query=compiled_query,
                result=result,
            )
        except Exception as exc:
            return QueryResponse(status="error", request=request, error=str(exc))
