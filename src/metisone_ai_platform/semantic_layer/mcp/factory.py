from __future__ import annotations

from metisone_ai_platform.semantic_layer.edit_service.client import (
    SemanticEditServiceClient,
)
from metisone_ai_platform.semantic_layer.mcp.contracts import MCPClient
from metisone_ai_platform.semantic_layer.mcp.in_process_client import InProcessMCPClient
from metisone_ai_platform.semantic_layer.mcp.semantic_edit_server import (
    SemanticLayerEditMCPServer,
)


class MCPFactory:
    @staticmethod
    def semantic_edit_client(edit_client: SemanticEditServiceClient) -> MCPClient:
        server = SemanticLayerEditMCPServer(edit_client)
        return InProcessMCPClient(server)
