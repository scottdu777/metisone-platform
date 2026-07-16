from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DataQueryStatus = Literal["success", "error"]


@dataclass(frozen=True)
class DataQueryRequest:
    question: str
    limit: int = 100


@dataclass(frozen=True)
class CubeFilter:
    member: str
    operator: str
    values: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CubeQuery:
    measures: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    filters: list[CubeFilter] = field(default_factory=list)
    time_dimensions: list[dict[str, Any]] = field(default_factory=list)
    segments: list[str] = field(default_factory=list)
    limit: int = 100
    order: dict[str, str] = field(default_factory=dict)

    def to_cube_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "measures": self.measures,
            "dimensions": self.dimensions,
            "filters": [
                {
                    "member": item.member,
                    "operator": item.operator,
                    **({"values": item.values} if item.values else {}),
                }
                for item in self.filters
            ],
            "timeDimensions": self.time_dimensions,
            "segments": self.segments,
            "limit": self.limit,
        }
        if self.order:
            payload["order"] = self.order
        return payload


@dataclass(frozen=True)
class DataQueryPlan:
    cube_query: CubeQuery
    response_hint: str | None = None


@dataclass(frozen=True)
class DataQueryResult:
    rows: list[dict[str, Any]]
    row_count: int
    annotation: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataQueryResponse:
    status: DataQueryStatus
    request: DataQueryRequest
    plan: DataQueryPlan | None = None
    result: DataQueryResult | None = None
    message: str | None = None
    error: str | None = None
