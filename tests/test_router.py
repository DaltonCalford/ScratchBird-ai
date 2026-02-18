from __future__ import annotations

import unittest

from scratchbird_ai.capability_matrix import load_capability_matrix
from scratchbird_ai.router import DialectRouter, RoutingError


class DialectRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = DialectRouter(matrix=load_capability_matrix())

    def test_available_dialects_contains_native(self) -> None:
        self.assertEqual(self.router.available_dialects(), ["native"])

    def test_require_capability_allows_supported_dialect(self) -> None:
        self.router.require_capability("native", "read_select")

    def test_require_capability_blocks_unsupported_dialect_capability(self) -> None:
        with self.assertRaises(RoutingError) as ctx:
            self.router.require_capability("native", "graph_ops")
        self.assertIn("lacks required capability", str(ctx.exception))

    def test_require_capability_rejects_non_native_dialect_with_policy_message(self) -> None:
        with self.assertRaises(RoutingError) as ctx:
            self.router.require_capability("postgresql", "read_select")
        self.assertIn("supports native-only", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
