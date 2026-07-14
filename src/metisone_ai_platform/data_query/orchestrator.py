from __future__ import annotations

from metisone_ai_platform.data_query.contracts import DataQueryClient, DataQueryPlanner
from metisone_ai_platform.data_query.models import (
    DataQueryRequest,
    DataQueryResponse,
    DataQueryResult,
)
from metisone_ai_platform.data_query.validator import CubeQueryValidator


class DataQueryOrchestrator:
    def __init__(
        self,
        planner: DataQueryPlanner,
        client: DataQueryClient,
        validator: CubeQueryValidator | None = None,
    ) -> None:
        self.planner = planner
        self.client = client
        self.validator = validator or CubeQueryValidator()

    def ask(self, request: DataQueryRequest) -> DataQueryResponse:
        try:
            metadata = self.client.meta()
            plan = self.planner.plan(request, metadata)
            self.validator.validate(plan.cube_query, metadata)
            raw_response = self.client.load(plan.cube_query.to_cube_payload())
            rows = raw_response.get("data") or []
            if not isinstance(rows, list):
                raise ValueError("Cube /v1/load response field `data` must be a list.")
            return DataQueryResponse(
                status="success",
                request=request,
                plan=plan,
                result=DataQueryResult(
                    rows=rows,
                    row_count=len(rows),
                    annotation=raw_response.get("annotation") or {},
                    raw_response=raw_response,
                ),
                message=plan.response_hint or "Data query completed.",
            )
        except Exception as exc:
            return DataQueryResponse(
                status="error",
                request=request,
                error=str(exc),
            )
