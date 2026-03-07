# Early Beta Known Gaps

Date: 2026-03-07
Scope: `ScratchBird-ai` early beta (`0.1.0`)

## 1. Functional Gaps

- Compile-repair is still absent; compile failures do not yet enter a bounded remediation loop.
- Explain/trace data exists at the helper and service level, but live bridge-backed explain validation is still limited.
- Native live-workload coverage is narrower than the in-process and fake-backend contract coverage.

## 2. Governance and Security Gaps

- Approval-gated mutation exists, but approval evidence is not yet durable or externally auditable.
- Fine-grained authorization and tenant boundary policy are stronger than the February baseline, but still not production-complete.
- Quotas, cost attribution, and rate limiting are not implemented.

## 3. Operational Gaps

- Full retry/circuit-breaker policy is not standardized across external calls.
- No published production SLO dashboard package or operator runbook bundle is checked into this repository.
- Parser/compiler compatibility enforcement is still policy-by-documentation rather than fail-closed compatibility negotiation.

## 4. Documentation and Release Gaps

- The older numbered `ScratchBird_AI_Specifications` suite is broader than the shipped code and should be treated as research/history, not the current release contract.
- Release readiness now depends on [EARLY_BETA_CONFORMANCE_GATES.md](/home/dcalford/CliWork/ScratchBird-ai/docs/releases/EARLY_BETA_CONFORMANCE_GATES.md); that contract should remain aligned with the actual code surface.
- Operator troubleshooting for real server connectivity and live bridge failures still needs a fuller playbook.

## 5. Exit Criteria Toward The Next Milestone

1. Add compile-repair with deterministic limits and coverage.
2. Validate live native bridge behavior against a real ScratchBird server in CI or gated release workflow.
3. Implement durable approval evidence plus negative tests proving fail-closed behavior.
4. Add quotas/rate limits and basic resilience policy.
