from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Awaitable, Callable

from fastapi import FastAPI


@dataclass(frozen=True)
class JsonRequestLogConfig:
    file_path: Path | None = None
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    max_body_bytes: int = 1024 * 1024

    @classmethod
    def from_env(cls) -> "JsonRequestLogConfig":
        file_name = os.getenv("METISONE_REQUEST_LOG_FILE")
        return cls(
            file_path=Path(file_name) if file_name else None,
            max_bytes=int(
                os.getenv("METISONE_REQUEST_LOG_MAX_BYTES", str(10 * 1024 * 1024))
            ),
            backup_count=int(os.getenv("METISONE_REQUEST_LOG_BACKUP_COUNT", "5")),
            max_body_bytes=int(
                os.getenv("METISONE_REQUEST_LOG_MAX_BODY_BYTES", str(1024 * 1024))
            ),
        )


def install_json_request_logging(
    app: FastAPI,
    service_name: str,
    paths: tuple[str, ...],
    config: JsonRequestLogConfig | None = None,
) -> None:
    resolved_config = config or JsonRequestLogConfig.from_env()
    if resolved_config.file_path is None:
        return
    app.add_middleware(
        JsonRequestResponseLogMiddleware,
        service_name=service_name,
        paths=paths,
        config=resolved_config,
    )


class JsonRequestResponseLogMiddleware:
    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        service_name: str,
        paths: tuple[str, ...],
        config: JsonRequestLogConfig,
    ) -> None:
        self.app = app
        self.service_name = service_name
        self.paths = paths
        self.config = config
        self.logger = _create_logger(service_name, config)

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or not self._matches(scope.get("path", "")):
            await self.app(scope, receive, send)
            return

        request_body = bytearray()
        response_body = bytearray()
        response_status = 500
        started_at = time.perf_counter()
        request_id = _request_id(scope)

        async def receive_with_capture() -> dict[str, Any]:
            message = await receive()
            if message.get("type") == "http.request":
                _append_limited(
                    request_body,
                    message.get("body", b""),
                    self.config.max_body_bytes,
                )
            return message

        async def send_with_capture(message: dict[str, Any]) -> None:
            nonlocal response_status
            if message.get("type") == "http.response.start":
                response_status = int(message.get("status", 500))
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            elif message.get("type") == "http.response.body":
                _append_limited(
                    response_body,
                    message.get("body", b""),
                    self.config.max_body_bytes,
                )
            await send(message)

        error: Exception | None = None
        try:
            await self.app(scope, receive_with_capture, send_with_capture)
        except Exception as exc:
            error = exc
            raise
        finally:
            self._write_record(
                scope=scope,
                request_id=request_id,
                status_code=response_status,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
                request_body=bytes(request_body),
                response_body=bytes(response_body),
                error=error,
            )

    def _matches(self, path: str) -> bool:
        return any(path == prefix or path.startswith(prefix) for prefix in self.paths)

    def _write_record(
        self,
        scope: dict[str, Any],
        request_id: str,
        status_code: int,
        duration_ms: float,
        request_body: bytes,
        response_body: bytes,
        error: Exception | None,
    ) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": self.service_name,
            "request_id": request_id,
            "method": scope.get("method"),
            "path": scope.get("path"),
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request": _decode_json_body(request_body, self.config.max_body_bytes),
            "response": _decode_json_body(response_body, self.config.max_body_bytes),
        }
        if error is not None:
            record["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
            }
        self.logger.info(json.dumps(_redact(record), ensure_ascii=False))


def _create_logger(service_name: str, config: JsonRequestLogConfig) -> logging.Logger:
    assert config.file_path is not None
    config.file_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"metisone.request_json.{service_name}.{uuid.uuid4()}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RotatingFileHandler(
        config.file_path,
        maxBytes=config.max_bytes,
        backupCount=config.backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def _request_id(scope: dict[str, Any]) -> str:
    for name, value in scope.get("headers", []):
        if name.lower() == b"x-request-id":
            return value.decode("ascii", errors="ignore") or uuid.uuid4().hex
    return uuid.uuid4().hex


def _append_limited(target: bytearray, chunk: bytes, limit: int) -> None:
    remaining = limit + 1 - len(target)
    if remaining > 0:
        target.extend(chunk[:remaining])


def _decode_json_body(body: bytes, limit: int) -> Any:
    if len(body) > limit:
        return {"_truncated": True, "captured_bytes": limit}
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_non_json_body": True, "size_bytes": len(body)}


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
