from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from metisone_ai_platform.data_query.models import DataQueryPlan, DataQueryRequest


class DataQueryPlanner(ABC):
    @abstractmethod
    def plan(
        self,
        request: DataQueryRequest,
        cube_metadata: dict[str, Any],
    ) -> DataQueryPlan:
        """Convert a natural-language data question into a Cube REST query."""


class DataQueryClient(ABC):
    @abstractmethod
    def meta(self) -> dict[str, Any]:
        """Return Cube metadata from /v1/meta."""

    @abstractmethod
    def load(self, query: dict[str, Any]) -> dict[str, Any]:
        """Execute a Cube REST /v1/load query."""
