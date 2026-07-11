from __future__ import annotations

import json
import urllib.request
from typing import Any


class CubeClient:
    def __init__(
        self,
        base_url: str,
        api_token: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def meta(self) -> dict[str, Any]:
        return self._request("GET", "/cubejs-api/v1/meta")

    def load(self, query: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/cubejs-api/v1/load", {"query": query})

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

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read())
