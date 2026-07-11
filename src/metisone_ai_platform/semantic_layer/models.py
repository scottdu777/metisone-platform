from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Aggregation = Literal["sum", "avg", "min", "max", "count", "count_distinct"]


@dataclass(frozen=True)
class Metric:
    name: str
    expression: str
    aggregation: Aggregation = "sum"
    description: str | None = None
    synonyms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Dimension:
    name: str
    expression: str
    data_type: str = "string"
    description: str | None = None
    synonyms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Join:
    name: str
    relationship: str
    sql: str


@dataclass(frozen=True)
class SemanticModel:
    name: str
    table: str
    metrics: dict[str, Metric]
    dimensions: dict[str, Dimension]
    joins: dict[str, Join] = field(default_factory=dict)
    default_time_dimension: str | None = None
    description: str | None = None
