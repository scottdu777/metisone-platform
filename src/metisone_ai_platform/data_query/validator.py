from __future__ import annotations

from typing import Any

from metisone_ai_platform.data_query.models import CubeQuery


ALLOWED_FILTER_OPERATORS = {
    "equals",
    "notEquals",
    "contains",
    "notContains",
    "startsWith",
    "notStartsWith",
    "endsWith",
    "notEndsWith",
    "gt",
    "gte",
    "lt",
    "lte",
    "set",
    "notSet",
    "inDateRange",
    "notInDateRange",
    "beforeDate",
    "beforeOrOnDate",
    "afterDate",
    "afterOrOnDate",
}


class CubeQueryValidator:
    def __init__(self, max_limit: int = 500) -> None:
        self.max_limit = max_limit

    def validate(self, query: CubeQuery, metadata: dict[str, Any]) -> None:
        members = self._members(metadata)

        for measure in query.measures:
            if measure not in members["measures"]:
                raise ValueError(f"Unknown Cube measure: {measure}")

        for dimension in query.dimensions:
            if self._base_time_member(dimension) not in members["dimensions"]:
                raise ValueError(f"Unknown Cube dimension: {dimension}")

        for segment in query.segments:
            if segment not in members["segments"]:
                raise ValueError(f"Unknown Cube segment: {segment}")

        for item in query.filters:
            if item.member not in members["all"]:
                raise ValueError(f"Unknown Cube filter member: {item.member}")
            if item.operator not in ALLOWED_FILTER_OPERATORS:
                raise ValueError(f"Unsupported Cube filter operator: {item.operator}")

        for item in query.time_dimensions:
            dimension = item.get("dimension")
            if not isinstance(dimension, str) or dimension not in members["dimensions"]:
                raise ValueError(f"Unknown Cube time dimension: {dimension}")

        if query.limit < 1 or query.limit > self.max_limit:
            raise ValueError(f"Cube query limit must be between 1 and {self.max_limit}.")

    def _members(self, metadata: dict[str, Any]) -> dict[str, set[str]]:
        measures: set[str] = set()
        dimensions: set[str] = set()
        segments: set[str] = set()

        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            measures.update(self._names(cube.get("measures")))
            dimensions.update(self._names(cube.get("dimensions")))
            segments.update(self._names(cube.get("segments")))

        return {
            "measures": measures,
            "dimensions": dimensions,
            "segments": segments,
            "all": measures | dimensions | segments,
        }

    def _names(self, items: Any) -> set[str]:
        names: set[str] = set()
        if not isinstance(items, list):
            return names
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.add(item["name"])
        return names

    def _base_time_member(self, member: str) -> str:
        parts = member.split(".")
        if len(parts) >= 3:
            return ".".join(parts[:2])
        return member
