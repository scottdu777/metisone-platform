from __future__ import annotations

from metisone_ai_platform.core.models import CompiledQuery, QueryResult
from metisone_ai_platform.providers.base import CapabilityProvider, DataProvider
from metisone_ai_platform.semantic_layer.cube_core.client import CubeClient


class CubeDataProvider(DataProvider, CapabilityProvider):
    """Execute compiled Cube queries through Cube Core."""

    def __init__(self, client: CubeClient) -> None:
        self.client = client

    def capabilities(self) -> set[str]:
        return {"cube_core", "execute_query"}

    def execute(self, query: CompiledQuery) -> QueryResult:
        if query.dialect != "cube":
            raise ValueError(f"CubeDataProvider cannot execute {query.dialect} query.")

        cube_query = query.parameters.get("query")
        if not isinstance(cube_query, dict):
            raise ValueError("Cube compiled query must include parameters['query'].")

        payload = self.client.load(cube_query)
        rows = [dict(row) for row in payload.get("data", [])]
        columns = list(rows[0].keys()) if rows else self._columns_from_annotation(payload)

        return QueryResult(columns=columns, rows=rows, row_count=len(rows))

    def _columns_from_annotation(self, payload: dict) -> list[str]:
        annotation = payload.get("annotation", {})
        columns: list[str] = []

        for section in ("dimensions", "measures", "timeDimensions"):
            values = annotation.get(section, {})
            if isinstance(values, dict):
                columns.extend(values.keys())

        return columns
