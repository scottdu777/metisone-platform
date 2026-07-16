from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from metisone_ai_platform.core.env import load_project_env

load_project_env()

DEFAULT_QUERY_SERVICE_URL = os.getenv(
    "SEMANTIC_DATA_QUERY_SERVICE_URL",
    "http://127.0.0.1:8091",
)


class SemanticDataQueryServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("SEMANTIC_DATA_QUERY_SERVICE_URL")
            or DEFAULT_QUERY_SERVICE_URL
        ).rstrip("/")
        self.api_token = api_token or os.getenv(
            "SEMANTIC_DATA_QUERY_SERVICE_TOKEN"
        )
        self.timeout_seconds = timeout_seconds

    def query(self, question: str, limit: int = 100) -> dict[str, Any]:
        if not self.api_token:
            raise ValueError("SEMANTIC_DATA_QUERY_SERVICE_TOKEN is required.")
        request = urllib.request.Request(
            f"{self.base_url}/v1/query",
            data=json.dumps({"question": question, "limit": limit}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Semantic data query failed with HTTP {exc.code}: {detail}"
            ) from exc
