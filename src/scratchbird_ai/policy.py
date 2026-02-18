"""Policy evaluation for query safety and operation mode controls."""

from __future__ import annotations

from dataclasses import dataclass


class PolicyDeniedError(RuntimeError):
    """Raised when a request violates platform policy."""


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    rule_id: str
    reason: str


class PolicyEngine:
    """Minimal policy engine for P0/P1 scaffolding."""

    def evaluate(
        self,
        *,
        mode: str,
        is_mutation: bool,
        approval_token: str | None,
    ) -> PolicyDecision:
        if mode == "read_only" and is_mutation:
            return PolicyDecision(
                allowed=False,
                rule_id="POLICY-READ-ONLY-001",
                reason="Mutations are blocked in read_only mode",
            )

        if mode == "mutation_with_approval" and is_mutation and not approval_token:
            return PolicyDecision(
                allowed=False,
                rule_id="POLICY-APPROVAL-001",
                reason="Missing approval token for mutation mode",
            )

        return PolicyDecision(
            allowed=True,
            rule_id="POLICY-ALLOW-000",
            reason="Request satisfies policy",
        )

    def enforce(self, *, mode: str, is_mutation: bool, approval_token: str | None) -> None:
        decision = self.evaluate(
            mode=mode,
            is_mutation=is_mutation,
            approval_token=approval_token,
        )
        if not decision.allowed:
            raise PolicyDeniedError(f"{decision.rule_id}: {decision.reason}")
