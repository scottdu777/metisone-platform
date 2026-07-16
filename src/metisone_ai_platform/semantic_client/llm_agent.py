from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any

from metisone_ai_platform.semantic_edit.llm.contracts import SemanticEditPlanner
from metisone_ai_platform.semantic_edit.mcp.contracts import (
    MCPClient,
    ToolCall,
    ToolResult,
)

READ_ONLY_TOOLS = {
    "list_cubes",
    "get_cube",
    "list_measures",
    "list_dimensions",
    "list_joins",
}


class LocalLLMSemanticEditAgent:
    """Local agent that plans with an LLM and executes through MCP."""

    def __init__(self, planner: SemanticEditPlanner, mcp_client: MCPClient) -> None:
        self.planner = planner
        self.mcp_client = mcp_client

    def handle(self, message: str, max_planning_rounds: int = 3) -> dict[str, Any]:
        tools = self.mcp_client.list_tools()
        context = self._load_context()
        all_calls: list[ToolCall] = []
        all_results: list[ToolResult] = []
        seen_read_calls: set[tuple[str, tuple[tuple[str, Any], ...]]] = set()

        for _ in range(max_planning_rounds):
            plan = self.planner.plan(message, tools, deepcopy(context))

            if not plan.tool_calls:
                return {
                    "success": False,
                    "message": plan.response_hint or "I need more information before editing the model.",
                    "tool_calls": [asdict(call) for call in all_calls],
                    "tool_results": [asdict(result) for result in all_results],
                    "context": context,
                }

            results = [self.mcp_client.call_tool(call) for call in plan.tool_calls]
            all_calls.extend(plan.tool_calls)
            all_results.extend(results)
            success = all(result.success for result in results)

            self._append_observations(context, plan.tool_calls, results)

            if not success or any(call.name not in READ_ONLY_TOOLS for call in plan.tool_calls):
                return {
                    "success": success,
                    "message": self._message(success, plan.response_hint, results),
                    "tool_calls": [asdict(call) for call in all_calls],
                    "tool_results": [asdict(result) for result in all_results],
                    "context": context,
                }

            read_signatures = {self._read_signature(call) for call in plan.tool_calls}
            if read_signatures <= seen_read_calls:
                return {
                    "success": False,
                    "message": plan.response_hint or "I need more information before editing the model.",
                    "tool_calls": [asdict(call) for call in all_calls],
                    "tool_results": [asdict(result) for result in all_results],
                    "context": context,
                }
            seen_read_calls.update(read_signatures)

        return {
            "success": False,
            "message": "I reached the planning round limit before editing the model.",
            "tool_calls": [asdict(call) for call in all_calls],
            "tool_results": [asdict(result) for result in all_results],
            "context": context,
        }

    def _load_context(self) -> dict[str, Any]:
        result = self.mcp_client.call_tool(ToolCall(name="list_cubes", arguments={}))
        if result.success:
            return {"cubes": result.data}
        return {"cubes_error": result.error}

    def _append_observations(
        self,
        context: dict[str, Any],
        calls: list[ToolCall],
        results: list[ToolResult],
    ) -> None:
        observations = context.setdefault("observations", [])
        for call, result in zip(calls, results):
            observations.append(
                {
                    "tool": call.name,
                    "arguments": call.arguments,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                }
            )

    def _read_signature(self, call: ToolCall) -> tuple[str, tuple[tuple[str, Any], ...]]:
        return (call.name, tuple(sorted(call.arguments.items())))

    def _message(
        self,
        success: bool,
        response_hint: str | None,
        results: list[ToolResult],
    ) -> str:
        if success:
            return response_hint or "Semantic layer edit completed."
        errors = [result.error for result in results if result.error]
        return errors[0] if errors else "Semantic layer edit failed."
