"""Runtime configuration for ScratchBird AI service wiring."""

from __future__ import annotations

import os
from dataclasses import dataclass


_ALLOWED_MODES = {"mock", "http", "hybrid"}


def _parse_csv(value: str) -> tuple[str, ...]:
    parts = [item.strip() for item in value.split(",")]
    return tuple(item for item in parts if item)


@dataclass(slots=True)
class RuntimeSettings:
    adapter_mode: str = "mock"
    http_base_url: str = "http://127.0.0.1:3095"
    http_timeout_sec: float = 10.0
    http_api_token: str | None = None
    http_dialects: tuple[str, ...] = ("native",)
    retrieval_catalog_path: str | None = None
    remote_mcp_auth_token: str | None = None
    remote_mcp_session_ttl_sec: int = 900
    remote_mcp_heartbeat_interval_sec: int = 30
    remote_mcp_protocol_versions: tuple[str, ...] = ("v0",)
    remote_mcp_supported_transports: tuple[str, ...] = (
        "https_json_request_response",
        "https_sse_server_stream",
    )

    def normalized_mode(self) -> str:
        mode = self.adapter_mode.strip().lower()
        return mode if mode in _ALLOWED_MODES else "mock"

    def should_use_http_for_dialect(self, dialect: str) -> bool:
        mode = self.normalized_mode()
        if mode == "mock":
            return False
        if mode == "http":
            return True
        # hybrid mode
        return dialect in set(self.http_dialects)



def load_runtime_settings() -> RuntimeSettings:
    mode = os.getenv("SCRATCHBIRD_AI_ADAPTER_MODE", "mock").strip().lower()
    if mode not in _ALLOWED_MODES:
        mode = "mock"

    base_url = os.getenv("SCRATCHBIRD_AI_HTTP_BASE_URL", "http://127.0.0.1:3095").strip()

    timeout_raw = os.getenv("SCRATCHBIRD_AI_HTTP_TIMEOUT_SEC", "10")
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 10.0

    api_token = os.getenv("SCRATCHBIRD_AI_HTTP_API_TOKEN", "").strip() or None
    retrieval_catalog_path = os.getenv("SCRATCHBIRD_AI_RETRIEVAL_CATALOG_PATH", "").strip() or None

    dialects_raw = os.getenv(
        "SCRATCHBIRD_AI_HTTP_DIALECTS",
        "native",
    )
    dialects = _parse_csv(dialects_raw)

    remote_auth_token = os.getenv("SCRATCHBIRD_AI_REMOTE_MCP_AUTH_TOKEN", "").strip() or None

    ttl_raw = os.getenv("SCRATCHBIRD_AI_REMOTE_MCP_SESSION_TTL_SEC", "900")
    try:
        remote_ttl = int(ttl_raw)
    except ValueError:
        remote_ttl = 900

    heartbeat_raw = os.getenv("SCRATCHBIRD_AI_REMOTE_MCP_HEARTBEAT_INTERVAL_SEC", "30")
    try:
        remote_heartbeat = int(heartbeat_raw)
    except ValueError:
        remote_heartbeat = 30

    protocol_versions = _parse_csv(
        os.getenv("SCRATCHBIRD_AI_REMOTE_MCP_PROTOCOL_VERSIONS", "v0")
    )
    supported_transports = _parse_csv(
        os.getenv(
            "SCRATCHBIRD_AI_REMOTE_MCP_SUPPORTED_TRANSPORTS",
            "https_json_request_response,https_sse_server_stream",
        )
    )

    return RuntimeSettings(
        adapter_mode=mode,
        http_base_url=base_url,
        http_timeout_sec=timeout,
        http_api_token=api_token,
        http_dialects=dialects,
        retrieval_catalog_path=retrieval_catalog_path,
        remote_mcp_auth_token=remote_auth_token,
        remote_mcp_session_ttl_sec=remote_ttl,
        remote_mcp_heartbeat_interval_sec=remote_heartbeat,
        remote_mcp_protocol_versions=protocol_versions or ("v0",),
        remote_mcp_supported_transports=(
            supported_transports or ("https_json_request_response", "https_sse_server_stream")
        ),
    )
