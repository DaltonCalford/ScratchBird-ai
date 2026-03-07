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

    def test_get_capabilities_publishes_interface_profile_inventory(self) -> None:
        capabilities = self.service.get_capabilities()
        self.assertEqual(capabilities["tool_descriptor_version"], "1.0")
        self.assertEqual(capabilities["compatibility_version"], "2026-03-07")
        self.assertTrue(capabilities["supports"]["compatibility_negotiation"])
        self.assertEqual(
            capabilities["supports"]["structured_output_modes"],
            ["none", "json_object", "json_schema"],
        )
        self.assertIn("get_tool_descriptors", capabilities["supports"]["canonical_tools"])
        self.assertIn("get_provider_profiles", capabilities["supports"]["canonical_tools"])
        self.assertIn("get_compatibility_manifest", capabilities["supports"]["canonical_tools"])
        self.assertIn("negotiate_compatibility", capabilities["supports"]["canonical_tools"])
        profiles = {
            profile["profile_id"]: profile for profile in capabilities["interface_profiles"]
        }
        provider_profiles = {
            profile["profile_id"]: profile for profile in capabilities["provider_profiles"]
        }

        self.assertEqual(profiles["service_internal_v0"]["state"], "implemented")
        self.assertEqual(profiles["service_internal_v0"]["transport"], "in_process")
        self.assertEqual(profiles["mcp_local_v0"]["state"], "implemented")
        self.assertEqual(profiles["mcp_remote_v0"]["state"], "draft")
        self.assertEqual(profiles["provider_tool_calling_v0"]["state"], "implemented")
        self.assertEqual(profiles["retrieval_ingest_v0"]["state"], "draft")
        self.assertEqual(profiles["governance_certification_v0"]["state"], "draft")
        self.assertIn(
            "execute_readonly_query",
            profiles["mcp_local_v0"]["operation_set"],
        )
        self.assertIn(
            "add_embeddings",
            profiles["service_internal_v0"]["operation_set"],
        )
        self.assertEqual(provider_profiles["openai_tool_calling_v0"]["state"], "implemented")
        self.assertEqual(provider_profiles["anthropic_tool_use_v0"]["state"], "implemented")
        self.assertEqual(provider_profiles["gemini_function_calling_v0"]["state"], "implemented")

    def test_get_tool_descriptors_returns_catalog(self) -> None:
        catalog = self.service.get_tool_descriptors()
        names = {tool["tool_name"] for tool in catalog["tools"]}
        self.assertIn("execute_readonly_query", names)
        self.assertIn("get_tool_descriptors", names)
        self.assertIn("get_provider_profiles", names)

    def test_get_provider_profiles_returns_catalog(self) -> None:
        catalog = self.service.get_provider_profiles()
        profiles = {profile["profile_id"]: profile for profile in catalog["profiles"]}
        self.assertEqual(profiles["openai_tool_calling_v0"]["state"], "implemented")
        self.assertFalse(profiles["openai_tool_calling_v0"]["streaming_support"])

    def test_invoke_provider_tool_openai_profile(self) -> None:
        response = self.service.invoke_provider_tool(
            provider_profile_id="openai_tool_calling_v0",
            payload={
                "request_id": "req_provider_openai",
                "id": "call_provider_openai",
                "function": {
                    "name": "execute_readonly_query",
                    "arguments": (
                        '{"dialect":"native","query_text":"SELECT 1","security_context":'
                        '{"tenant_id":"tenant_a","actor_id":"actor_a"},"options":{"max_rows":1}}'
                    ),
                },
            },
        )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["provider_profile_id"], "openai_tool_calling_v0")
        self.assertEqual(response["result"]["row_count"], 1)

    def test_invoke_provider_tool_rejects_unimplemented_profile(self) -> None:
        response = self.service.invoke_provider_tool(
            provider_profile_id="unknown_profile_v0",
            payload={
                "request_id": "req_provider_anthropic",
                "id": "call_provider_anthropic",
                "name": "execute_readonly_query",
                "input": {
                    "dialect": "native",
                    "query_text": "SELECT 1",
                    "security_context": {"tenant_id": "tenant_a", "actor_id": "actor_a"},
                },
            },
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["error_code"], "E_PROVIDER_CONTRACT_UNSUPPORTED")

    def test_invoke_provider_tool_anthropic_profile(self) -> None:
        response = self.service.invoke_provider_tool(
            provider_profile_id="anthropic_tool_use_v0",
            payload={
                "request_id": "req_provider_anthropic",
                "id": "call_provider_anthropic",
                "name": "execute_readonly_query",
                "input": {
                    "dialect": "native",
                    "query_text": "SELECT 1",
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                    },
                    "options": {"max_rows": 1},
                },
            },
        )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["provider_profile_id"], "anthropic_tool_use_v0")
        self.assertEqual(response["result"]["row_count"], 1)

    def test_invoke_provider_tool_gemini_profile(self) -> None:
        response = self.service.invoke_provider_tool(
            provider_profile_id="gemini_function_calling_v0",
            payload={
                "request_id": "req_provider_gemini",
                "functionCall": {
                    "id": "call_provider_gemini",
                    "name": "execute_readonly_query",
                    "args": {
                        "dialect": "native",
                        "query_text": "SELECT 1",
                        "security_context": {
                            "tenant_id": "tenant_a",
                            "actor_id": "actor_a",
                        },
                        "options": {"max_rows": 1},
                    },
                },
            },
        )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["provider_profile_id"], "gemini_function_calling_v0")
        self.assertEqual(response["result"]["row_count"], 1)

    def test_remote_session_invocation_binds_session_security_context(self) -> None:
        service = build_default_service(
            settings=RuntimeSettings(remote_mcp_auth_token="remote-secret")
        )
        opened = service.open_remote_session(
            {
                "request_id": "req_remote_open",
                "interface_profile_id": "mcp_remote_v0",
                "protocol_version": "v0",
                "requested_transport": "https_json_request_response",
                "client_id": "remote-client",
                "client_version": "0.0.1",
                "client_capabilities": {"streaming": False},
                "auth_envelope": {
                    "auth_type": "bearer",
                    "token": "remote-secret",
                },
                "security_context_hint": {
                    "tenant_id": "tenant_remote",
                    "actor_id": "actor_remote",
                    "roles": ["remote_reader"],
                    "session_id": "sess_remote",
                    "context_version": 1,
                },
            }
        )

        response = service.invoke_remote_tool(
            session_id=opened["session_id"],
            request_id="req_remote_query",
            method="execute_readonly_query",
            params={
                "dialect": "native",
                "query_text": "SELECT 1",
                "security_context": {
                    "tenant_id": "tenant_override",
                    "actor_id": "actor_override",
                },
                "context": {
                    "security_context": {
                        "tenant_id": "tenant_override_ctx",
                        "actor_id": "actor_override_ctx",
                    }
                },
                "client_capabilities": {"requested_transport": "websocket_bidirectional"},
                "options": {"max_rows": 1},
            },
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"]["row_count"], 1)
        bundle = service.latest_audit_bundle()
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["tenant_id"], "tenant_remote")
        self.assertEqual(bundle["actor_id"], "actor_remote")

    def test_remote_session_stream_request_fails_closed(self) -> None:
        service = build_default_service(
            settings=RuntimeSettings(remote_mcp_auth_token="remote-secret")
        )
        opened = service.open_remote_session(
            {
                "client_id": "remote-client",
                "client_version": "0.0.1",
                "auth_envelope": {
                    "auth_type": "bearer",
                    "token": "remote-secret",
                    "security_context": {
                        "tenant_id": "tenant_remote",
                        "actor_id": "actor_remote",
                    },
                },
            }
        )

        response = service.invoke_remote_tool(
            session_id=opened["session_id"],
            request_id="req_remote_stream",
            method="execute_readonly_query",
            params={"dialect": "native", "query_text": "SELECT 1"},
            stream_requested=True,
        )

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["error_code"], "E_STREAM_NOT_SUPPORTED")

    def test_remote_streaming_lifecycle_exposes_events_and_continuation(self) -> None:
        service = build_default_service(
            settings=RuntimeSettings(remote_mcp_auth_token="remote-secret")
        )
        opened = service.open_remote_session(
            {
                "request_id": "req_remote_stream_open",
                "requested_transport": "https_sse_server_stream",
                "client_id": "remote-client",
                "client_version": "0.0.1",
                "auth_envelope": {
                    "auth_type": "bearer",
                    "token": "remote-secret",
                    "security_context": {
                        "tenant_id": "tenant_remote",
                        "actor_id": "actor_remote",
                        "roles": ["remote_reader"],
                    },
                },
            }
        )

        response = service.invoke_remote_tool(
            session_id=opened["session_id"],
            request_id="req_remote_stream_exec",
            method="execute_readonly_query",
            params={
                "dialect": "native",
                "query_text": "SELECT 1",
                "options": {"max_rows": 1},
            },
            stream_requested=True,
        )

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["operation_state"], "completed")
        self.assertTrue(str(response["operation_id"]).startswith("op_"))
        self.assertIsNone(response["result"])
        self.assertEqual(response["stream_channel"], f"stream:{response['operation_id']}")
        self.assertIsNotNone(response["continuation_token"])

        events = service.poll_remote_operation(
            session_id=opened["session_id"],
            operation_id=response["operation_id"],
        )
        self.assertEqual(events["operation_state"], "completed")
        self.assertTrue(events["terminal"])
        self.assertEqual(
            [event["event_type"] for event in events["events"]],
            ["accepted", "progress", "completed"],
        )
        self.assertEqual(events["events"][-1]["payload"]["result"]["row_count"], 1)

        empty_poll = service.poll_remote_operation(
            session_id=opened["session_id"],
            operation_id=response["operation_id"],
            continuation_token=events["continuation_token"],
        )
        self.assertEqual(empty_poll["events"], [])
        self.assertTrue(empty_poll["terminal"])

    def test_cancel_remote_operation_reports_already_terminal(self) -> None:
        service = build_default_service(
            settings=RuntimeSettings(remote_mcp_auth_token="remote-secret")
        )
        opened = service.open_remote_session(
            {
                "requested_transport": "https_sse_server_stream",
                "client_id": "remote-client",
                "client_version": "0.0.1",
                "auth_envelope": {
                    "auth_type": "bearer",
                    "token": "remote-secret",
                    "security_context": {
                        "tenant_id": "tenant_remote",
                        "actor_id": "actor_remote",
                    },
                },
            }
        )

        response = service.invoke_remote_tool(
            session_id=opened["session_id"],
            request_id="req_remote_stream_cancel",
            method="execute_readonly_query",
            params={"dialect": "native", "query_text": "SELECT 1"},
            stream_requested=True,
        )

        cancelled = service.cancel_remote_operation(
            session_id=opened["session_id"],
            operation_id=response["operation_id"],
            request_id="req_cancel_terminal",
            reason="user_cancelled",
        )
        self.assertEqual(cancelled["status"], "already_terminal")
        self.assertEqual(cancelled["operation_state"], "completed")

    def test_remote_session_close_invalidates_future_invocation(self) -> None:
        service = build_default_service(
            settings=RuntimeSettings(remote_mcp_auth_token="remote-secret")
        )
        opened = service.open_remote_session(
            {
                "client_id": "remote-client",
                "client_version": "0.0.1",
                "auth_envelope": {
                    "auth_type": "bearer",
                    "token": "remote-secret",
                    "security_context": {
                        "tenant_id": "tenant_remote",
                        "actor_id": "actor_remote",
                    },
                },
            }
        )

        closed = service.close_remote_session(
            session_id=opened["session_id"],
            request_id="req_remote_close",
        )
        self.assertEqual(closed["status"], "closed")

        response = service.invoke_remote_tool(
            session_id=opened["session_id"],
            request_id="req_remote_after_close",
            method="execute_readonly_query",
            params={"dialect": "native", "query_text": "SELECT 1"},
        )
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error"]["error_code"], "E_SESSION_REQUIRED")

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
