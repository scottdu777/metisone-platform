from __future__ import annotations

import os
from dataclasses import dataclass

from metisone_ai_platform.core.env import load_project_env

load_project_env()


@dataclass(frozen=True)
class DataQueryServiceConfig:
    cube_api_url: str
    cube_api_token: str | None = None
    api_token: str | None = None


def load_config_from_env() -> DataQueryServiceConfig:
    return DataQueryServiceConfig(
        cube_api_url=os.getenv(
            "CUBE_API_BASE_URL",
            "http://127.0.0.1:4000/cubejs-api/v1",
        ),
        cube_api_token=os.getenv("CUBE_API_TOKEN"),
        api_token=(
            os.getenv("SEMANTIC_DATA_QUERY_SERVICE_TOKEN")
            or os.getenv("QUERY_DATA_SERVICE_TOKEN")
        ),
    )
