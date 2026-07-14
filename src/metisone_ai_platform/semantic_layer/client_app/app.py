from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from metisone_ai_platform.data_query import (
    CubeRestDataQueryClient,
    DataQueryOrchestrator,
    DataQueryRequest,
    OpenAIDataQueryPlanner,
)
from metisone_ai_platform.data_query.cube_client import DEFAULT_CUBE_API_BASE_URL
from metisone_ai_platform.semantic_layer.client_app.llm_agent import (
    LocalLLMSemanticEditAgent,
)
from metisone_ai_platform.semantic_layer.client_app.ui import LOCAL_CHAT_UI_HTML
from metisone_ai_platform.semantic_layer.env import load_project_env
from metisone_ai_platform.semantic_layer.edit_service.client import (
    DEFAULT_EDIT_SERVICE_URL,
    SemanticEditServiceClient,
)
from metisone_ai_platform.semantic_layer.llm import LLMPlannerFactory
from metisone_ai_platform.semantic_layer.mcp.contracts import ToolCall
from metisone_ai_platform.semantic_layer.mcp.factory import MCPFactory

load_project_env()


class LocalCubesRequest(BaseModel):
    service_url: str = DEFAULT_EDIT_SERVICE_URL
    api_token: str


class LocalChatRequest(LocalCubesRequest):
    message: str


class LocalDataQueryRequest(BaseModel):
    cube_api_url: str = DEFAULT_CUBE_API_BASE_URL
    cube_api_token: str | None = None
    message: str
    limit: int = 100


def create_app() -> FastAPI:
    app = FastAPI(
        title="MetisOne Local Semantic Chat Client",
        version="0.1.0",
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return LOCAL_CHAT_UI_HTML

    @app.get("/local-config")
    def local_config() -> dict[str, Any]:
        return {
            "service_url": DEFAULT_EDIT_SERVICE_URL,
            "agent_mode": LLMPlannerFactory.mode_from_env(),
            "openai_model": LLMPlannerFactory.model_from_env(),
            "has_openai_api_key": LLMPlannerFactory.has_api_key(),
            "cube_api_url": DEFAULT_CUBE_API_BASE_URL,
        }

    @app.post("/local-cubes")
    def local_cubes(request: LocalCubesRequest) -> dict[str, Any]:
        client = SemanticEditServiceClient(
            base_url=request.service_url,
            api_token=request.api_token,
        )
        mcp_client = MCPFactory.semantic_edit_client(client)
        try:
            result = mcp_client.call_tool(ToolCall(name="list_cubes", arguments={}))
            if not result.success:
                raise RuntimeError(result.error or "Failed to list cubes.")
            return {"cubes": result.data}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/local-chat")
    def local_chat(request: LocalChatRequest) -> dict[str, Any]:
        client = SemanticEditServiceClient(
            base_url=request.service_url,
            api_token=request.api_token,
        )
        mcp_client = MCPFactory.semantic_edit_client(client)
        try:
            planner = LLMPlannerFactory.create()
            agent = LocalLLMSemanticEditAgent(planner=planner, mcp_client=mcp_client)
            return agent.handle(request.message)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/local-query")
    def local_query(request: LocalDataQueryRequest) -> dict[str, Any]:
        try:
            client = CubeRestDataQueryClient(
                base_url=request.cube_api_url,
                api_token=request.cube_api_token,
            )
            orchestrator = DataQueryOrchestrator(
                planner=OpenAIDataQueryPlanner(),
                client=client,
            )
            response = orchestrator.ask(
                DataQueryRequest(question=request.message, limit=request.limit)
            )
            if response.status == "error":
                raise RuntimeError(response.error or "Data query failed.")
            return {
                "status": response.status,
                "message": response.message,
                "plan": {
                    "cube_query": response.plan.cube_query.to_cube_payload()
                    if response.plan
                    else None,
                    "response_hint": response.plan.response_hint if response.plan else None,
                },
                "result": {
                    "rows": response.result.rows if response.result else [],
                    "row_count": response.result.row_count if response.result else 0,
                    "annotation": response.result.annotation if response.result else {},
                },
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()
