"""Canonical interface profile descriptors for ScratchBird AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INTERFACE_COMPATIBILITY_VERSION = "2026-03-07"


@dataclass(slots=True, frozen=True)
class InterfaceProfileDescriptor:
    profile_id: str
    family: str
    version: str
    state: str
    transport: str
    session_model: str
    auth_model: str
    operation_set: tuple[str, ...]
    streaming_mode: str
    compatibility_version: str = INTERFACE_COMPATIBILITY_VERSION
    evidence_gate: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "family": self.family,
            "version": self.version,
            "state": self.state,
            "transport": self.transport,
            "session_model": self.session_model,
            "auth_model": self.auth_model,
            "operation_set": list(self.operation_set),
            "streaming_mode": self.streaming_mode,
            "compatibility_version": self.compatibility_version,
            "evidence_gate": self.evidence_gate,
        }


_CANONICAL_READ_OPS = (
    "discover_capabilities",
    "get_compatibility_manifest",
    "negotiate_compatibility",
    "discover_dialects",
    "discover_metadata",
    "compile_query",
    "execute_compiled",
    "execute_readonly_query",
    "explain_query",
)

_RETRIEVAL_OPS = (
    "add_embeddings",
    "delete_embeddings",
    "vector_search",
    "hybrid_search",
)

_MUTATION_OPS = ("execute_mutation",)


_INTERFACE_PROFILES = (
    InterfaceProfileDescriptor(
        profile_id="service_internal_v0",
        family="service_internal",
        version="v0",
        state="implemented",
        transport="in_process",
        session_model="request_scoped",
        auth_model="forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + _RETRIEVAL_OPS,
        streaming_mode="request_response",
        evidence_gate="EVID-03",
    ),
    InterfaceProfileDescriptor(
        profile_id="mcp_local_v0",
        family="mcp_local",
        version="v0",
        state="implemented",
        transport="stdio_jsonrpc",
        session_model="process_local_tool_session",
        auth_model="forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + ("vector_search", "hybrid_search"),
        streaming_mode="request_response",
        evidence_gate="EVID-03",
    ),
    InterfaceProfileDescriptor(
        profile_id="mcp_remote_v0",
        family="mcp_remote",
        version="v0",
        state="draft",
        transport="https_json_request_response",
        session_model="remote_session_bound",
        auth_model="token_or_session_bound_identity",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + ("vector_search", "hybrid_search"),
        streaming_mode="server_stream",
    ),
    InterfaceProfileDescriptor(
        profile_id="langchain_v0",
        family="framework_adapter",
        version="v0",
        state="draft",
        transport="in_process_sdk",
        session_model="adapter_request_scoped",
        auth_model="forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + ("vector_search", "hybrid_search"),
        streaming_mode="request_response",
    ),
    InterfaceProfileDescriptor(
        profile_id="llamaindex_v0",
        family="framework_adapter",
        version="v0",
        state="draft",
        transport="in_process_sdk",
        session_model="adapter_request_scoped",
        auth_model="forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + ("vector_search", "hybrid_search"),
        streaming_mode="request_response",
    ),
    InterfaceProfileDescriptor(
        profile_id="semantic_kernel_v0",
        family="framework_adapter",
        version="v0",
        state="draft",
        transport="in_process_sdk",
        session_model="adapter_request_scoped",
        auth_model="forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS + ("vector_search", "hybrid_search"),
        streaming_mode="request_response",
    ),
    InterfaceProfileDescriptor(
        profile_id="provider_tool_calling_v0",
        family="provider_tool_calling",
        version="v0",
        state="implemented",
        transport="provider_http_api",
        session_model="provider_request_scoped",
        auth_model="provider_auth_plus_forwarded_security_context",
        operation_set=_CANONICAL_READ_OPS + _MUTATION_OPS,
        streaming_mode="request_response",
        evidence_gate="EVID-13",
    ),
    InterfaceProfileDescriptor(
        profile_id="streaming_async_v0",
        family="streaming_async",
        version="v0",
        state="draft",
        transport="event_stream",
        session_model="operation_session",
        auth_model="forwarded_security_context",
        operation_set=(
            "execute_readonly_query",
            "execute_mutation",
            "explain_query",
            "vector_search",
            "hybrid_search",
        ),
        streaming_mode="server_stream",
    ),
    InterfaceProfileDescriptor(
        profile_id="retrieval_ingest_v0",
        family="retrieval_ingest",
        version="v0",
        state="draft",
        transport="request_response",
        session_model="request_scoped",
        auth_model="forwarded_security_context",
        operation_set=_RETRIEVAL_OPS,
        streaming_mode="request_response",
    ),
    InterfaceProfileDescriptor(
        profile_id="governance_certification_v0",
        family="governance_certification",
        version="v0",
        state="draft",
        transport="request_response",
        session_model="request_scoped",
        auth_model="forwarded_security_context",
        operation_set=(
            "execute_mutation",
            "replay_audit_bundle",
            "validate_approval_evidence",
            "export_certification_manifest",
        ),
        streaming_mode="request_response",
    ),
)


def get_interface_profiles() -> list[dict[str, Any]]:
    return [profile.to_dict() for profile in _INTERFACE_PROFILES]


def get_interface_profile_descriptors() -> tuple[InterfaceProfileDescriptor, ...]:
    return _INTERFACE_PROFILES
