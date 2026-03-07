"""Canonical tool schema validation and error envelope helpers."""

from __future__ import annotations

import json
from typing import Any

from .deterministic import deterministic_id

TOOL_SCHEMA_VERSION = "1.0"
TOOL_DESCRIPTOR_VERSION = TOOL_SCHEMA_VERSION

OPTION_LIMITS = {
    "max_rows": (1, 10_000, 200),
    "timeout_ms": (100, 30_000, 5_000),
    "memory_mb": (64, 2_048, 256),
}


class ToolContractError(RuntimeError):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        policy_rule_id: str | None = None,
        sqlstate: str | None = None,
        retryable: bool = False,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.policy_rule_id = policy_rule_id
        self.sqlstate = sqlstate
        self.retryable = retryable
        self.trace_id = trace_id


_FREEFORM_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
}

_SECURITY_CONTEXT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tenant_id": {"type": "string"},
        "actor_id": {"type": "string"},
        "roles": {"type": "array", "items": {"type": "string"}},
        "session_id": {"type": "string"},
        "context_version": {"type": "integer"},
    },
    "required": ["tenant_id", "actor_id"],
    "additionalProperties": True,
}

_APPROVAL_EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "approval_token": {"type": "string"},
        "approval_id": {"type": "string"},
        "approved_by": {"type": "string"},
        "approved_at": {"type": "string"},
    },
    "required": ["approval_token"],
    "additionalProperties": True,
}

_OPTIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "max_rows": {"type": "integer"},
        "limit": {"type": "integer"},
        "timeout_ms": {"type": "integer"},
        "memory_mb": {"type": "integer"},
    },
    "additionalProperties": False,
}

_QUERY_EMBEDDING_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 1,
}

_EMBEDDING_RECORD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "vector_id": {"type": "string"},
        "embedding": _QUERY_EMBEDDING_SCHEMA,
        "metadata": _FREEFORM_OBJECT_SCHEMA,
    },
    "required": ["vector_id", "embedding"],
    "additionalProperties": False,
}

_GENERATED_EMBEDDING_RECORD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "vector_id": {"type": "string"},
        "text": {"type": "string"},
        "metadata": _FREEFORM_OBJECT_SCHEMA,
    },
    "required": ["vector_id", "text"],
    "additionalProperties": False,
}

_PROVIDER_CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "provider_profile_id": {"type": "string"},
        "provider_id": {"type": "string"},
        "model": {"type": "string"},
        "api_key_env_var": {"type": "string"},
        "api_key": {"type": "string"},
    },
    "additionalProperties": True,
}

_TOOL_DESCRIPTORS: dict[str, dict[str, Any]] = {
    "get_capabilities": {
        "tool_name": "get_capabilities",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Return the canonical ScratchBird AI capability advertisement.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_capabilities",
        "retryable": False,
    },
    "get_tool_descriptors": {
        "tool_name": "get_tool_descriptors",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Return canonical tool descriptors and schema metadata.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_mode": "json_schema",
        "output_schema": {
            "schema_id": "tool_descriptor_catalog",
            "schema_version": "v1",
            "type": "object",
            "properties": {
                "tools": {"type": "array", "items": {"type": "object", "additionalProperties": True}}
            },
            "required": ["tools"],
            "additionalProperties": False,
        },
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_capabilities",
        "retryable": False,
    },
    "get_provider_profiles": {
        "tool_name": "get_provider_profiles",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Return direct-provider compatibility profile descriptors.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_mode": "json_schema",
        "output_schema": {
            "schema_id": "provider_profile_catalog",
            "schema_version": "v1",
            "type": "object",
            "properties": {
                "profiles": {
                    "type": "array",
                    "items": {"type": "object", "additionalProperties": True},
                }
            },
            "required": ["profiles"],
            "additionalProperties": False,
        },
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_capabilities",
        "retryable": False,
    },
    "get_compatibility_manifest": {
        "tool_name": "get_compatibility_manifest",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Return the machine-readable compatibility manifest for this release.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_capabilities",
        "retryable": False,
    },
    "negotiate_compatibility": {
        "tool_name": "negotiate_compatibility",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Validate interface profile and transport compatibility for a caller.",
        "input_schema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "string"},
                        "interface_profile_id": {"type": "string"},
                        "requested_profile_version": {"type": "string"},
                        "requested_transport": {"type": "string"},
                        "client_component_versions": _FREEFORM_OBJECT_SCHEMA,
                        "server_component_versions": _FREEFORM_OBJECT_SCHEMA,
                        "driver_runtime_versions": _FREEFORM_OBJECT_SCHEMA,
                    },
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "negotiate_compatibility",
        "retryable": False,
    },
    "list_dialects": {
        "tool_name": "list_dialects",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "List available SQL or native dialects.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_dialects",
        "retryable": False,
    },
    "list_schemas": {
        "tool_name": "list_schemas",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "List schemas for a dialect/database pair.",
        "input_schema": {
            "type": "object",
            "properties": {"dialect": {"type": "string"}, "database": {"type": "string"}},
            "required": ["dialect"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["metadata:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_metadata",
        "retryable": False,
    },
    "list_tables": {
        "tool_name": "list_tables",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "List tables for a dialect/schema pair.",
        "input_schema": {
            "type": "object",
            "properties": {"dialect": {"type": "string"}, "schema": {"type": "string"}},
            "required": ["dialect", "schema"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["metadata:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_metadata",
        "retryable": False,
    },
    "describe_table": {
        "tool_name": "describe_table",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Describe a table schema and columns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "schema": {"type": "string"},
                "table": {"type": "string"},
            },
            "required": ["dialect", "schema", "table"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["metadata:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "discover_metadata",
        "retryable": False,
    },
    "compile_query": {
        "tool_name": "compile_query",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Compile query text into a reusable compile artifact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "context": _FREEFORM_OBJECT_SCHEMA,
            },
            "required": ["dialect", "query_text"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "compile_query",
        "retryable": False,
    },
    "execute_compiled": {
        "tool_name": "execute_compiled",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Execute a previously compiled artifact with bounded options.",
        "input_schema": {
            "type": "object",
            "properties": {
                "compile_artifact_id": {"type": "string"},
                "options": _OPTIONS_SCHEMA,
                "mode": {"type": "string"},
                "approval_token": {"type": "string"},
            },
            "required": ["compile_artifact_id"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "execute_compiled",
        "retryable": True,
    },
    "execute_readonly_query": {
        "tool_name": "execute_readonly_query",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Execute a bounded read-only query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "options": _OPTIONS_SCHEMA,
                "context": _FREEFORM_OBJECT_SCHEMA,
            },
            "required": ["dialect", "query_text", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["query:read"],
        "mode_constraints": ["ai_analysis"],
        "operation_mapping": "execute_readonly_query",
        "retryable": True,
    },
    "execute_mutation": {
        "tool_name": "execute_mutation",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Execute a mutation with validated approval evidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "approval_evidence": _APPROVAL_EVIDENCE_SCHEMA,
                "options": _OPTIONS_SCHEMA,
                "context": _FREEFORM_OBJECT_SCHEMA,
            },
            "required": ["dialect", "query_text", "security_context", "approval_evidence"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["query:write"],
        "mode_constraints": ["ai_mutation_approved"],
        "operation_mapping": "execute_mutation",
        "retryable": False,
    },
    "run_query": {
        "tool_name": "run_query",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Run a query through the combined compile/execute path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "mode": {"type": "string"},
                "options": _OPTIONS_SCHEMA,
                "context": _FREEFORM_OBJECT_SCHEMA,
                "approval_token": {"type": "string"},
            },
            "required": ["dialect", "query_text"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": [],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "run_query",
        "retryable": True,
    },
    "run_mutation": {
        "tool_name": "run_mutation",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Run a mutation through the combined path with an approval token.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "approval_token": {"type": "string"},
                "options": _OPTIONS_SCHEMA,
                "context": _FREEFORM_OBJECT_SCHEMA,
            },
            "required": ["dialect", "query_text", "approval_token"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["query:write"],
        "mode_constraints": ["ai_mutation_approved"],
        "operation_mapping": "execute_mutation",
        "retryable": False,
    },
    "explain_query": {
        "tool_name": "explain_query",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Explain or introspect a query plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "context": _FREEFORM_OBJECT_SCHEMA,
            },
            "required": ["dialect", "query_text"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["query:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "explain_query",
        "retryable": False,
    },
    "create_vector_index": {
        "tool_name": "create_vector_index",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Create a retrieval index descriptor in provisioning state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "dimension": {"type": "integer"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "profile_id": {"type": "string"},
            },
            "required": ["index_id", "dimension", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "create_vector_index",
        "retryable": False,
    },
    "list_vector_indexes": {
        "tool_name": "list_vector_indexes",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "List retrieval indexes visible to the caller tenant.",
        "input_schema": {
            "type": "object",
            "properties": {
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "include_deleted": {"type": "boolean"},
            },
            "required": ["security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "list_vector_indexes",
        "retryable": True,
    },
    "describe_vector_index": {
        "tool_name": "describe_vector_index",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Describe a retrieval index and its lifecycle descriptor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": ["index_id", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "describe_vector_index",
        "retryable": True,
    },
    "add_embeddings": {
        "tool_name": "add_embeddings",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Ingest caller-supplied embeddings into a retrieval index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "dimension": {"type": "integer"},
                "records": {"type": "array", "items": _EMBEDDING_RECORD_SCHEMA, "minItems": 1},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": ["index_id", "dimension", "records", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "add_embeddings",
        "retryable": True,
    },
    "add_generated_embeddings": {
        "tool_name": "add_generated_embeddings",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Acquire provider-generated embeddings and ingest them into a retrieval index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "dimension": {"type": "integer"},
                "records": {
                    "type": "array",
                    "items": _GENERATED_EMBEDDING_RECORD_SCHEMA,
                    "minItems": 1,
                },
                "provider_config": _PROVIDER_CONFIG_SCHEMA,
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": [
                "index_id",
                "dimension",
                "records",
                "provider_config",
                "security_context",
            ],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "add_generated_embeddings",
        "retryable": True,
    },
    "delete_embeddings": {
        "tool_name": "delete_embeddings",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Delete embeddings from a retrieval index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "vector_ids": {"type": "array", "items": {"type": "string"}},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": ["index_id", "vector_ids", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "delete_embeddings",
        "retryable": True,
    },
    "reindex_vector_index": {
        "tool_name": "reindex_vector_index",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Advance a retrieval index through an explicit reindex lifecycle transition.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": ["index_id", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "reindex_vector_index",
        "retryable": False,
    },
    "delete_vector_index": {
        "tool_name": "delete_vector_index",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Delete a retrieval index and move it to the deleted lifecycle state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
            },
            "required": ["index_id", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:write"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "delete_vector_index",
        "retryable": False,
    },
    "vector_search": {
        "tool_name": "vector_search",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Run deterministic vector similarity search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_id": {"type": "string"},
                "query_embedding": _QUERY_EMBEDDING_SCHEMA,
                "top_k": {"type": "integer"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "filters": _FREEFORM_OBJECT_SCHEMA,
                "include_vectors": {"type": "boolean"},
            },
            "required": ["index_id", "query_embedding", "top_k", "security_context"],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "vector_search",
        "retryable": True,
    },
    "hybrid_search": {
        "tool_name": "hybrid_search",
        "tool_version": TOOL_DESCRIPTOR_VERSION,
        "description": "Run hybrid lexical and vector search.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dialect": {"type": "string"},
                "query_text": {"type": "string"},
                "query_embedding": _QUERY_EMBEDDING_SCHEMA,
                "vector_index_id": {"type": "string"},
                "top_k": {"type": "integer"},
                "security_context": _SECURITY_CONTEXT_SCHEMA,
                "sql_filter": _FREEFORM_OBJECT_SCHEMA,
                "weights": _FREEFORM_OBJECT_SCHEMA,
                "options": _OPTIONS_SCHEMA,
            },
            "required": [
                "dialect",
                "query_text",
                "query_embedding",
                "vector_index_id",
                "top_k",
                "security_context",
            ],
            "additionalProperties": False,
        },
        "output_mode": "json_object",
        "output_schema": None,
        "required_security_scopes": ["retrieval:read"],
        "mode_constraints": ["ai_analysis", "ai_mutation_pending_approval", "ai_mutation_approved"],
        "operation_mapping": "hybrid_search",
        "retryable": True,
    },
}


def _to_int(value: Any, default: int) -> int:
    if value is None or isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_tool_descriptors() -> list[dict[str, Any]]:
    return [dict(descriptor) for descriptor in _TOOL_DESCRIPTORS.values()]


def get_tool_descriptor(tool_name: str) -> dict[str, Any]:
    descriptor = _TOOL_DESCRIPTORS.get(str(tool_name).strip())
    if descriptor is None:
        raise ToolContractError(
            error_code="E_TOOL_NOT_FOUND",
            message=f"unknown tool: {tool_name}",
            policy_rule_id="TOOL-DESCRIPTOR-001",
        )
    return dict(descriptor)


def validate_tool_arguments(tool_name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    descriptor = get_tool_descriptor(tool_name)
    schema = descriptor["input_schema"]
    if arguments is None:
        payload: dict[str, Any] = {}
    elif isinstance(arguments, dict):
        payload = dict(arguments)
    else:
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="tool arguments must be an object",
            policy_rule_id="TOOL-INPUT-001",
        )
    errors = _validate_schema(payload, schema, path="$")
    if errors:
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="; ".join(errors),
            policy_rule_id="TOOL-INPUT-002",
        )
    if "security_context" in payload:
        payload["security_context"] = require_security_context(
            {"security_context": payload["security_context"]}
        )
    if "options" in payload and isinstance(payload["options"], dict):
        payload["options"] = validate_options(payload["options"])
    return payload


def normalize_tool_invocation(
    *,
    payload: dict[str, Any],
    interface_profile_id: str = "service_internal_v0",
    provider_profile_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="tool invocation payload must be an object",
            policy_rule_id="TOOL-INVOKE-001",
        )
    tool_name, arguments, call_id = _extract_tool_call(payload, provider_profile_id=provider_profile_id)
    validated_arguments = validate_tool_arguments(tool_name, arguments)
    descriptor = get_tool_descriptor(tool_name)
    request_id = str(payload.get("request_id", "")).strip() or deterministic_id(
        "req",
        {
            "tool_name": tool_name,
            "call_id": call_id,
            "interface_profile_id": interface_profile_id,
        },
    )
    approval_evidence = payload.get("approval_evidence", validated_arguments.get("approval_evidence"))
    if not isinstance(approval_evidence, dict):
        approval_token = str(
            payload.get("approval_token", validated_arguments.get("approval_token", ""))
        ).strip()
        approval_evidence = {"approval_token": approval_token} if approval_token else None
    options = payload.get("options", validated_arguments.get("options", {}))
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="options must be an object when provided",
            policy_rule_id="TOOL-INVOKE-002",
        )
    normalized_options = validate_options(options) if options else {}
    security_context = validated_arguments.get("security_context", payload.get("security_context"))
    if security_context is None:
        security_context = {}
    client_capabilities = payload.get("client_capabilities", {})
    if not isinstance(client_capabilities, dict):
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="client_capabilities must be an object when provided",
            policy_rule_id="TOOL-INVOKE-003",
        )
    mode = str(
        payload.get("mode", validated_arguments.get("mode", "ai_analysis"))
    ).strip() or "ai_analysis"
    return {
        "request_id": request_id,
        "interface_profile_id": interface_profile_id,
        "call_id": call_id,
        "tool_name": tool_name,
        "tool_version": descriptor["tool_version"],
        "arguments": validated_arguments,
        "security_context": security_context,
        "mode": mode,
        "approval_evidence": approval_evidence,
        "options": normalized_options,
        "client_capabilities": client_capabilities,
        "provider_profile_id": provider_profile_id,
    }


def validate_structured_output(
    *,
    output_mode: str,
    payload: Any,
    output_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = str(output_mode).strip() or "none"
    if mode == "none":
        return {
            "schema_id": None,
            "schema_version": None,
            "validation_status": "not_requested",
            "payload": None,
            "validation_errors": [],
        }
    if mode == "json_object":
        if not isinstance(payload, dict):
            raise ToolContractError(
                error_code="E_STRUCTURED_OUTPUT_INVALID",
                message="structured output must be a JSON object",
                policy_rule_id="STRUCTURED-OUTPUT-001",
            )
        return {
            "schema_id": None,
            "schema_version": None,
            "validation_status": "valid",
            "payload": payload,
            "validation_errors": [],
        }
    if mode == "json_schema":
        if output_schema is None:
            raise ToolContractError(
                error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
                message="json_schema output requires an output_schema descriptor",
                policy_rule_id="STRUCTURED-OUTPUT-002",
            )
        errors = _validate_schema(payload, output_schema, path="$")
        if errors:
            raise ToolContractError(
                error_code="E_RESPONSE_SCHEMA_MISMATCH",
                message="; ".join(errors),
                policy_rule_id="STRUCTURED-OUTPUT-003",
            )
        return {
            "schema_id": output_schema.get("schema_id"),
            "schema_version": output_schema.get("schema_version"),
            "validation_status": "valid",
            "payload": payload,
            "validation_errors": [],
        }
    raise ToolContractError(
        error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
        message=f"unsupported structured output mode: {output_mode}",
        policy_rule_id="STRUCTURED-OUTPUT-004",
    )


def normalize_tool_response(
    *,
    tool_name: str,
    request_id: str,
    call_id: str,
    interface_profile_id: str,
    trace_id: str,
    result: Any = None,
    notices: list[str] | None = None,
    error: dict[str, Any] | Exception | None = None,
) -> dict[str, Any]:
    descriptor = get_tool_descriptor(tool_name)
    notices_list = [str(item) for item in (notices or [])]
    if error is not None:
        normalized_error = (
            error
            if isinstance(error, dict)
            else map_exception_to_error(
                error,
                trace_seed={"tool_name": tool_name, "request_id": request_id, "call_id": call_id},
            )
        )
        return {
            "request_id": request_id,
            "call_id": call_id,
            "interface_profile_id": interface_profile_id,
            "trace_id": trace_id,
            "status": "error",
            "result": None,
            "structured_output": None,
            "error": normalized_error,
            "notices": notices_list,
        }
    structured_output = validate_structured_output(
        output_mode=descriptor["output_mode"],
        payload=result,
        output_schema=descriptor["output_schema"],
    )
    return {
        "request_id": request_id,
        "call_id": call_id,
        "interface_profile_id": interface_profile_id,
        "trace_id": trace_id,
        "status": "success",
        "result": result,
        "structured_output": structured_output,
        "error": None,
        "notices": notices_list,
    }


def require_security_context(payload: dict[str, Any] | None) -> dict[str, Any]:
    src = payload or {}
    raw = src.get("security_context", src)
    if not isinstance(raw, dict):
        raise ToolContractError(
            error_code="E_POLICY_DENY",
            message="security_context must be an object",
            policy_rule_id="SECURITY-CONTEXT-001",
        )

    tenant_id = str(raw.get("tenant_id", "")).strip()
    actor_id = str(raw.get("actor_id", "")).strip()
    roles_raw = raw.get("roles", [])
    session_id = str(raw.get("session_id", "")).strip()
    context_version = _to_int(raw.get("context_version"), 1)

    if not tenant_id or not actor_id:
        raise ToolContractError(
            error_code="E_POLICY_DENY",
            message="security_context requires tenant_id and actor_id",
            policy_rule_id="SECURITY-CONTEXT-002",
        )

    roles = [str(role) for role in roles_raw] if isinstance(roles_raw, list) else []
    normalized = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "roles": roles,
        "session_id": session_id,
        "context_version": max(1, context_version),
    }
    return normalized


def validate_options(options: dict[str, Any] | None) -> dict[str, int]:
    src = options or {}
    out: dict[str, int] = {}
    aliases = {
        "max_rows": "limit",
    }
    for field_name, (minimum, maximum, default) in OPTION_LIMITS.items():
        value_raw = src.get(field_name)
        if value_raw is None and field_name in aliases:
            value_raw = src.get(aliases[field_name])
        value = _to_int(value_raw, default)
        if value > maximum:
            raise ToolContractError(
                error_code="E_LIMIT_EXCEEDED",
                message=f"{field_name} exceeds hard limit ({maximum})",
                policy_rule_id="OPTIONS-LIMIT-001",
            )
        if value < minimum:
            value = minimum
        out[field_name] = value
    out["limit"] = out["max_rows"]
    return out


def make_trace_id(seed: dict[str, Any]) -> str:
    return deterministic_id("tr", seed)


def error_envelope(
    *,
    error_code: str,
    message: str,
    trace_id: str | None = None,
    policy_rule_id: str | None = None,
    sqlstate: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": message,
        "trace_id": trace_id or make_trace_id({"error_code": error_code, "message": message}),
        "policy_rule_id": policy_rule_id,
        "sqlstate": sqlstate,
        "retryable": bool(retryable),
    }


def map_exception_to_error(exc: Exception, *, trace_seed: dict[str, Any]) -> dict[str, Any]:
    try:
        from .execution_mode import ExecutionModeError
        from .policy import PolicyDeniedError
        from .retrieval import RetrievalError
        from .router import RoutingError
    except Exception:  # pragma: no cover - import cycle fallback
        ExecutionModeError = None  # type: ignore[assignment]
        PolicyDeniedError = None  # type: ignore[assignment]
        RetrievalError = None  # type: ignore[assignment]
        RoutingError = None  # type: ignore[assignment]

    trace_id = make_trace_id(trace_seed)
    if isinstance(exc, ToolContractError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=exc.trace_id or trace_id,
            policy_rule_id=exc.policy_rule_id,
            sqlstate=exc.sqlstate,
            retryable=exc.retryable,
        )
    if PolicyDeniedError is not None and isinstance(exc, PolicyDeniedError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.reason,
            trace_id=trace_id,
            policy_rule_id=exc.rule_id,
            retryable=False,
        )
    if RoutingError is not None and isinstance(exc, RoutingError):
        return error_envelope(
            error_code="E_DIALECT_UNAVAILABLE",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    if ExecutionModeError is not None and isinstance(exc, ExecutionModeError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=trace_id,
            policy_rule_id=exc.rule_id,
            retryable=False,
        )
    if RetrievalError is not None and isinstance(exc, RetrievalError):
        return error_envelope(
            error_code=exc.error_code,
            message=exc.message,
            trace_id=trace_id,
            policy_rule_id=exc.policy_rule_id,
            retryable=exc.retryable,
        )
    if isinstance(exc, KeyError):
        return error_envelope(
            error_code="E_INVALID_ARGUMENT",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    if isinstance(exc, ValueError):
        return error_envelope(
            error_code="E_INVALID_ARGUMENT",
            message=str(exc),
            trace_id=trace_id,
            retryable=False,
        )
    return error_envelope(
        error_code="E_EXECUTION_FAILED",
        message=str(exc) or "execution failed",
        trace_id=trace_id,
        retryable=False,
    )


def _extract_tool_call(
    payload: dict[str, Any],
    *,
    provider_profile_id: str | None,
) -> tuple[str, dict[str, Any], str]:
    if provider_profile_id == "openai_tool_calling_v0":
        function = payload.get("function", {})
        if not isinstance(function, dict):
            raise ToolContractError(
                error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
                message="OpenAI-style function payload must be an object",
                policy_rule_id="TOOL-PROVIDER-001",
            )
        tool_name = str(function.get("name", "")).strip()
        args_raw = function.get("arguments", {})
        if isinstance(args_raw, str):
            try:
                arguments = json.loads(args_raw)
            except json.JSONDecodeError as exc:
                raise ToolContractError(
                    error_code="E_TOOL_INPUT_INVALID",
                    message=f"invalid JSON function arguments: {exc}",
                    policy_rule_id="TOOL-PROVIDER-002",
                ) from None
        else:
            arguments = args_raw
        call_id = str(payload.get("id", payload.get("call_id", ""))).strip()
    elif provider_profile_id == "anthropic_tool_use_v0":
        tool_name = str(payload.get("name", "")).strip()
        arguments = payload.get("input", {})
        call_id = str(payload.get("id", payload.get("call_id", ""))).strip()
    elif provider_profile_id == "gemini_function_calling_v0":
        function_call = payload.get("functionCall", payload)
        if not isinstance(function_call, dict):
            raise ToolContractError(
                error_code="E_PROVIDER_CONTRACT_UNSUPPORTED",
                message="Gemini-style functionCall payload must be an object",
                policy_rule_id="TOOL-PROVIDER-003",
            )
        tool_name = str(function_call.get("name", "")).strip()
        arguments = function_call.get("args", {})
        call_id = str(function_call.get("id", payload.get("call_id", ""))).strip()
    else:
        tool_name = str(payload.get("tool_name", payload.get("name", ""))).strip()
        arguments = payload.get("arguments", {})
        call_id = str(payload.get("call_id", payload.get("id", ""))).strip()

    if not tool_name:
        raise ToolContractError(
            error_code="E_TOOL_NOT_FOUND",
            message="tool_name is required",
            policy_rule_id="TOOL-INVOKE-004",
        )
    if not call_id:
        call_id = deterministic_id(
            "call",
            {"tool_name": tool_name, "provider_profile_id": provider_profile_id or "canonical"}
        )
    if not isinstance(arguments, dict):
        raise ToolContractError(
            error_code="E_TOOL_INPUT_INVALID",
            message="tool arguments must decode to an object",
            policy_rule_id="TOOL-INVOKE-005",
        )
    return tool_name, dict(arguments), call_id


def _validate_schema(value: Any, schema: dict[str, Any] | None, *, path: str) -> list[str]:
    if schema is None:
        return []
    schema_type = schema.get("type")
    errors: list[str] = []

    if schema_type == "object":
        if not isinstance(value, dict):
            return [f"{path} must be an object"]
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                errors.append(f"{path}.{field} is required")
        additional_allowed = schema.get("additionalProperties", False)
        if not additional_allowed:
            for field in value:
                if field not in properties:
                    errors.append(f"{path}.{field} is not allowed")
        for field, field_schema in properties.items():
            if field in value:
                errors.extend(_validate_schema(value[field], field_schema, path=f"{path}.{field}"))
        return errors

    if schema_type == "array":
        if not isinstance(value, list):
            return [f"{path} must be an array"]
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path} must contain at least {min_items} item(s)")
        item_schema = schema.get("items")
        for idx, item in enumerate(value):
            errors.extend(_validate_schema(item, item_schema, path=f"{path}[{idx}]"))
        return errors

    if schema_type == "string":
        if not isinstance(value, str):
            return [f"{path} must be a string"]
        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            return [f"{path} must be one of {enum_values}"]
        return []

    if schema_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return [f"{path} must be an integer"]
        return []

    if schema_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return [f"{path} must be a number"]
        return []

    if schema_type == "boolean":
        if not isinstance(value, bool):
            return [f"{path} must be a boolean"]
        return []

    return []
