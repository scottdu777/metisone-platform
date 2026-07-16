from __future__ import annotations

from metisone_ai_platform.semantic_edit.mcp.contracts import (
    MCPClient,
    SemanticEditGateway,
)
from metisone_ai_platform.semantic_edit.mcp.in_process_client import InProcessMCPClient
from metisone_ai_platform.semantic_edit.mcp.semantic_edit_server import (
    SemanticLayerEditMCPServer,
)


class MCPFactory:
    @staticmethod
    def semantic_edit_client(edit_client: SemanticEditGateway) -> MCPClient:
        server = SemanticLayerEditMCPServer(edit_client)
        return InProcessMCPClient(server)
