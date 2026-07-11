from __future__ import annotations

import json
from typing import Any

from metisone_ai_platform.core.models import CompiledQuery, QueryIntent
from metisone_ai_platform.providers.base import CapabilityProvider
from metisone_ai_platform.semantic_layer.contracts import SemanticProvider
from metisone_ai_platform.semantic_layer.cube_core.client import CubeClient
from metisone_ai_platform.semantic_layer.models import (
    Aggregation,
    Dimension,
    Metric,
    SemanticModel,
)


class CubeSemanticProvider(SemanticProvider, CapabilityProvider):
    """Semantic provider backed by Cube Core metadata and query format."""

    def __init__(self, client: CubeClient) -> None:
        self.client = client

    def capabilities(self) -> set[str]:
        return {"cube_core", "metadata", "metrics", "dimensions", "compile_query"}

    def list_models(self) -> list[SemanticModel]:
        payload = self.client.meta()
        return [self._to_semantic_model(cube) for cube in payload.get("cubes", [])]

    def get_model(self, model_name: str) -> SemanticModel:
        for model in self.list_models():
            if model.name == model_name:
                return model
        raise ValueError(f"Unknown Cube semantic model: {model_name}")

    def compile(self, intent: QueryIntent) -> CompiledQuery:
        model = self.get_model(intent.model_name)
        measures = [self._member_name(model, metric) for metric in intent.metrics]
        dimensions = [
            self._member_name(model, dimension) for dimension in intent.dimensions
        ]

        query: dict[str, Any] = {
            "measures": measures,
            "dimensions": dimensions,
            "filters": [
                self._compile_filter(model, item) for item in intent.filters
            ],
            "limit": intent.limit,
        }

        time_dimensions = self._compile_time_dimensions(model, intent.time_range)
        if time_dimensions:
            query["timeDimensions"] = time_dimensions

        return CompiledQuery(
            sql=json.dumps(query, separators=(",", ":"), sort_keys=True),
            parameters={"query": query},
            dialect="cube",
        )

    def _to_semantic_model(self, cube: dict[str, Any]) -> SemanticModel:
        cube_name = cube["name"]
        metrics = {
            self._short_name(item["name"], cube_name): Metric(
                name=self._short_name(item["name"], cube_name),
                expression=item["name"],
                aggregation=self._map_aggregation(item.get("type")),
                description=item.get("description") or item.get("title"),
            )
            for item in cube.get("measures", [])
        }
        dimensions = {
            self._short_name(item["name"], cube_name): Dimension(
                name=self._short_name(item["name"], cube_name),
                expression=item["name"],
                data_type=item.get("type", "string"),
                description=item.get("description") or item.get("title"),
            )
            for item in cube.get("dimensions", [])
        }

        return SemanticModel(
            name=cube_name,
            table=cube_name,
            metrics=metrics,
            dimensions=dimensions,
        )

    def _short_name(self, member_name: str, cube_name: str) -> str:
        prefix = f"{cube_name}."
        if member_name.startswith(prefix):
            return member_name[len(prefix) :]
        return member_name

    def _member_name(self, model: SemanticModel, name: str) -> str:
        if "." in name:
            return name
        if name in model.metrics:
            return model.metrics[name].expression
        if name in model.dimensions:
            return model.dimensions[name].expression
        raise ValueError(f"Unknown Cube member for {model.name}: {name}")

    def _map_aggregation(self, cube_type: str | None) -> Aggregation:
        mapping: dict[str, Aggregation] = {
            "sum": "sum",
            "avg": "avg",
            "average": "avg",
            "min": "min",
            "max": "max",
            "count": "count",
            "countDistinct": "count_distinct",
            "count_distinct": "count_distinct",
        }
        return mapping.get(cube_type or "", "sum")

    def _compile_filter(
        self,
        model: SemanticModel,
        item: dict[str, Any],
    ) -> dict[str, Any]:
        operator = item.get("operator", "equals")
        value = item.get("value")

        return {
            "member": self._member_name(model, item["field"]),
            "operator": self._map_filter_operator(operator),
            "values": value if isinstance(value, list) else [value],
        }

    def _map_filter_operator(self, operator: str) -> str:
        mapping = {
            "=": "equals",
            "==": "equals",
            "equals": "equals",
            "in": "equals",
            "!=": "notEquals",
            "<>": "notEquals",
            "not_equals": "notEquals",
            ">": "gt",
            ">=": "gte",
            "<": "lt",
            "<=": "lte",
            "contains": "contains",
        }
        return mapping.get(operator.lower(), operator)

    def _compile_time_dimensions(
        self,
        model: SemanticModel,
        time_range: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        if not time_range:
            return []

        dimension = time_range.get("dimension") or model.default_time_dimension
        if not dimension:
            return []

        output: dict[str, Any] = {"dimension": self._member_name(model, dimension)}
        if "date_range" in time_range:
            output["dateRange"] = time_range["date_range"]
        if "granularity" in time_range:
            output["granularity"] = time_range["granularity"]

        return [output]
