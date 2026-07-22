from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from metisone_ai_platform.observability import (
    JsonRequestLogConfig,
    install_json_request_logging,
)
from metisone_ai_platform.semantic_query.config import (
    DataQueryServiceConfig,
    load_config_from_env,
)
from metisone_ai_platform.semantic_query.cube_client import CubeRestDataQueryClient
from metisone_ai_platform.semantic_query.models import DataQueryRequest
from metisone_ai_platform.semantic_query.orchestrator import DataQueryOrchestrator
from metisone_ai_platform.semantic_query.planner import OpenAIDataQueryPlanner
from metisone_ai_platform.semantic_query.presentation import format_query_answer


class QueryRequest(BaseModel):
    question: str
    limit: int = Field(default=100, ge=1, le=500)


def create_app(
    config: DataQueryServiceConfig | None = None,
    orchestrator: DataQueryOrchestrator | None = None,
    request_log_config: JsonRequestLogConfig | None = None,
) -> FastAPI:
    resolved_config = config or load_config_from_env()
    resolved_orchestrator = orchestrator or DataQueryOrchestrator(
        planner=OpenAIDataQueryPlanner(),
        client=CubeRestDataQueryClient(
            base_url=resolved_config.cube_api_url,
            api_token=resolved_config.cube_api_token,
        ),
    )
    app = FastAPI(title="MetisOne Semantic Data Query Service", version="0.1.0")
    install_json_request_logging(
        app,
        service_name="semantic_data_query_service",
        paths=("/v1/query",),
        config=request_log_config,
    )

    def require_token(authorization: str | None = Header(default=None)) -> None:
        if not resolved_config.api_token:
            return
        if authorization != f"Bearer {resolved_config.api_token}":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API token.",
            )

    auth_dependency = Depends(require_token)

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "cube_api_url": resolved_config.cube_api_url}

    @app.post("/v1/query", dependencies=[auth_dependency])
    def query(request: QueryRequest) -> dict[str, Any]:
        response = resolved_orchestrator.ask(
            DataQueryRequest(question=request.question, limit=request.limit)
        )
        if response.status == "error":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=response.error or "Data query failed.",
            )
        cube_query = (
            response.plan.cube_query.to_cube_payload() if response.plan else None
        )
        cube_response = response.result.raw_response if response.result else None
        return {
            "status": response.status,
            "message": response.message,
            "answer": format_query_answer(
                response.result.rows if response.result else [],
                question=request.question,
                response_hint=response.plan.response_hint if response.plan else None,
            ),
            "plan": {
                "response_hint": response.plan.response_hint if response.plan else None,
            },
            "cube_request": {
                "endpoint": "/load",
                "method": "POST",
                "query": cube_query,
            },
            "cube_response": cube_response,
            "result": {
                "rows": response.result.rows if response.result else [],
                "row_count": response.result.row_count if response.result else 0,
                "annotation": response.result.annotation if response.result else {},
            },
        }

    return app
