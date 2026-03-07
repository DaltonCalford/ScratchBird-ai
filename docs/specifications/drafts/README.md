# Draft Specifications

Work-in-progress specifications under active review.

## Current Draft Set

- `AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md` - top-level interface profile inventory and coverage program for broader AI access
- `AI_PLATFORM_ARCHITECTURE_SPEC.md` - End-to-end architecture for ScratchBird AI integration
- `COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md` - version matrix, runtime negotiation, and fail-closed compatibility contract
- `DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md` - direct provider tool-calling compatibility profiles and canonical mapping rules
- `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` - canonical lifecycle for embeddings, vector indexes, vector search, and hybrid retrieval profiles
- `LANGCHAIN_ADAPTER_SPEC.md` - current-architecture LangChain adapter contract over canonical ScratchBird AI operations
- `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` - live runtime certification and profile-level release evidence contract
- `LLAMAINDEX_ADAPTER_SPEC.md` - current-architecture LlamaIndex adapter contract over canonical ScratchBird AI operations
- `MCP_DATABASE_SERVER_SPEC.md` - MCP tool server contract for ScratchBird access
- `MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md` - provider-neutral tool calling and structured-output normalization contract
- `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` - approval-gated mutation, deterministic audit bundle, and replay-validation contract
- `REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md` - remote MCP transport, session, streaming, and cancellation contract
- `SEMANTIC_KERNEL_ADAPTER_SPEC.md` - Semantic Kernel plugin/function compatibility contract over canonical ScratchBird AI operations
- `STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md` - canonical streaming, partial-result, continuation, and cancellation model
- `TEXT_TO_SQL_ROUTER_AND_COMPILER_SPEC.md` - NL query orchestration and parser-compiler integration
- `DIALECT_CAPABILITY_MATRIX_SPEC.md` - Dialect readiness/capability contract and routing rules
- `SECURITY_GOVERNANCE_OBSERVABILITY_SPEC.md` - Security, audit, policy, and telemetry requirements
- `SCRATCHBIRD_HTTP_ADAPTER_CONTRACT_SPEC.md` - HTTP endpoint contract for real compile/execute/metadata adapters

## Supporting Artifacts

- `capability-matrix/capability-matrix.schema.json` - machine-readable matrix schema
- `capability-matrix/capability-matrix.v0.json` - initial matrix payload

## Promotion Rule

A draft can be moved to `../final/` only after:

1. All open questions are resolved.
2. Acceptance criteria are testable and implemented in CI.
3. Security and governance controls are explicitly defined.
