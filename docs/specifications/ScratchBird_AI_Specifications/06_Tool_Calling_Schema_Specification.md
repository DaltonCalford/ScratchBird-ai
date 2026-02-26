# ScratchBird Tool-Calling Schema Specification

Status: Normative Draft  
Owner: ScratchBird AI Team  
Effective Date: 2026-02-24

## 1. Scope

Define the canonical AI tool contract for `ScratchBird-ai`, including:
1. tool names,
2. input and output schemas,
3. error envelope,
4. security and governance rules.

This specification is the source of truth for MCP and HTTP tool interfaces.

## 2. Canonical Tool Catalog (v1)

Required tools:
1. `get_capabilities`
2. `list_dialects`
3. `list_schemas`
4. `list_tables`
5. `describe_table`
6. `execute_readonly_query`
7. `execute_mutation`
8. `explain_query`
9. `vector_search`
10. `hybrid_search`

Compatibility aliases (MAY be supported during migration):
1. `run_query` => `execute_readonly_query`
2. `run_mutation` => `execute_mutation`
3. `compile_query` + `execute_compiled` may remain internal/advanced tools but are not canonical public names.

## 3. Shared Types

### 3.1 SecurityContext

```json
{
  "tenant_id": "string",
  "actor_id": "string",
  "roles": ["string"],
  "session_id": "string",
  "context_version": 1
}
```

### 3.2 Options

```json
{
  "max_rows": 200,
  "timeout_ms": 5000,
  "memory_mb": 256
}
```

Constraints:
1. `max_rows` MUST be `1..10000`.
2. `timeout_ms` MUST be `100..30000`.
3. `memory_mb` MUST be `64..2048`.

### 3.3 ApprovalEvidence

```json
{
  "approval_token": "jwt-or-signed-token",
  "approval_id": "appr-...",
  "approved_by": "actor-or-service",
  "approved_at": "2026-02-24T12:34:56Z"
}
```

### 3.4 Artifact ID Determinism Rules

1. `compile_artifact_id` format:
   - `cmp_` + first 24 hex chars of `SHA256(canonical_compile_input)`
2. `canonical_compile_input` fields:
   - `dialect`
   - `normalized_query_text`
   - `security_context_hash`
   - `context` (canonicalized JSON)
3. `execution_artifact_id` format:
   - `exe_` + first 24 hex chars of `SHA256(canonical_execution_input)`
4. `canonical_execution_input` fields:
   - `compile_artifact_id`
   - canonicalized `options`
   - `execution_mode`
   - `attempt_index`
5. Hashing and canonicalization:
   - JSON MUST be canonicalized with RFC 8785 JCS.
   - SHA-256 output MUST be lowercase hex.

## 4. Tool Schemas

### 4.1 get_capabilities

Input:

```json
{}
```

Output:

```json
{
  "service": "scratchbird-ai",
  "version": "string",
  "adapter_mode": "string",
  "supports": {
    "metadata": true,
    "compile_execute_split": true,
    "read_only_mode": true,
    "mutation_requires_approval": true
  },
  "matrix_version": "string"
}
```

### 4.2 list_dialects

Input:

```json
{}
```

Output:

```json
{
  "dialects": ["native"]
}
```

### 4.3 list_schemas

Input:

```json
{
  "dialect": "native",
  "database": "optional-string",
  "security_context": { "...": "SecurityContext" }
}
```

Output:

```json
{
  "schemas": ["public", "analytics"],
  "trace_id": "tr_..."
}
```

### 4.4 list_tables

Input:

```json
{
  "dialect": "native",
  "schema": "public",
  "security_context": { "...": "SecurityContext" }
}
```

Output:

```json
{
  "tables": ["orders", "customers"],
  "trace_id": "tr_..."
}
```

### 4.5 describe_table

Input:

```json
{
  "dialect": "native",
  "schema": "public",
  "table": "orders",
  "security_context": { "...": "SecurityContext" }
}
```

Output:

```json
{
  "dialect": "native",
  "schema": "public",
  "table": "orders",
  "columns": [
    { "name": "order_id", "type": "uuid", "nullable": false }
  ],
  "trace_id": "tr_..."
}
```

### 4.6 execute_readonly_query

Input:

```json
{
  "dialect": "native",
  "query_text": "SELECT ...",
  "security_context": { "...": "SecurityContext" },
  "options": { "...": "Options" },
  "context": {}
}
```

Behavior:
1. Execution mode is fixed to `ai_analysis`.
2. Mutation statements MUST be denied.

Output:

```json
{
  "compile_artifact_id": "cmp_...",
  "execution_artifact_id": "exe_...",
  "result_rows": [],
  "row_count": 0,
  "notices": [],
  "trace_id": "tr_..."
}
```

### 4.7 execute_mutation

Input:

```json
{
  "dialect": "native",
  "query_text": "UPDATE ...",
  "security_context": { "...": "SecurityContext" },
  "approval_evidence": { "...": "ApprovalEvidence" },
  "options": { "...": "Options" },
  "context": {}
}
```

Behavior:
1. Must run in `ai_mutation_approved`.
2. Must validate approval evidence before compile/execute.

Output:

```json
{
  "compile_artifact_id": "cmp_...",
  "execution_artifact_id": "exe_...",
  "affected_rows": 10,
  "notices": [],
  "trace_id": "tr_..."
}
```

### 4.8 explain_query

Input:

```json
{
  "dialect": "native",
  "query_text": "SELECT ...",
  "security_context": { "...": "SecurityContext" },
  "context": {}
}
```

Output:

```json
{
  "compile_artifact_id": "cmp_...",
  "plan_hash": "hex-sha256",
  "operator_tree": {},
  "rls_visibility": { "applied": true, "policy_ids": ["RLS-001"] },
  "trace_id": "tr_..."
}
```

### 4.9 vector_search

Input:

```json
{
  "index_id": "idx_docs",
  "query_embedding": [0.11, 0.22, 0.33],
  "top_k": 20,
  "filters": {},
  "security_context": { "...": "SecurityContext" }
}
```

Output:

```json
{
  "results": [],
  "trace_id": "tr_...",
  "rls_applied": true
}
```

### 4.10 hybrid_search

Input:

```json
{
  "dialect": "native",
  "query_text": "latest overdue invoices",
  "query_embedding": [0.11, 0.22, 0.33],
  "vector_index_id": "idx_docs",
  "sql_filter": {},
  "weights": { "vector": 0.6, "lexical": 0.3, "structured": 0.1 },
  "top_k": 20,
  "security_context": { "...": "SecurityContext" },
  "options": { "...": "Options" }
}
```

Output:

```json
{
  "results": [],
  "trace_id": "tr_...",
  "rls_applied": true,
  "query_plan_ref": "plan_..."
}
```

## 5. Standard Error Envelope

All tool failures MUST return:

```json
{
  "error_code": "E_POLICY_DENY",
  "message": "human-readable reason",
  "trace_id": "tr_...",
  "policy_rule_id": "POLICY-...",
  "sqlstate": "optional-sqlstate",
  "retryable": false
}
```

## 6. Governance Rules

1. Mutation requires validated approval evidence and audit logging.
2. Missing or invalid `security_context` MUST fail closed.
3. Unsupported dialect MUST fail with `E_DIALECT_UNAVAILABLE`.
4. Prompt text MUST NOT be used as policy authority.

## 7. Versioning Rules

1. Contract version string: `tool_schema_version`.
2. Breaking changes require major version increment.
3. Additive fields may be introduced in minor versions if backward compatible.
4. Deprecated alias tools MUST remain functional for at least one minor release unless a security issue requires removal.

## 8. Required Conformance Tests

1. JSON schema validation for all tool inputs/outputs.
2. Negative tests for missing required fields.
3. Mutation denied without approval evidence.
4. Deterministic traceability fields present in all success/error responses.
5. Compatibility alias tests (`run_query`, `run_mutation`).

## 9. Acceptance Criteria

1. Canonical tool catalog is fully implemented and tested.
2. All responses use standard success/error envelopes.
3. Security and governance checks pass for every tool.

## 10. Evidence Binding

1. This specification is bound to `EVID-06` in `12_External_Evidence_Traceability.md`.
2. Release evidence MUST include:
   - `artifacts/ai_conformance/06/schema_report.json`
   - `artifacts/ai_conformance/06/compat_report.json`
3. Tool schema version promotions MUST be blocked when `EVID-06` is not `PASS`.
