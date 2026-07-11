from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from metisone_ai_platform.core.models import QueryIntent, QueryRequest, SemanticModel
from metisone_ai_platform.providers.base import CapabilityProvider, LLMProvider
from metisone_ai_platform.semantic_layer.env import load_project_env

load_project_env()


class RuleBasedLLMProvider(LLMProvider, CapabilityProvider):
    """Small local provider for development and tests.

    It chooses metrics and dimensions by matching names/descriptions in the user
    question. A real LLM provider can be swapped in without changing the
    orchestrator contract.
    """

    def capabilities(self) -> set[str]:
        return {"natural_language", "intent_generation", "local"}

    def generate_intent(
        self,
        request: QueryRequest,
        models: list[SemanticModel],
    ) -> QueryIntent:
        model = self._select_model(request, models)
        text = request.question.lower()

        metrics = [
            name
            for name, metric in model.metrics.items()
            if name.lower() in text
            or (metric.description and metric.description.lower() in text)
        ]
        dimensions = [
            name
            for name, dimension in model.dimensions.items()
            if name.lower() in text
            or (dimension.description and dimension.description.lower() in text)
        ]

        if not metrics and model.metrics:
            metrics = [next(iter(model.metrics))]

        return QueryIntent(
            model_name=model.name,
            metrics=metrics,
            dimensions=dimensions,
            limit=request.limit,
        )

    def _select_model(
        self,
        request: QueryRequest,
        models: list[SemanticModel],
    ) -> SemanticModel:
        if not models:
            raise ValueError("No semantic models are available.")

        if request.model_name:
            for model in models:
                if model.name == request.model_name:
                    return model
            raise ValueError(f"Unknown semantic model: {request.model_name}")

        return models[0]


class OpenAIChatLLMProvider(LLMProvider, CapabilityProvider):
    """OpenAI-compatible intent provider using only Python stdlib HTTP."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.base_url = (
            base_url
            or os.getenv("OPENAI_CHAT_COMPLETIONS_URL")
            or f"{(os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com').rstrip('/')}/v1/chat/completions"
        )

    def capabilities(self) -> set[str]:
        return {"natural_language", "intent_generation", "remote_llm"}

    def generate_intent(
        self,
        request: QueryRequest,
        models: list[SemanticModel],
    ) -> QueryIntent:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIChatLLMProvider.")

        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only JSON for a BI query intent. "
                        "Schema: model_name string, metrics string[], "
                        "dimensions string[], filters object[], time_range object|null."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": request.question,
                            "preferred_model": request.model_name,
                            "limit": request.limit,
                            "semantic_models": [
                                {
                                    "name": model.name,
                                    "table": model.table,
                                    "metrics": list(model.metrics),
                                    "dimensions": list(model.dimensions),
                                }
                                for model in models
                            ],
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(http_request, timeout=30) as response:
            response_payload: dict[str, Any] = json.loads(response.read())

        content = response_payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        return QueryIntent(
            model_name=parsed["model_name"],
            metrics=parsed.get("metrics", []),
            dimensions=parsed.get("dimensions", []),
            filters=parsed.get("filters", []),
            time_range=parsed.get("time_range"),
            limit=request.limit,
        )
