from __future__ import annotations

from typing import Any

from metisone_ai_platform.semantic_edit.llm.contracts import (
    LLMPlan,
    SemanticEditPlanner,
)
from metisone_ai_platform.semantic_edit.llm.rule_parser import RuleBasedSemanticParser
from metisone_ai_platform.semantic_edit.mcp.contracts import ToolCall


class RuleBasedSemanticPlanner(SemanticEditPlanner):
    """Deterministic fallback planner for local debugging without an LLM key."""

    def plan(
        self,
        message: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> LLMPlan:
        command = RuleBasedSemanticParser().parse(message)
        tool_name = f"{command.operation}_{command.member_kind}"
        arguments: dict[str, Any] = {
            "cube": command.cube,
            "name": command.member_name,
        }

        if command.operation == "create":
            if command.sql is not None:
                arguments["sql"] = command.sql
            if command.member_type is not None:
                arguments["type"] = command.member_type
            if command.relationship is not None:
                arguments["relationship"] = command.relationship
            arguments.update(command.fields)
        elif command.operation == "modify":
            arguments["fields"] = command.fields

        return LLMPlan(
            tool_calls=[ToolCall(name=tool_name, arguments=arguments)],
            response_hint="Planned with rule-based fallback.",
        )
