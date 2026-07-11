from __future__ import annotations

from metisone_ai_platform.semantic_layer.mcp.contracts import (
    MCPClient,
    MCPServer,
    ToolCall,
    ToolResult,
)


class InProcessMCPClient(MCPClient):
    """MCP client that calls an MCP server object in-process.

    This keeps the Local Chat UI simple while preserving an MCP-like boundary.
    A JSON-RPC or stdio MCP client can replace this class later.
    """

    def __init__(self, server: MCPServer) -> None:
        self.server = server

    def list_tools(self) -> list[dict]:
        return self.server.list_tools()

    def call_tool(self, call: ToolCall) -> ToolResult:
        return self.server.call_tool(call)
