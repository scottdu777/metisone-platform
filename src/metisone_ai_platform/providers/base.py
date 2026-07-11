from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from metisone_ai_platform.core.models import (
    CompiledQuery,
    QueryIntent,
    QueryRequest,
    QueryResult,
)
from metisone_ai_platform.semantic_layer.contracts import SemanticProvider
from metisone_ai_platform.semantic_layer.models import SemanticModel


class LLMProvider(ABC):
    @abstractmethod
    def generate_intent(
        self,
        request: QueryRequest,
        models: list[SemanticModel],
    ) -> QueryIntent:
        """Convert a natural-language request into a structured query intent."""


class DataProvider(ABC):
    @abstractmethod
    def execute(self, query: CompiledQuery) -> QueryResult:
        """Execute a compiled query and return structured rows."""


class CapabilityProvider(ABC):
    @abstractmethod  
    def capabilities(self) -> set[str]:
        """Declare provider capabilities for future orchestration."""
