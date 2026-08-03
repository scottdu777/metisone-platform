from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from metisone_ai_platform.core.env import load_project_env
from metisone_ai_platform.semantic_edit.llm.contracts import (
    LLMPlan,
    SemanticEditPlanner,
)
from metisone_ai_platform.semantic_edit.mcp.contracts import ToolCall

load_project_env()


class OpenAISemanticPlanner(SemanticEditPlanner):
    """OpenAI-backed planner that emits MCP-style tool calls as JSON."""

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def plan(
        self,
        message: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> LLMPlan:
        content = self._call_openai(message, tools, context or {})
        payload = self._parse_json(content)
        return self._to_plan(payload, tools)

    def _call_openai(
        self,
        message: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> str:
        request_payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a semantic layer edit planner. Convert the user's "
                        "request into zero or more tool calls. Return only JSON with "
                        "this shape: {\"tool_calls\":[{\"name\":\"tool_name\","
                        "\"arguments\":{}}],\"response_hint\":\"short message\"}. "
                        "Only use tools from the provided tool list. If information is "
                        "missing, return no tool calls and explain the missing fields in "
                        "response_hint. Do not invent cube names when available context "
                        "contains cube names. For create_dimension requests, infer "
                        "snake_case SQL identifiers from human names when the request is "
                        "clear, for example first name -> first_name, last name -> "
                        "last_name, full name -> full_name. For create_dimension SQL, "
                        "always reference current-cube columns with {CUBE}. For example, "
                        "use CONCAT({CUBE}.first_name, ' ', {CUBE}.last_name), not "
                        "${actor.first_name} or actor.first_name. If you need to inspect "
                        "read-only tools first, use observations from prior tool results "
                        "in the context to finish the requested edit in the next plan. "
                        "For broad requests asking to inspect the database schema and "
                        "fix or complete primary keys, foreign keys, joins, or all Cube "
                        "YAML models, prefer one auto_complete tool call with "
                        "apply=true and bidirectional_joins=true instead of editing one "
                        "cube at a time. For requests that only ask to fix invalid "
                        "pre_aggregations, rollup, or JavaScript-like Cube UI model "
                        "snippets in YAML files, prefer normalize_models with "
                        "apply=true because it does not require database inspection. "
                        "For requests asking to create a new pre_aggregation, "
                        "rollup, cached aggregate, or monthly/daily/yearly aggregate, "
                        "use create_pre_aggregation. Prefer YAML-style fields: "
                        "measures, dimensions, segments, time_dimension, granularity, "
                        "partition_granularity, refresh_key, and scheduled_refresh. "
                        "Use fully-qualified Cube members such as payment.count and "
                        "payment.payment_date. Do not return JavaScript object syntax."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_request": message,
                            "available_tools": tools,
                            "context": context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        data = json.dumps(request_payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI planner request failed with HTTP {exc.code}: {detail}") from exc

        try:
            return response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"OpenAI planner returned an unexpected payload: {response_payload}") from exc

    def _parse_json(self, content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAI planner did not return valid JSON: {content}") from exc
        if not isinstance(payload, dict):
            raise ValueError("OpenAI planner JSON must be an object.")
        return payload

    def _to_plan(self, payload: dict[str, Any], tools: list[dict[str, Any]]) -> LLMPlan:
        allowed_tools = {tool["name"] for tool in tools if "name" in tool}
        raw_calls = payload.get("tool_calls", [])
        if not isinstance(raw_calls, list):
            raise ValueError("OpenAI planner field `tool_calls` must be a list.")

        calls: list[ToolCall] = []
        for raw_call in raw_calls:
            if not isinstance(raw_call, dict):
                raise ValueError("Each tool call must be an object.")
            name = raw_call.get("name")
            arguments = raw_call.get("arguments", {})
            if name not in allowed_tools:
                raise ValueError(f"OpenAI planner selected unknown tool: {name}")
            if not isinstance(arguments, dict):
                raise ValueError(f"Arguments for tool {name} must be an object.")
            calls.append(ToolCall(name=name, arguments=arguments))

        response_hint = payload.get("response_hint")
        if response_hint is not None and not isinstance(response_hint, str):
            response_hint = str(response_hint)
        return LLMPlan(tool_calls=calls, response_hint=response_hint)
