from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    name: str
    success: bool
    data: Any = None
    error: str | None = None


class MCPServer(ABC):
    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas the LLM can use."""

    @abstractmethod
    def call_tool(self, call: ToolCall) -> ToolResult:
        """Execute one tool call."""


class MCPClient(ABC):
    @abstractmethod
    def list_tools(self) -> list[dict[str, Any]]:
        """Return tool schemas from the server."""

    @abstractmethod
    def call_tool(self, call: ToolCall) -> ToolResult:
        """Call one tool on the server."""
