from __future__ import annotations

import unittest

from scratchbird_ai.policy import PolicyDeniedError, PolicyEngine


class PolicyEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PolicyEngine()

    def test_read_only_blocks_mutation(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            self.engine.enforce(mode="read_only", is_mutation=True, approval_token=None)

    def test_mutation_mode_requires_approval(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            self.engine.enforce(
                mode="mutation_with_approval",
                is_mutation=True,
                approval_token=None,
            )

    def test_mutation_mode_with_approval_allows(self) -> None:
        self.engine.enforce(
            mode="mutation_with_approval",
            is_mutation=True,
            approval_token="approved-token",
        )


if __name__ == "__main__":
    unittest.main()
