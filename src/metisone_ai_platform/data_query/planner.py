from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from metisone_ai_platform.data_query.contracts import DataQueryPlanner
from metisone_ai_platform.data_query.models import (
    CubeFilter,
    CubeQuery,
    DataQueryPlan,
    DataQueryRequest,
)
from metisone_ai_platform.semantic_layer.env import load_project_env

load_project_env()


class OpenAIDataQueryPlanner(DataQueryPlanner):
    """OpenAI planner that emits Cube REST /v1/load query JSON."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def plan(
        self,
        request: DataQueryRequest,
        cube_metadata: dict[str, Any],
    ) -> DataQueryPlan:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIDataQueryPlanner.")
        content = self._call_openai(request, self._compact_metadata(cube_metadata))
        payload = self._parse_json(content)
        return self._to_plan(payload, request.limit)

    def _call_openai(
        self,
        request: DataQueryRequest,
        compact_metadata: dict[str, Any],
    ) -> str:
        request_payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You convert natural-language data questions into Cube REST "
                        "/v1/load query JSON. Use Cube REST docs rules: queries are "
                        "plain JSON objects with measures, dimensions, filters, "
                        "timeDimensions, segments, limit, order, and timezone. Member "
                        "names must use cube_name.member_name, and must come only from "
                        "the provided Cube /v1/meta metadata. Filters use member, "
                        "operator, and optional string values. For exact lookups use "
                        "operator equals. Return only JSON with this shape: "
                        "{\"query\":{...},\"response_hint\":\"short message\"}. "
                        "Do not include SQL. Do not invent members. If the question "
                        "asks whether a record exists, select identifying dimensions "
                        "and limit 1."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": request.question,
                            "default_limit": request.limit,
                            "cube_metadata": compact_metadata,
                            "examples": [
                                {
                                    "question": "Is there a film called Academy Dinosaur?",
                                    "query": {
                                        "dimensions": ["film.title"],
                                        "filters": [
                                            {
                                                "member": "film.title",
                                                "operator": "equals",
                                                "values": ["Academy Dinosaur"],
                                            }
                                        ],
                                        "limit": 1,
                                    },
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        data = json.dumps(request_payload).encode("utf-8")
        http_request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI data query planner failed with HTTP {exc.code}: {detail}") from exc

        try:
            return response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"OpenAI returned an unexpected payload: {response_payload}") from exc

    def _compact_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        cubes = []
        for cube in metadata.get("cubes", []):
            if not isinstance(cube, dict):
                continue
            cubes.append(
                {
                    "name": cube.get("name"),
                    "title": cube.get("title"),
                    "measures": self._members(cube.get("measures")),
                    "dimensions": self._members(cube.get("dimensions")),
                    "segments": self._members(cube.get("segments")),
                }
            )
        return {"cubes": cubes}

    def _members(self, items: Any) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [
            {
                "name": item.get("name"),
                "title": item.get("title"),
                "type": item.get("type"),
                "description": item.get("description"),
            }
            for item in items
            if isinstance(item, dict) and item.get("name")
        ]

    def _parse_json(self, content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI did not return valid JSON: {content}") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI data query planner JSON must be an object.")
        return payload

    def _to_plan(self, payload: dict[str, Any], default_limit: int) -> DataQueryPlan:
        raw_query = payload.get("query")
        if not isinstance(raw_query, dict):
            raise ValueError("OpenAI data query planner must return a query object.")

        filters = [
            CubeFilter(
                member=str(item["member"]),
                operator=str(item["operator"]),
                values=[str(value) for value in item.get("values", [])],
            )
            for item in raw_query.get("filters", [])
            if isinstance(item, dict) and item.get("member") and item.get("operator")
        ]
        query = CubeQuery(
            measures=[str(item) for item in raw_query.get("measures", [])],
            dimensions=[str(item) for item in raw_query.get("dimensions", [])],
            filters=filters,
            time_dimensions=list(raw_query.get("timeDimensions", [])),
            segments=[str(item) for item in raw_query.get("segments", [])],
            limit=int(raw_query.get("limit") or default_limit),
            order=dict(raw_query.get("order", {})),
        )
        response_hint = payload.get("response_hint")
        return DataQueryPlan(
            cube_query=query,
            response_hint=response_hint if isinstance(response_hint, str) else None,
        )
