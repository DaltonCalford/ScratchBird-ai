# Draft Specifications

Work-in-progress specifications under active review.

## Current Draft Set

- `AI_PLATFORM_ARCHITECTURE_SPEC.md` - End-to-end architecture for ScratchBird AI integration
- `MCP_DATABASE_SERVER_SPEC.md` - MCP tool server contract for ScratchBird access
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
