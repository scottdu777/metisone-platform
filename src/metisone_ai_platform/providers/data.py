from __future__ import annotations

from metisone_ai_platform.core.models import CompiledQuery, QueryResult
from metisone_ai_platform.providers.base import CapabilityProvider, DataProvider


class PostgreSQLDataProvider(DataProvider, CapabilityProvider):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def capabilities(self) -> set[str]:
        return {"postgres", "execute_query"}

    def execute(self, query: CompiledQuery) -> QueryResult:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQLDataProvider requires optional dependency psycopg. "
                'Install it with: pip install ".[postgres]"'
            ) from exc

        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query.sql, query.parameters)
                rows = [dict(row) for row in cursor.fetchall()]
                columns = [column.name for column in cursor.description or []]

        return QueryResult(columns=columns, rows=rows, row_count=len(rows))


class InMemoryDataProvider(DataProvider, CapabilityProvider):
    """Test/dev provider keyed by SQL text."""

    def __init__(self, responses: dict[str, QueryResult] | None = None) -> None:
        self.responses = responses or {}

    def capabilities(self) -> set[str]:
        return {"execute_query", "local"}

    def execute(self, query: CompiledQuery) -> QueryResult:
        return self.responses.get(
            query.sql,
            QueryResult(columns=[], rows=[], row_count=0),
        )
