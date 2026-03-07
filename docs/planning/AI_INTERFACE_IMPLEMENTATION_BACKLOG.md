# AI Interface Implementation Backlog

Status: Active
Last Updated: 2026-03-07

## 1. Purpose

Convert the drafted AI interface specifications into concrete implementation, testing, and release-evidence work for `ScratchBird-ai`.

This backlog covers the post-early-beta expansion path required to move from the currently implemented profiles:

- `service_internal_v0`
- `mcp_local_v0`

into broader live, framework, provider, retrieval, and governance coverage.

## 2. Scope

- In scope:
- interface profile descriptors and compatibility negotiation
- remote MCP/session transport support
- framework adapters and direct provider tool-calling profiles
- streaming and long-running execution support
- retrieval lifecycle expansion beyond the in-memory helper baseline
- durable approval evidence and live certification

- Out of scope:
- replacing the existing early-beta backlog
- non-native dialect enablement
- direct SQL execution paths outside parser/compiler boundaries

## 3. Source Specifications

This backlog is derived from:

- `docs/planning/AI_INTERFACE_SPEC_EXPANSION_BACKLOG.md`
- `docs/specifications/drafts/AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md`
- `docs/specifications/drafts/REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md`
- `docs/specifications/drafts/MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md`
- `docs/specifications/drafts/COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md`
- `docs/specifications/drafts/LANGCHAIN_ADAPTER_SPEC.md`
- `docs/specifications/drafts/LLAMAINDEX_ADAPTER_SPEC.md`
- `docs/specifications/drafts/SEMANTIC_KERNEL_ADAPTER_SPEC.md`
- `docs/specifications/drafts/DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md`
- `docs/specifications/drafts/STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md`
- `docs/specifications/drafts/EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md`
- `docs/specifications/drafts/MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md`
- `docs/specifications/drafts/LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md`

## 4. Current Baseline

As of 2026-03-07:

- `service_internal_v0` is implemented
- `mcp_local_v0` is implemented
- remote MCP session establishment, streaming lifecycle, continuation polling, and cancellation primitives are implemented at the service layer
- direct provider child profiles for OpenAI-style, Anthropic-style, and Gemini-style tool calls are implemented over the canonical normalization layer
- LangChain, LlamaIndex, and Semantic Kernel compatibility adapters are implemented as thin wrappers over the canonical service contract
- vector and hybrid retrieval exist only as helper-level, in-memory baseline behavior
- mutation approval validation and audit bundles exist only as in-process, non-durable behavior
- release evidence covers repository selftest, not live certification

## 5. Workstreams

### 5.1 Workstream A: Shared Control Plane

Goal: create the common control-plane surface every external interface must inherit.

| Task | Status | Spec Binding | Notes |
| --- | --- | --- | --- |
| IF-001: Implement interface profile descriptor inventory and expanded capability advertisement | Completed | `AI_INTERFACE_COVERAGE_PROGRAM_SPEC.md` | `get_capabilities()` now publishes the canonical `interface_profiles[]` inventory and compatibility version |
| IF-002: Implement compatibility manifest generation and request-time negotiation checks | Completed | `COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md` | Service now publishes a machine-readable manifest, exposes negotiation APIs, and blocks incompatible declared profile/transport requests |
| IF-003: Implement canonical tool-calling normalization layer and structured-output validator | Completed | `MODEL_TOOL_CALLING_AND_STRUCTURED_OUTPUT_SPEC.md` | Canonical tool descriptors, provider-shape normalization, strict argument validation, and structured-output validation are now implemented and test-backed |
| IF-004: Implement remote session/auth lifecycle primitives for non-local clients | Completed | `REMOTE_MCP_TRANSPORT_AND_SESSION_SPEC.md` | Remote session create, auth binding, expiry, and close semantics are now implemented and test-backed |
| IF-005: Implement streaming event envelope, continuation tokens, and cancellation primitives | Completed | `STREAMING_AND_LONG_RUNNING_OPERATION_SPEC.md` | Streaming event envelopes, continuation polling, and deterministic cancellation outcomes are now implemented at the service layer |

### 5.2 Workstream B: Framework and Provider Adapters

Goal: expose the canonical service contract through major framework and provider ecosystems without adding alternate execution semantics.

| Task | Status | Spec Binding | Notes |
| --- | --- | --- | --- |
| IF-101: Implement LangChain adapter over canonical operations | Completed | `LANGCHAIN_ADAPTER_SPEC.md` | Toolkit and runnable-style wrappers now delegate to the canonical service contract |
| IF-102: Implement LlamaIndex adapter over canonical operations | Completed | `LLAMAINDEX_ADAPTER_SPEC.md` | Query, explain, vector, and hybrid retrieval wrappers now delegate to the canonical service contract |
| IF-103: Implement Semantic Kernel adapter over canonical operations | Completed | `SEMANTIC_KERNEL_ADAPTER_SPEC.md` | Deterministic plugin/function descriptors and invocation wrappers now delegate to the canonical service contract |
| IF-104: Implement OpenAI-style direct provider tool-calling profile | Completed | `DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md` | OpenAI-style direct provider requests now execute through the canonical service layer |
| IF-105: Implement Anthropic-style tool-use profile | Completed | `DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md` | Anthropic-style tool-use payloads now execute through the same canonical provider entrypoint |
| IF-106: Implement Gemini-style function-calling profile | Completed | `DIRECT_PROVIDER_COMPATIBILITY_PROFILES_SPEC.md` | Gemini-style functionCall payloads now execute through the same canonical provider entrypoint |

### 5.3 Workstream C: Retrieval Expansion

Goal: move retrieval from helper-level behavior to certifiable runtime support.

| Task | Status | Spec Binding | Notes |
| --- | --- | --- | --- |
| IF-201: Implement provider-generated embedding acquisition path with secret handling | Pending | `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` | Current baseline only accepts caller-supplied embeddings |
| IF-202: Implement persistent index catalog and explicit retrieval lifecycle states | Pending | `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` | Current helper store lazily creates ephemeral indexes |
| IF-203: Implement engine-managed retrieval backend profile | Pending | `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` | Requires live ScratchBird integration |
| IF-204: Implement live hybrid pushdown path and planner-backed structured filter validation | Pending | `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md` | Current offline mode intentionally denies `where` pushdown |
| IF-205: Build live retrieval evaluation and certification harness | Partial | `EMBEDDING_AND_RETRIEVAL_LIFECYCLE_SPEC.md`, `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Offline evidence exists; live corpus evaluation does not |

### 5.4 Workstream D: Governed Mutation and Audit Hardening

Goal: move mutation support from inline approval checks to durable, certifiable governance.

| Task | Status | Spec Binding | Notes |
| --- | --- | --- | --- |
| IF-301: Implement durable approval record storage and lookup | Pending | `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` | Current approval evidence is inline only |
| IF-302: Implement approval expiry, revocation, and operator workflow hooks | Pending | `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` | Required before enterprise mutation claims |
| IF-303: Implement signed or externally attested audit bundle flow | Pending | `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` | Current audit bundles are deterministic but unsigned |
| IF-304: Add mutation replay/correlation checks against persisted approval evidence | Pending | `MUTATION_APPROVAL_AND_AUDIT_EVIDENCE_SPEC.md` | Must prove deny/allow correlation under restart and replay conditions |

### 5.5 Workstream E: Live Conformance and Release Certification

Goal: turn draft interface claims into live, release-grade certified profiles.

| Task | Status | Spec Binding | Notes |
| --- | --- | --- | --- |
| IF-401: Build live-native conformance harness against a real ScratchBird runtime | Partial | `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Repo selftest exists; live-native automation does not |
| IF-402: Build framework parity harness for LangChain, LlamaIndex, and Semantic Kernel | Completed | `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Release-gating framework parity artifacts now compare adapter outputs to canonical service behavior |
| IF-403: Build provider parity harness for direct tool-calling profiles | Completed | `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Release-gating provider parity artifacts now compare OpenAI-, Anthropic-, and Gemini-style payloads to canonical execution results |
| IF-404: Implement environment manifest capture and certification artifact packaging | Pending | `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md` | Needs machine-readable runtime/version descriptors |
| IF-405: Add release-candidate gate automation for claimed interface profiles | Pending | `LIVE_CONFORMANCE_AND_CERTIFICATION_SPEC.md`, `COMPATIBILITY_AND_RELEASE_NEGOTIATION_SPEC.md` | Must fail closed on stale or mismatched artifacts |

## 6. Recommended Delivery Order

1. IF-001, IF-002, IF-003
2. IF-004 and IF-005
3. IF-104 as the first external-provider normalization anchor
4. IF-101, IF-102, and IF-103
5. IF-201 through IF-205
6. IF-301 through IF-304
7. IF-401 through IF-405

Reason:

- shared control-plane contracts must exist before adapters can converge on one model
- first provider profile should prove the tool-calling normalization layer before multiplying adapters
- live certification only becomes meaningful after retrieval and governance surfaces exist in durable form

## 7. Promotion Criteria By Profile

| Profile | Minimum tasks required before `implemented` claim |
| --- | --- |
| `mcp_remote_v0` | IF-001, IF-002, IF-004, IF-005, IF-401, IF-404 |
| `langchain_v0` | IF-001, IF-003, IF-101, IF-401, IF-402 |
| `llamaindex_v0` | IF-001, IF-003, IF-102, IF-201 or IF-203, IF-401, IF-402 |
| `semantic_kernel_v0` | IF-001, IF-003, IF-103, IF-401, IF-402 |
| `provider_tool_calling_v0` | IF-001, IF-002, IF-003, IF-104, IF-105, IF-106, IF-403 |
| `streaming_async_v0` | IF-001, IF-005, IF-401 |
| `retrieval_ingest_v0` | IF-201, IF-202, IF-203, IF-204, IF-205, IF-401 |
| `governance_certification_v0` | IF-002, IF-301, IF-302, IF-303, IF-304, IF-404, IF-405 |

## 8. Immediate Next Tasks

1. Start `IF-201` and `IF-202` so retrieval moves beyond the current in-memory helper baseline.
2. Begin `IF-404` environment manifest capture so implemented profiles can advance toward release-grade certification.
3. Advance `IF-401` from partial to full live-native conformance so non-draft profile promotion criteria can be satisfied.

These are the minimum foundation tasks required before any adapter or provider implementation can be done cleanly.
