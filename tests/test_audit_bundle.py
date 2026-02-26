from __future__ import annotations

import unittest

from scratchbird_ai.audit_bundle import (
    REPLAY_OUTCOMES,
    create_audit_bundle,
    replay_validate_bundle,
)


class AuditBundleTests(unittest.TestCase):
    def _base_bundle(self) -> dict:
        return create_audit_bundle(
            trace_id="tr_1",
            request_id="req_1",
            tenant_id="tenant_a",
            actor_id="actor_a",
            dialect="native",
            execution_mode="ai_analysis",
            sql_text_normalized="SELECT 1",
            compile_artifact_id="cmp_1",
            execution_artifact_id="exe_1",
            plan_json={"operator_tree": {"operator_id": "root", "operator_type": "Read", "children": []}},
            plan_hash="plan_1",
            policy_decision="allow",
            policy_rule_id="MODE-ALLOW-READ-001",
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": [],
                "context_version": 1,
            },
            approval_id=None,
            approval_token=None,
            error_code=None,
            created_at_utc="2026-02-24T18:00:00Z",
            statement_kind="read",
            sblr_hash="hash123",
        )

    def test_replay_match(self) -> None:
        bundle = self._base_bundle()
        result = replay_validate_bundle(
            bundle=bundle,
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": [],
                "context_version": 1,
            },
            expected_policy_decision="allow",
            expected_plan_hash="plan_1",
        )
        self.assertEqual(result.outcome, REPLAY_OUTCOMES["match"])

    def test_replay_detects_hash_tamper(self) -> None:
        bundle = self._base_bundle()
        bundle["policy_rule_id"] = "tampered"
        result = replay_validate_bundle(bundle=bundle)
        self.assertEqual(result.outcome, REPLAY_OUTCOMES["mismatch_hash"])

    def test_replay_detects_policy_mismatch(self) -> None:
        bundle = self._base_bundle()
        result = replay_validate_bundle(bundle=bundle, expected_policy_decision="deny")
        self.assertEqual(result.outcome, REPLAY_OUTCOMES["mismatch_policy"])


if __name__ == "__main__":
    unittest.main()
