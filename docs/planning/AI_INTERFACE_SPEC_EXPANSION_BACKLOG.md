# AI Interface Specification Expansion Backlog

Status: Active
Last Updated: 2026-03-07

## 1. Purpose

Define the missing specification work required to make `ScratchBird-ai` broadly consumable by external AI frameworks, model runtimes, and remote clients without violating the existing architecture decisions in:

- `docs/specifications/final/ADR-0001_REPOSITORY_BOUNDARY.md`
- `docs/specifications/final/ADR-0002_QUERY_ENTRYPOINT_AND_SBLR_POLICY.md`
- `docs/specifications/final/ADR-0003_SERVER_EXECUTION_BOUNDARY_AND_ADAPTER_ROLE.md`

This backlog is about specification coverage, not feature-complete implementation.

## 2. Current Baseline

The current repository has implementation-backed coverage for:

- native-only routing and capability gating
- MCP-oriented local service orchestration
- HTTP adapter and local bridge runtime
- deterministic policy, retrieval, plan, audit, and routing helpers
- early-beta conformance gating for the implemented surface

What it does not yet have is a complete, current specification set for exposing the same engine-access model through the broader AI ecosystem.

## 3. Non-Negotiable Invariants

Every new interface specification in this backlog must preserve these rules:

1. Native-only scope remains the current supported repository scope unless explicitly expanded.
2. Query text goes through parser/compiler pathways before execution.
3. Engine execution boundary remains `ServerSession`; no direct SQL execution path is introduced in engine code.
4. Policy and authorization remain server-side, not prompt-driven.
5. Non-native or unsupported capability requests fail closed.

## 4. Specification Backlog

| Priority | Proposed spec file | Scope | Why it is missing | Status |
| --- | --- | --- | --- | --- |
| P0 | `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md` | Master spec for supported interface classes, compatibility promises, and boundary rules | The repo has architecture and release docs, but no single current contract for which AI interfaces are in scope and how they relate | Drafted |
| P0 | `docs/specifications/drafts/REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md` | Remote MCP transport, auth, session lifecycle, streaming, long-running calls, and cancellation | Current MCP draft is tool-focused and leaves remote transport/auth/session behavior open | Drafted |
| P0 | `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md` | Provider-neutral tool calling, JSON/schema validation, structured-output coercion, and error envelopes | Current tool schema coverage is implementation-oriented and not yet framed as a provider-neutral contract | Drafted |
| P0 | `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md` | Version matrix, compatibility policy, release negotiation between `ScratchBird-ai`, ScratchBird server, parser/compiler, and driver/runtime | ADR-0001 calls for this, but no concrete compatibility spec exists yet | Drafted |
| P1 | `docs/specifications/drafts/LANGCHAIN_ADAPTER_SPEC.md` | Current-architecture LangChain adapter contract aligned to native-only, parser-first execution | The older LangChain spec exists under `ScratchBird_AI_Specifications/` but is broader than the current shipped code and not tied to the active release model | Drafted |
| P1 | `docs/specifications/drafts/LLAMAINDEX_ADAPTER_SPEC.md` | Current-architecture LlamaIndex adapter contract aligned to native-only, parser-first execution | Same issue as LangChain: existing material is stale relative to the active implementation boundary | Drafted |
| P1 | `docs/specifications/drafts/SEMANTIC_KERNEL_ADAPTER_SPEC.md` | Semantic Kernel plugin/function integration profile | There is no maintained spec for Semantic Kernel despite it being a likely enterprise-facing interface | Drafted |
| P1 | `docs/specifications/drafts/DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md` | Direct provider integration profiles for tool-calling model APIs (for example OpenAI-, Anthropic-, and Gemini-style clients) | The repo has no explicit contract for direct non-framework clients calling into the service | Drafted |
| P1 | `docs/specifications/drafts/STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md` | Partial results, event streaming, progress, continuation tokens, and cancellation semantics | Current service and bridge docs do not define a stable streaming model for AI clients | Drafted |
| P2 | `docs/specifications/drafts/EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` | Embedding generation contracts, corpus ingestion/update/delete, vector-index lifecycle, and retrieval store responsibilities | Current retrieval behavior is implementation-backed but still mostly engine-free helper logic | Drafted |
| P2 | `docs/specifications/drafts/MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` | Durable approval evidence, policy binding, replay/audit requirements, and operator workflow | Governance docs describe the need, but the durable approval contract is still incomplete | Drafted |
| P2 | `docs/specifications/drafts/LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Live-server certification matrix, framework conformance evidence, and release-grade runtime validation | Current conformance gate covers the implemented early-beta surface, not full external interface certification | Drafted |

## 5. Delivery Sequence

### Phase A: Interface-Neutral Foundations

Deliver first:

1. `AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
2. `REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md`
3. `MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
4. `COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`

Reason:

These documents define the common contract that every framework-specific or provider-specific adapter must inherit.

### Phase B: Framework and Provider Adapters

Deliver next:

1. `LANGCHAIN_ADAPTER_SPEC.md`
2. `LLAMAINDEX_ADAPTER_SPEC.md`
3. `SEMANTIC_KERNEL_ADAPTER_SPEC.md`
4. `DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md`
5. `STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md`

Reason:

These are the missing interface layers needed to make the engine accessible through the external AI ecosystems most likely to matter in practice.

### Phase C: Governance, Retrieval, and Certification

Deliver last:

1. `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md`
2. `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md`
3. `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md`

Reason:

These specs move the system from interface availability to production-grade and certifiable behavior.

## 6. Minimum Content Required In Every New Spec

Every spec in this backlog should define:

1. Supported entrypoints and use cases
2. Request/response schemas
3. Auth and security-context requirements
4. Policy and mode handling rules
5. Error taxonomy and retry semantics
6. Streaming or long-running behavior if applicable
7. Compatibility/versioning rules
8. Required conformance tests and release evidence

## 7. Relationship To Existing Docs

- `docs/releases/EARLY_BETA_CONFORMANCE_GATES.md` remains the active release contract for what is currently implemented.
- `docs/specifications/ScratchBird_AI_Specifications/` should be treated as older expansion material and not as the active release-aligned interface program.
- New interface specs should be written under `docs/specifications/drafts/` and promoted only after they are implemented and evidence-backed.
- Execution sequencing for the drafted interface set now lives in `docs/planning/AI_INTERFACE_IMPLEMENTATION_BACKLOG.md`.

## 8. Recommended Next Authoring Order

1. Review the draft set for overlapping request/response schemas and consolidate shared definitions.
2. Map each draft spec to concrete implementation backlog items and release evidence.
3. Identify which draft specs are candidates for promotion to `docs/specifications/final/` once code and CI coverage exist.
