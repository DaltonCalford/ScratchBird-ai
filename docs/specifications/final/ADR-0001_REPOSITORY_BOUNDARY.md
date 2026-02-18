# ADR: Repository Boundary for ScratchBird AI Integration

Date: 2026-02-18
Status: Accepted

## Context

ScratchBird core engine and parser/dialect implementations are active, high-velocity codebases with strict architectural boundaries. AI integration introduces fast-moving dependencies (LLM SDKs, MCP frameworks, orchestration libraries, evaluation tooling) and a distinct release cadence.

The project needs a placement decision for AI integration code and specifications.

## Decision

Adopt a dedicated repository: `ScratchBird-ai`.

- Keep core engine/parser responsibilities in `ScratchBird`.
- Keep language/native protocol drivers in `ScratchBird-driver`.
- Build AI orchestration, MCP service layer, policy controls, and evaluation framework in `ScratchBird-ai`.

## Consequences

Positive:

- Isolates fast-changing AI dependencies from engine and driver release risk.
- Enables independent CI/CD and versioning for AI features.
- Preserves architecture ownership boundaries.
- Makes security review scope clearer for AI tool access pathways.

Negative:

- Requires explicit contract versioning across repositories.
- Adds operational overhead for multi-repo coordination.

Follow-up actions:

- Define versioned interface contracts in `../drafts/AI_PLATFORM_ARCHITECTURE_SPEC.md`.
- Create compatibility matrix between `ScratchBird-ai` and `ScratchBird` releases.
