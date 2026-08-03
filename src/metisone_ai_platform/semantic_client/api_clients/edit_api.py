from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from metisone_ai_platform.core.env import load_project_env

load_project_env()

DEFAULT_EDIT_SERVICE_URL = os.getenv("SEMANTIC_EDIT_SERVICE_URL", "http://127.0.0.1:8088")


class SemanticEditServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("SEMANTIC_EDIT_SERVICE_URL")
            or DEFAULT_EDIT_SERVICE_URL
        ).rstrip("/")
        self.api_token = api_token or os.getenv("SEMANTIC_EDIT_SERVICE_TOKEN")
        self.timeout_seconds = timeout_seconds

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health", requires_auth=False)

    def list_cubes(self) -> list[dict[str, Any]]:
        return self._request("GET", "/v1/cubes")

    def get_cube(self, cube: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/cubes/{cube}")

    def list_measures(self, cube: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/v1/cubes/{cube}/measures")

    def create_measure(
        self,
        cube: str,
        name: str,
        sql: str,
        measure_type: str,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/cubes/{cube}/measures",
            {
                "name": name,
                "sql": sql,
                "type": measure_type,
                "extra_fields": extra_fields or {},
            },
        )

    def modify_measure(
        self,
        cube: str,
        name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/v1/cubes/{cube}/measures/{name}",
            {"fields": fields},
        )

    def delete_measure(self, cube: str, name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/cubes/{cube}/measures/{name}")

    def list_dimensions(self, cube: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/v1/cubes/{cube}/dimensions")

    def create_dimension(
        self,
        cube: str,
        name: str,
        sql: str,
        dimension_type: str,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/cubes/{cube}/dimensions",
            {
                "name": name,
                "sql": sql,
                "type": dimension_type,
                "extra_fields": extra_fields or {},
            },
        )

    def modify_dimension(
        self,
        cube: str,
        name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/v1/cubes/{cube}/dimensions/{name}",
            {"fields": fields},
        )

    def delete_dimension(self, cube: str, name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/cubes/{cube}/dimensions/{name}")

    def list_joins(self, cube: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/v1/cubes/{cube}/joins")

    def create_join(
        self,
        cube: str,
        name: str,
        sql: str,
        relationship: str,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/cubes/{cube}/joins",
            {
                "name": name,
                "sql": sql,
                "relationship": relationship,
                "extra_fields": extra_fields or {},
            },
        )

    def modify_join(
        self,
        cube: str,
        name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/v1/cubes/{cube}/joins/{name}",
            {"fields": fields},
        )

    def delete_join(self, cube: str, name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/cubes/{cube}/joins/{name}")

    def list_pre_aggregations(self, cube: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/v1/cubes/{cube}/pre-aggregations")

    def create_pre_aggregation(
        self,
        cube: str,
        name: str,
        pre_aggregation_type: str = "rollup",
        measures: list[str] | None = None,
        dimensions: list[str] | None = None,
        segments: list[str] | None = None,
        time_dimension: str | None = None,
        granularity: str | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/cubes/{cube}/pre-aggregations",
            {
                "name": name,
                "type": pre_aggregation_type,
                "measures": measures or [],
                "dimensions": dimensions or [],
                "segments": segments or [],
                "time_dimension": time_dimension,
                "granularity": granularity,
                "extra_fields": extra_fields or {},
            },
        )

    def modify_pre_aggregation(
        self,
        cube: str,
        name: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            "PATCH",
            f"/v1/cubes/{cube}/pre-aggregations/{name}",
            {"fields": fields},
        )

    def delete_pre_aggregation(self, cube: str, name: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/cubes/{cube}/pre-aggregations/{name}")

    def auto_complete(
        self,
        schemas: list[str] | None = None,
        apply: bool = True,
        bidirectional_joins: bool = True,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/auto-complete",
            {
                "schemas": schemas or ["public"],
                "apply": apply,
                "bidirectional_joins": bidirectional_joins,
            },
        )

    def normalize_models(self, apply: bool = True) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/normalize-models",
            {"apply": apply},
        )

    def compile(self) -> dict[str, Any]:
        return self._request("POST", "/v1/compile")

    def chat(self, message: str) -> dict[str, Any]:
        return self._request("POST", "/v1/chat", {"message": message})

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        requires_auth: bool = True,
    ) -> Any:
        data = None
        headers = {"Content-Type": "application/json"}

        if requires_auth:
            if not self.api_token:
                raise ValueError("SEMANTIC_EDIT_SERVICE_TOKEN is required.")
            headers["Authorization"] = f"Bearer {self.api_token}"

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Edit service request failed for {method} {path} "
                f"with HTTP {exc.code}: {detail}"
            ) from exc
