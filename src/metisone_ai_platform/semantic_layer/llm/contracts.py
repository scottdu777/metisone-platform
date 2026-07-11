from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from metisone_ai_platform.semantic_layer.mcp.contracts import ToolCall


@dataclass(frozen=True)
class LLMPlan:
    tool_calls: list[ToolCall] = field(default_factory=list)
    response_hint: str | None = None


class SemanticEditPlanner(ABC):
    """Convert a natural language edit request into MCP tool calls."""

    @abstractmethod
    def plan(
        self,
        message: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> LLMPlan:
        """Return the tool calls needed to satisfy the user's request."""
