from __future__ import annotations

from abc import ABC, abstractmethod

from metisone_ai_platform.core.models import CompiledQuery, QueryIntent
from metisone_ai_platform.semantic_layer.models import SemanticModel


class SemanticProvider(ABC):
    @abstractmethod
    def list_models(self) -> list[SemanticModel]:
        """Return available semantic models."""

    @abstractmethod
    def get_model(self, model_name: str) -> SemanticModel:
        """Return one semantic model by name."""

    @abstractmethod
    def compile(self, intent: QueryIntent) -> CompiledQuery:
        """Compile a structured query intent into a provider-specific query."""
