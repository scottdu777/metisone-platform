from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from metisone_ai_platform.semantic_client.api_clients.query_api import (
    DEFAULT_QUERY_SERVICE_URL,
    SemanticDataQueryServiceClient,
)
from metisone_ai_platform.observability import (
    JsonRequestLogConfig,
    install_json_request_logging,
)
from metisone_ai_platform.semantic_client.llm_agent import (
    LocalLLMSemanticEditAgent,
)
from metisone_ai_platform.semantic_client.ui import LOCAL_CHAT_UI_HTML
from metisone_ai_platform.core.env import load_project_env
from metisone_ai_platform.semantic_client.api_clients.edit_api import (
    DEFAULT_EDIT_SERVICE_URL,
    SemanticEditServiceClient,
)
from metisone_ai_platform.semantic_edit.llm import LLMPlannerFactory
from metisone_ai_platform.semantic_edit.mcp.factory import MCPFactory

load_project_env()


class LocalChatRequest(BaseModel):
    message: str
    mode: Literal["edit", "query"] = "edit"


def create_app(
    query_client: SemanticDataQueryServiceClient | None = None,
    request_log_config: JsonRequestLogConfig | None = None,
) -> FastAPI:
    resolved_query_client = query_client or SemanticDataQueryServiceClient()
    app = FastAPI(
        title="MetisOne Semantic Client",
        version="0.1.0",
    )
    install_json_request_logging(
        app,
        service_name="semantic_client",
        paths=("/local-chat",),
        config=request_log_config,
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return LOCAL_CHAT_UI_HTML

    @app.get("/local-config")
    def local_config() -> dict[str, Any]:
        return {
            "edit_service_url": DEFAULT_EDIT_SERVICE_URL,
            "query_service_url": DEFAULT_QUERY_SERVICE_URL,
            "agent_mode": LLMPlannerFactory.mode_from_env(),
            "openai_model": LLMPlannerFactory.model_from_env(),
            "has_openai_api_key": LLMPlannerFactory.has_api_key(),
        }

    @app.post("/local-chat")
    def local_chat(request: LocalChatRequest) -> dict[str, Any]:
        if request.mode == "query":
            try:
                result = resolved_query_client.query(request.message)
                return {
                    "success": True,
                    "mode": "query",
                    "message": result.get("answer") or "Query completed.",
                }
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

        client = SemanticEditServiceClient()
        mcp_client = MCPFactory.semantic_edit_client(client)
        try:
            planner = LLMPlannerFactory.create()
            agent = LocalLLMSemanticEditAgent(planner=planner, mcp_client=mcp_client)
            result = agent.handle(request.message)
            return {
                "success": bool(result.get("success")),
                "mode": "edit",
                "message": _format_edit_message(result),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


def _format_edit_message(result: dict[str, Any]) -> str:
    if not result.get("success"):
        return str(result.get("message") or "Model update failed.")

    calls = result.get("tool_calls") or []
    for call in reversed(calls):
        tool_name = str(call.get("name") or "")
        arguments = call.get("arguments") or {}
        action = _EDIT_ACTIONS.get(tool_name)
        if not action:
            continue
        cube = arguments.get("cube")
        member = arguments.get("name")
        target = ".".join(str(value) for value in (cube, member) if value)
        return f"{target + ' ' if target else ''}{action} successfully."

    return str(result.get("message") or "Operation completed successfully.")


_EDIT_ACTIONS = {
    "create_measure": "created",
    "create_dimension": "created",
    "create_join": "created",
    "modify_measure": "modified",
    "modify_dimension": "modified",
    "modify_join": "modified",
    "delete_measure": "deleted",
    "delete_dimension": "deleted",
    "delete_join": "deleted",
    "compile": "compiled",
}


app = create_app()
