from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from metisone_ai_platform.semantic_layer.models import (
    Aggregation,
    Dimension,
    Metric,
    SemanticModel,
)

QueryStatus = Literal["success", "error"]


@dataclass(frozen=True)
class QueryRequest:
    question: str
    model_name: str | None = None
    limit: int = 500


@dataclass(frozen=True)
class QueryIntent:
    model_name: str
    metrics: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    filters: list[dict[str, Any]] = field(default_factory=list)
    time_range: dict[str, Any] | None = None
    limit: int = 500


@dataclass(frozen=True)
class CompiledQuery:
    sql: str
    parameters: dict[str, Any] = field(default_factory=dict)
    dialect: str = "postgres"


@dataclass(frozen=True)
class QueryResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int


@dataclass(frozen=True)
class QueryResponse:
    status: QueryStatus
    request: QueryRequest
    intent: QueryIntent | None = None
    compiled_query: CompiledQuery | None = None
    result: QueryResult | None = None
    error: str | None = None
