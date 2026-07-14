from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from metisone_ai_platform.semantic_layer.env import load_project_env

load_project_env()


DEFAULT_CUBE_API_BASE_URL = os.getenv(
    "CUBE_API_BASE_URL",
    "http://127.0.0.1:4000/cubejs-api/v1",
)


class CubeRestDataQueryClient:
    """Small stdlib client for Cube REST /meta and /load endpoints."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = (base_url or os.getenv("CUBE_API_BASE_URL") or DEFAULT_CUBE_API_BASE_URL).rstrip("/")
        self.api_token = api_token or os.getenv("CUBE_API_TOKEN")
        self.timeout_seconds = timeout_seconds

    def meta(self) -> dict[str, Any]:
        return self._request("GET", "/meta")

    def load(self, query: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/load", {"query": query})

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = self.api_token

        url = f"{self.base_url}{path}"
        if method == "GET" and payload:
            url = f"{url}?{urllib.parse.urlencode(payload)}"
        elif payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Cube REST request failed for {method} {path} "
                f"with HTTP {exc.code}: {detail}"
            ) from exc
