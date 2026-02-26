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
            context={
                "security_context": {
                    "tenant_id": "tenant_a",
                    "actor_id": "actor_a",
                    "roles": ["analyst"],
                    "session_id": "sess_1",
                    "context_version": 1,
                }
            },
        )
        self.assertEqual(resp.request_id, "req_test_1")
        self.assertEqual(resp.row_count, 2)
        self.assertEqual(len(resp.result_rows), 2)

    def test_run_query_mutation_denied_without_approval(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            self.service.run_query(
                request_id="req_test_2",
                dialect="native",
                query_text="UPDATE users SET name = 'x'",
                mode="read_only",
                context={
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                        "roles": ["analyst"],
                        "session_id": "sess_1",
                        "context_version": 1,
                    }
                },
            )

    def test_run_query_denies_missing_security_context(self) -> None:
        with self.assertRaises(PolicyDeniedError) as ctx:
            self.service.run_query(
                request_id="req_missing_ctx",
                dialect="native",
                query_text="SELECT 1",
                mode="ai_analysis",
                context={},
            )
        self.assertEqual(ctx.exception.error_code, "E_POLICY_DENY")
        bundle = self.service.latest_audit_bundle()
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["request_id"], "req_missing_ctx")
        self.assertEqual(bundle["policy_decision"], "deny")

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
                context={
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                        "roles": [],
                        "session_id": "sess_1",
                        "context_version": 1,
                    }
                },
            )
        self.assertIn("supports native-only", str(ctx.exception))

    def test_run_query_emits_allow_audit_bundle(self) -> None:
        response = self.service.run_query(
            request_id="req_audit_allow",
            dialect="native",
            query_text="SELECT 1",
            mode="ai_analysis",
            context={
                "security_context": {
                    "tenant_id": "tenant_a",
                    "actor_id": "actor_a",
                    "roles": ["analyst"],
                    "session_id": "sess_1",
                    "context_version": 1,
                }
            },
        )
        bundle = self.service.latest_audit_bundle()
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["request_id"], response.request_id)
        self.assertEqual(bundle["policy_decision"], "allow")
        self.assertEqual(bundle["tenant_id"], "tenant_a")

    def test_run_query_emits_deny_audit_bundle(self) -> None:
        with self.assertRaises(PolicyDeniedError):
            self.service.run_query(
                request_id="req_audit_deny",
                dialect="native",
                query_text="UPDATE t SET c=1",
                mode="ai_analysis",
                context={
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                        "roles": ["analyst"],
                        "session_id": "sess_1",
                        "context_version": 1,
                    }
                },
            )
        bundle = self.service.latest_audit_bundle()
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["request_id"], "req_audit_deny")
        self.assertEqual(bundle["policy_decision"], "deny")
        self.assertEqual(bundle["error_code"], "E_POLICY_DENY")

    def test_execute_readonly_query_canonical_tool(self) -> None:
        response = self.service.execute_readonly_query(
            request_id="req_tool_read",
            dialect="native",
            query_text="SELECT 1",
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            },
            options={"max_rows": 1},
        )
        self.assertEqual(response["row_count"], 1)
        self.assertTrue(response["compile_artifact_id"].startswith("cmp_"))

    def test_vector_and_hybrid_search_engine_free(self) -> None:
        self.service.add_embeddings(
            index_id="idx_docs",
            dimension=3,
            records=[
                {
                    "vector_id": "doc-1#1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"document_id": "doc-1", "text": "north overdue invoice"},
                }
            ],
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            },
        )
        vector = self.service.vector_search(
            index_id="idx_docs",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            },
        )
        self.assertEqual(vector["results"][0]["metadata"]["document_id"], "doc-1")

        hybrid = self.service.hybrid_search(
            dialect="native",
            query_text="overdue north invoice",
            query_embedding=[0.1, 0.2, 0.3],
            vector_index_id="idx_docs",
            top_k=5,
            security_context={
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            },
            sql_filter={"metadata": {"document_id": "doc-1"}},
        )
        self.assertEqual(hybrid["results"][0]["document_id"], "doc-1")

    def test_compile_artifact_id_is_deterministic(self) -> None:
        context = {
            "security_context": {
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            }
        }
        first = self.service.compile_query(
            dialect="native",
            query_text="SELECT 1",
            context=context,
        )
        second = self.service.compile_query(
            dialect="native",
            query_text="SELECT   1",
            context=context,
        )
        self.assertEqual(first.compile_artifact_id, second.compile_artifact_id)

    def test_execution_artifact_id_changes_with_attempt_index(self) -> None:
        context = {
            "security_context": {
                "tenant_id": "tenant_a",
                "actor_id": "actor_a",
                "roles": ["analyst"],
                "session_id": "sess_1",
                "context_version": 1,
            }
        }
        compiled = self.service.compile_query(
            dialect="native",
            query_text="SELECT 1",
            context=context,
        )
        first = self.service.execute_compiled(
            compile_artifact_id=compiled.compile_artifact_id,
            options={"max_rows": 1},
            mode="ai_analysis",
        )
        second = self.service.execute_compiled(
            compile_artifact_id=compiled.compile_artifact_id,
            options={"max_rows": 1},
            mode="ai_analysis",
        )
        self.assertNotEqual(first.execution_artifact_id, second.execution_artifact_id)


if __name__ == "__main__":
    unittest.main()
