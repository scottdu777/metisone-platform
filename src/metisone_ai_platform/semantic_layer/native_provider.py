from __future__ import annotations

from typing import Any

from metisone_ai_platform.core.models import CompiledQuery, QueryIntent
from metisone_ai_platform.providers.base import CapabilityProvider
from metisone_ai_platform.semantic_layer.contracts import SemanticProvider
from metisone_ai_platform.semantic_layer.models import Dimension, Metric, SemanticModel


class NativeSemanticProvider(SemanticProvider, CapabilityProvider):
    def __init__(self, models: list[SemanticModel]) -> None:
        self._models = {model.name: model for model in models}

    def capabilities(self) -> set[str]:
        return {"metadata", "metrics", "dimensions", "compile_sql"}

    def list_models(self) -> list[SemanticModel]:
        return list(self._models.values())

    def get_model(self, model_name: str) -> SemanticModel:
        try:
            return self._models[model_name]
        except KeyError as exc:
            raise ValueError(f"Unknown semantic model: {model_name}") from exc

    def compile(self, intent: QueryIntent) -> CompiledQuery:
        model = self.get_model(intent.model_name)
        selected_metrics = self._resolve_metrics(model, intent.metrics)
        selected_dimensions = self._resolve_dimensions(model, intent.dimensions)

        select_parts: list[str] = []
        group_by_parts: list[str] = []

        for dimension in selected_dimensions:
            select_parts.append(f"{dimension.expression} AS {dimension.name}")
            group_by_parts.append(dimension.expression)

        for metric in selected_metrics:
            select_parts.append(f"{self._compile_metric(metric)} AS {metric.name}")

        if not select_parts:
            raise ValueError("Query must include at least one metric or dimension.")

        sql_parts = [
            "SELECT",
            ", ".join(select_parts),
            "FROM",
            model.table,
        ]

        where_sql, parameters = self._compile_filters(intent.filters)
        if where_sql:
            sql_parts.extend(["WHERE", where_sql])

        if group_by_parts:
            sql_parts.extend(["GROUP BY", ", ".join(group_by_parts)])

        sql_parts.extend(["LIMIT", "%(limit)s"])
        parameters["limit"] = intent.limit

        return CompiledQuery(sql=" ".join(sql_parts), parameters=parameters)

    def _resolve_metrics(
        self,
        model: SemanticModel,
        metric_names: list[str],
    ) -> list[Metric]:
        unknown = [name for name in metric_names if name not in model.metrics]
        if unknown:
            raise ValueError(f"Unknown metrics for {model.name}: {', '.join(unknown)}")
        return [model.metrics[name] for name in metric_names]

    def _resolve_dimensions(
        self,
        model: SemanticModel,
        dimension_names: list[str],
    ) -> list[Dimension]:
        unknown = [name for name in dimension_names if name not in model.dimensions]
        if unknown:
            raise ValueError(
                f"Unknown dimensions for {model.name}: {', '.join(unknown)}"
            )
        return [model.dimensions[name] for name in dimension_names]

    def _compile_metric(self, metric: Metric) -> str:
        if metric.aggregation == "count_distinct":
            return f"COUNT(DISTINCT {metric.expression})"
        return f"{metric.aggregation.upper()}({metric.expression})"

    def _compile_filters(
        self,
        filters: list[dict[str, Any]],
    ) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        parameters: dict[str, Any] = {}

        for index, item in enumerate(filters):
            field = item["field"]
            operator = item.get("operator", "=")
            value = item.get("value")
            param_name = f"filter_{index}"

            if operator.lower() == "in":
                clauses.append(f"{field} = ANY(%({param_name})s)")
            else:
                clauses.append(f"{field} {operator} %({param_name})s")

            parameters[param_name] = value

        return " AND ".join(clauses), parameters
