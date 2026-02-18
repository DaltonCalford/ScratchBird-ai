from __future__ import annotations

import unittest

from scratchbird_ai.policy import PolicyDeniedError
from scratchbird_ai.router import RoutingError
from scratchbird_ai.service import build_default_service
from scratchbird_ai.settings import RuntimeSettings


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_default_service()

    def test_run_query_read_only(self) -> None:
        resp = self.service.run_query(
            request_id="req_test_1",
            dialect="native",
            query_text="SELECT 1",
            mode="read_only",
            options={"limit": 2},
        )
        self.assertEqual(resp.request_id, "req_test_1")
        self.assertEqual(len(resp.result_rows), 2)

    def test_run_query_mutation_denied_without_approval(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            self.service.run_query(
                request_id="req_test_2",
                dialect="native",
                query_text="UPDATE users SET name = 'x'",
                mode="read_only",
            )

    def test_hybrid_mode_wires_http_for_native_dialect(self) -> None:
        settings = RuntimeSettings(
            adapter_mode="hybrid",
            http_base_url="http://127.0.0.1:3095",
            http_dialects=("native",),
        )
        service = build_default_service(settings=settings)

        native_adapter_name = service.adapters["native"].__class__.__name__

        self.assertEqual(native_adapter_name, "ScratchBirdHttpDialectAdapter")
        self.assertEqual(set(service.adapters.keys()), {"native"})

    def test_run_query_rejects_non_native_dialect(self) -> None:
        with self.assertRaises(RoutingError) as ctx:
            self.service.run_query(
                request_id="req_test_non_native",
                dialect="postgresql",
                query_text="SELECT 1",
                mode="read_only",
            )
        self.assertIn("supports native-only", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
