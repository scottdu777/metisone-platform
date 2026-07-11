from __future__ import annotations

from typing import Any, Callable

from metisone_ai_platform.semantic_layer.edit_service.client import (
    SemanticEditServiceClient,
)
from metisone_ai_platform.semantic_layer.mcp.contracts import (
    MCPServer,
    ToolCall,
    ToolResult,
)


class SemanticLayerEditMCPServer(MCPServer):
    """MCP-style tool server over the remote Semantic Layer Edit Service."""

    def __init__(self, edit_client: SemanticEditServiceClient) -> None:
        self.edit_client = edit_client
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "list_cubes": lambda args: self.edit_client.list_cubes(),
            "get_cube": lambda args: self.edit_client.get_cube(args["cube"]),
            "list_measures": lambda args: self.edit_client.list_measures(args["cube"]),
            "create_measure": self._create_measure,
            "modify_measure": self._modify_measure,
            "delete_measure": self._delete_measure,
            "list_dimensions": lambda args: self.edit_client.list_dimensions(args["cube"]),
            "create_dimension": self._create_dimension,
            "modify_dimension": self._modify_dimension,
            "delete_dimension": self._delete_dimension,
            "list_joins": lambda args: self.edit_client.list_joins(args["cube"]),
            "create_join": self._create_join,
            "modify_join": self._modify_join,
            "delete_join": self._delete_join,
            "compile": lambda args: self.edit_client.compile(),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            self._tool("list_cubes", "List all available Cube models.", {}),
            self._tool("get_cube", "Read one Cube model by name.", {"cube": "string"}),
            self._tool("list_measures", "List measures in a cube.", {"cube": "string"}),
            self._tool(
                "create_measure",
                "Create a measure in a cube.",
                {
                    "cube": "string",
                    "name": "string",
                    "sql": "string",
                    "type": "string",
                    "title": "string?",
                    "description": "string?",
                },
            ),
            self._tool(
                "modify_measure",
                "Modify fields on an existing measure.",
                {"cube": "string", "name": "string", "fields": "object"},
            ),
            self._tool(
                "delete_measure",
                "Delete a measure from a cube.",
                {"cube": "string", "name": "string"},
            ),
            self._tool("list_dimensions", "List dimensions in a cube.", {"cube": "string"}),
            self._tool(
                "create_dimension",
                "Create a dimension in a cube.",
                {
                    "cube": "string",
                    "name": "string",
                    "sql": "string",
                    "type": "string",
                    "title": "string?",
                    "description": "string?",
                },
            ),
            self._tool(
                "modify_dimension",
                "Modify fields on an existing dimension.",
                {"cube": "string", "name": "string", "fields": "object"},
            ),
            self._tool(
                "delete_dimension",
                "Delete a dimension from a cube.",
                {"cube": "string", "name": "string"},
            ),
            self._tool("list_joins", "List joins in a cube.", {"cube": "string"}),
            self._tool(
                "create_join",
                "Create a join in a cube.",
                {
                    "cube": "string",
                    "name": "string",
                    "sql": "string",
                    "relationship": "string",
                },
            ),
            self._tool(
                "modify_join",
                "Modify fields on an existing join.",
                {"cube": "string", "name": "string", "fields": "object"},
            ),
            self._tool(
                "delete_join",
                "Delete a join from a cube.",
                {"cube": "string", "name": "string"},
            ),
            self._tool("compile", "Trigger configured Cube compile/reload command.", {}),
        ]

    def call_tool(self, call: ToolCall) -> ToolResult:
        handler = self._handlers.get(call.name)
        if handler is None:
            return ToolResult(
                name=call.name,
                success=False,
                error=f"Unknown tool: {call.name}",
            )

        try:
            return ToolResult(name=call.name, success=True, data=handler(call.arguments))
        except Exception as exc:
            return ToolResult(name=call.name, success=False, error=str(exc))

    def _create_measure(self, args: dict[str, Any]) -> Any:
        return self.edit_client.create_measure(
            args["cube"],
            args["name"],
            args["sql"],
            args["type"],
            extra_fields=self._extra_fields(args),
        )

    def _modify_measure(self, args: dict[str, Any]) -> Any:
        return self.edit_client.modify_measure(args["cube"], args["name"], args["fields"])

    def _delete_measure(self, args: dict[str, Any]) -> Any:
        return self.edit_client.delete_measure(args["cube"], args["name"])

    def _create_dimension(self, args: dict[str, Any]) -> Any:
        return self.edit_client.create_dimension(
            args["cube"],
            args["name"],
            args["sql"],
            args["type"],
            extra_fields=self._extra_fields(args),
        )

    def _modify_dimension(self, args: dict[str, Any]) -> Any:
        return self.edit_client.modify_dimension(args["cube"], args["name"], args["fields"])

    def _delete_dimension(self, args: dict[str, Any]) -> Any:
        return self.edit_client.delete_dimension(args["cube"], args["name"])

    def _create_join(self, args: dict[str, Any]) -> Any:
        return self.edit_client.create_join(
            args["cube"],
            args["name"],
            args["sql"],
            args["relationship"],
            extra_fields=self._extra_fields(args),
        )

    def _modify_join(self, args: dict[str, Any]) -> Any:
        return self.edit_client.modify_join(args["cube"], args["name"], args["fields"])

    def _delete_join(self, args: dict[str, Any]) -> Any:
        return self.edit_client.delete_join(args["cube"], args["name"])

    def _extra_fields(self, args: dict[str, Any]) -> dict[str, Any]:
        reserved = {"cube", "name", "sql", "type", "relationship", "fields"}
        return {
            key: value
            for key, value in args.items()
            if key not in reserved and value is not None
        }

    def _tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
