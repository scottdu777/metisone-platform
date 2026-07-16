from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LLMTraceLogConfig:
    file_path: Path | None = None
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5

    @classmethod
    def from_env(cls) -> "LLMTraceLogConfig":
        file_name = os.getenv("METISONE_LLM_TRACE_LOG_FILE")
        return cls(
            file_path=Path(file_name) if file_name else None,
            max_bytes=int(
                os.getenv("METISONE_LLM_TRACE_LOG_MAX_BYTES", str(10 * 1024 * 1024))
            ),
            backup_count=int(os.getenv("METISONE_LLM_TRACE_LOG_BACKUP_COUNT", "5")),
        )


class LLMTraceLogger:
    def __init__(self, config: LLMTraceLogConfig | None = None) -> None:
        self.config = config or LLMTraceLogConfig.from_env()
        self.logger = self._create_logger() if self.config.file_path else None

    def enabled(self) -> bool:
        return self.logger is not None

    def write(self, record: dict[str, Any]) -> None:
        if self.logger is None:
            return
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            **record,
        }
        self.logger.info(json.dumps(_redact(payload), ensure_ascii=False))

    def _create_logger(self) -> logging.Logger:
        assert self.config.file_path is not None
        self.config.file_path.parent.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(f"metisone.llm_trace.{uuid.uuid4()}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = RotatingFileHandler(
            self.config.file_path,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding="utf-8",
            delay=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        return logger


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***REDACTED***" if _is_sensitive(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _is_sensitive(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(
        marker in normalized
        for marker in ("token", "password", "secret", "api_key", "authorization")
    )
