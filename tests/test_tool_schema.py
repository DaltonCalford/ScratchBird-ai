from __future__ import annotations

import unittest

from scratchbird_ai.tool_schema import (
    ToolContractError,
    error_envelope,
    require_security_context,
    validate_options,
)


class ToolSchemaTests(unittest.TestCase):
    def test_require_security_context_normalizes_payload(self) -> None:
        normalized = require_security_context(
            {
                "security_context": {
                    "tenant_id": "tenant_a",
                    "actor_id": "actor_a",
                    "roles": ["analyst"],
                    "session_id": "sess_1",
                    "context_version": 1,
                }
            }
        )
        self.assertEqual(normalized["tenant_id"], "tenant_a")
        self.assertEqual(normalized["actor_id"], "actor_a")
        self.assertEqual(normalized["roles"], ["analyst"])

    def test_require_security_context_fails_closed(self) -> None:
        with self.assertRaises(ToolContractError) as ctx:
            require_security_context({"security_context": {"tenant_id": "tenant_a"}})
        self.assertEqual(ctx.exception.error_code, "E_POLICY_DENY")

    def test_validate_options_enforces_bounds(self) -> None:
        options = validate_options({"timeout_ms": 1, "memory_mb": 1, "max_rows": 0})
        self.assertEqual(options["timeout_ms"], 100)
        self.assertEqual(options["memory_mb"], 64)
        self.assertEqual(options["max_rows"], 1)

    def test_validate_options_rejects_hard_limit(self) -> None:
        with self.assertRaises(ToolContractError) as ctx:
            validate_options({"max_rows": 10001})
        self.assertEqual(ctx.exception.error_code, "E_LIMIT_EXCEEDED")

    def test_error_envelope_shape(self) -> None:
        env = error_envelope(
            error_code="E_POLICY_DENY",
            message="denied",
            trace_id="tr_123",
            policy_rule_id="RULE-1",
            retryable=False,
        )
        self.assertEqual(env["error_code"], "E_POLICY_DENY")
        self.assertEqual(env["trace_id"], "tr_123")
        self.assertEqual(env["policy_rule_id"], "RULE-1")
        self.assertFalse(env["retryable"])


if __name__ == "__main__":
    unittest.main()
