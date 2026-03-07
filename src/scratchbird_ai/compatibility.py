"""Compatibility manifest and negotiation helpers for ScratchBird AI."""

from __future__ import annotations

from typing import Any

from .deterministic import deterministic_id
from .interface_profiles import (
    INTERFACE_COMPATIBILITY_VERSION,
    get_interface_profile_descriptors,
    get_interface_profiles,
)


SERVICE_RELEASE_VERSION = "0.1.0"
COMPATIBILITY_MANIFEST_VERSION = INTERFACE_COMPATIBILITY_VERSION
COMPATIBILITY_RELEASE_DATE = "2026-03-07"


def build_compatibility_manifest(
    *,
    adapter_mode: str,
    matrix_version: str,
) -> dict[str, Any]:
    profile_entries = []
    for profile in get_interface_profiles():
        profile_entries.append(
            {
                "component": profile["profile_id"],
                "component_version": profile["version"],
                "support_state": "supported" if profile["state"] == "implemented" else "unsupported",
                "required_conditions": [],
                "failure_reason_code": (
                    None if profile["state"] == "implemented" else "INTERFACE-NOT-IMPLEMENTED"
                ),
                "evidence_gate": profile["evidence_gate"],
            }
        )

    server_support_state = (
        "conditionally_supported" if adapter_mode in {"http", "hybrid"} else "unsupported"
    )
    server_conditions = (
        ["native_only", "bridge_contract_passes"]
        if server_support_state == "conditionally_supported"
        else []
    )

    http_bridge_state = (
        "conditionally_supported" if adapter_mode in {"http", "hybrid"} else "unsupported"
    )

    return {
        "manifest_version": COMPATIBILITY_MANIFEST_VERSION,
        "release_version": SERVICE_RELEASE_VERSION,
        "release_date": COMPATIBILITY_RELEASE_DATE,
        "compatibility_version": INTERFACE_COMPATIBILITY_VERSION,
        "interface_profiles": profile_entries,
        "server_runtime_support": [
            {
                "component": "scratchbird_server",
                "version_range": "native-http-bridge-preview",
                "support_state": server_support_state,
                "required_conditions": server_conditions,
                "failure_reason_code": (
                    None
                    if server_support_state == "conditionally_supported"
                    else "SERVER-RUNTIME-NOT-BOUND"
                ),
                "evidence_gate": "EVID-02",
            }
        ],
        "parser_compiler_support": [
            {
                "component": "native_parser_compiler",
                "version_range": "native-only",
                "support_state": "supported",
                "required_conditions": ["dialect=native"],
                "failure_reason_code": None,
                "evidence_gate": "EVID-03",
            }
        ],
        "driver_runtime_support": [
            {
                "component": "mcp_local_runtime",
                "version_range": "builtin",
                "support_state": "supported",
                "required_conditions": [],
                "failure_reason_code": None,
                "evidence_gate": "EVID-03",
            },
            {
                "component": "http_bridge_runtime",
                "version_range": "builtin",
                "support_state": http_bridge_state,
                "required_conditions": (
                    ["SCRATCHBIRD_AI_ADAPTER_MODE in {http,hybrid}"]
                    if http_bridge_state == "conditionally_supported"
                    else []
                ),
                "failure_reason_code": (
                    None
                    if http_bridge_state == "conditionally_supported"
                    else "BRIDGE-RUNTIME-NOT-ENABLED"
                ),
                "evidence_gate": "EVID-02",
            },
        ],
        "transport_support": [
            {
                "component": "in_process",
                "component_version": "v0",
                "support_state": "supported",
                "required_conditions": [],
                "failure_reason_code": None,
                "evidence_gate": "EVID-03",
            },
            {
                "component": "stdio_jsonrpc",
                "component_version": "v0",
                "support_state": "supported",
                "required_conditions": [],
                "failure_reason_code": None,
                "evidence_gate": "EVID-03",
            },
            {
                "component": "https_json_request_response",
                "component_version": "v0",
                "support_state": "unsupported",
                "required_conditions": [],
                "failure_reason_code": "TRANSPORT-NOT-IMPLEMENTED",
                "evidence_gate": None,
            },
            {
                "component": "server_stream",
                "component_version": "v0",
                "support_state": "unsupported",
                "required_conditions": [],
                "failure_reason_code": "STREAMING-NOT-IMPLEMENTED",
                "evidence_gate": None,
            },
        ],
        "notes": [
            f"adapter_mode={adapter_mode}",
            f"matrix_version={matrix_version}",
            "unknown interface profiles or transports fail closed",
            "runtime component negotiation beyond repo_release and profile transport remains conservative",
        ],
    }


def negotiate_compatibility(
    request: dict[str, Any] | None,
    *,
    adapter_mode: str,
    matrix_version: str,
) -> dict[str, Any]:
    payload = dict(request or {})
    manifest = build_compatibility_manifest(adapter_mode=adapter_mode, matrix_version=matrix_version)
    profiles = {profile.profile_id: profile for profile in get_interface_profile_descriptors()}

    request_id = str(payload.get("request_id", "")).strip() or deterministic_id(
        "req",
        {
            "operation": "negotiate_compatibility",
            "adapter_mode": adapter_mode,
            "payload": payload,
        },
    )
    requested_profile = str(payload.get("interface_profile_id", "")).strip() or "service_internal_v0"
    requested_version = str(payload.get("requested_profile_version", "")).strip() or "v0"
    requested_transport = str(payload.get("requested_transport", "")).strip()
    client_component_versions = payload.get("client_component_versions", {})
    server_component_versions = payload.get("server_component_versions", {})
    driver_runtime_versions = payload.get("driver_runtime_versions", {})

    decisions: list[dict[str, Any]] = []
    warnings: list[str] = []

    profile = profiles.get(requested_profile)
    if profile is None:
        return _blocked_response(
            request_id=request_id,
            requested_profile=requested_profile,
            requested_transport=requested_transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_INTERFACE_PROFILE_UNSUPPORTED",
            reason_code="INTERFACE-PROFILE-UNKNOWN",
            message=f"Unsupported interface profile: {requested_profile}",
        )

    decisions.append(
        {
            "domain": "interface_profile",
            "component": profile.profile_id,
            "requested": requested_version,
            "resolved": profile.version,
            "support_state": "supported" if profile.state == "implemented" else "unsupported",
            "reason_code": None if profile.state == "implemented" else "INTERFACE-NOT-IMPLEMENTED",
        }
    )
    if profile.state != "implemented":
        return _blocked_response(
            request_id=request_id,
            requested_profile=profile.profile_id,
            requested_transport=requested_transport or profile.transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_INTERFACE_PROFILE_UNSUPPORTED",
            reason_code="INTERFACE-NOT-IMPLEMENTED",
            message=f"Interface profile is not implemented: {profile.profile_id}",
        )

    if requested_version != profile.version:
        return _blocked_response(
            request_id=request_id,
            requested_profile=profile.profile_id,
            requested_transport=requested_transport or profile.transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_INTERFACE_PROFILE_UNSUPPORTED",
            reason_code="INTERFACE-VERSION-MISMATCH",
            message=(
                f"Requested profile version {requested_version} is not supported for "
                f"{profile.profile_id}"
            ),
        )

    resolved_transport = profile.transport
    if requested_transport:
        decisions.append(
            {
                "domain": "transport_profile",
                "component": requested_transport,
                "requested": requested_transport,
                "resolved": resolved_transport,
                "support_state": "supported" if requested_transport == resolved_transport else "unsupported",
                "reason_code": None if requested_transport == resolved_transport else "TRANSPORT-MISMATCH",
            }
        )
        if requested_transport != resolved_transport:
            return _blocked_response(
                request_id=request_id,
                requested_profile=profile.profile_id,
                requested_transport=requested_transport,
                decisions=decisions,
                warnings=warnings,
                error_code="E_TRANSPORT_PROFILE_UNSUPPORTED",
                reason_code="TRANSPORT-MISMATCH",
                message=(
                    f"Requested transport {requested_transport} is not supported for "
                    f"{profile.profile_id}"
                ),
            )
    else:
        decisions.append(
            {
                "domain": "transport_profile",
                "component": resolved_transport,
                "requested": resolved_transport,
                "resolved": resolved_transport,
                "support_state": "supported",
                "reason_code": None,
            }
        )

    repo_version = ""
    if isinstance(client_component_versions, dict):
        repo_version = str(
            client_component_versions.get(
                "scratchbird_ai",
                client_component_versions.get("repo_release", ""),
            )
        ).strip()
    if repo_version and repo_version != SERVICE_RELEASE_VERSION:
        decisions.append(
            {
                "domain": "repo_release",
                "component": "scratchbird_ai",
                "requested": repo_version,
                "resolved": SERVICE_RELEASE_VERSION,
                "support_state": "unsupported",
                "reason_code": "REPO-RELEASE-MISMATCH",
            }
        )
        return _blocked_response(
            request_id=request_id,
            requested_profile=profile.profile_id,
            requested_transport=resolved_transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_COMPONENT_VERSION_UNSUPPORTED",
            reason_code="REPO-RELEASE-MISMATCH",
            message=(
                f"Client repo release {repo_version} is not supported by "
                f"{SERVICE_RELEASE_VERSION}"
            ),
        )
    decisions.append(
        {
            "domain": "repo_release",
            "component": "scratchbird_ai",
            "requested": repo_version or SERVICE_RELEASE_VERSION,
            "resolved": SERVICE_RELEASE_VERSION,
            "support_state": "supported",
            "reason_code": None,
        }
    )

    if isinstance(server_component_versions, dict) and server_component_versions:
        return _blocked_response(
            request_id=request_id,
            requested_profile=profile.profile_id,
            requested_transport=resolved_transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_CONDITIONAL_SUPPORT_BLOCKED",
            reason_code="SERVER-RUNTIME-NEGOTIATION-PENDING",
            message="Server runtime version negotiation is not implemented yet",
        )

    if isinstance(driver_runtime_versions, dict) and driver_runtime_versions:
        return _blocked_response(
            request_id=request_id,
            requested_profile=profile.profile_id,
            requested_transport=resolved_transport,
            decisions=decisions,
            warnings=warnings,
            error_code="E_DRIVER_RUNTIME_UNSUPPORTED",
            reason_code="DRIVER-RUNTIME-NEGOTIATION-PENDING",
            message="Driver/runtime version negotiation is not implemented yet",
        )

    return {
        "request_id": request_id,
        "manifest_version": manifest["manifest_version"],
        "negotiation_status": "supported",
        "resolved_interface_profile_version": profile.version,
        "resolved_transport": resolved_transport,
        "compatibility_decisions": decisions,
        "warnings": warnings,
        "error": None,
    }


def _blocked_response(
    *,
    request_id: str,
    requested_profile: str,
    requested_transport: str,
    decisions: list[dict[str, Any]],
    warnings: list[str],
    error_code: str,
    reason_code: str,
    message: str,
) -> dict[str, Any]:
    trace_id = deterministic_id(
        "tr",
        {
            "operation": "negotiate_compatibility",
            "request_id": request_id,
            "profile": requested_profile,
            "transport": requested_transport,
            "error_code": error_code,
            "reason_code": reason_code,
        },
    )
    return {
        "request_id": request_id,
        "manifest_version": COMPATIBILITY_MANIFEST_VERSION,
        "negotiation_status": "blocked",
        "resolved_interface_profile_version": None,
        "resolved_transport": None,
        "compatibility_decisions": decisions,
        "warnings": warnings,
        "error": {
            "error_code": error_code,
            "reason_code": reason_code,
            "message": message,
            "trace_id": trace_id,
        },
    }
