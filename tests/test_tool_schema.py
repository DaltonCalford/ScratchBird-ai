from __future__ import annotations

import unittest

from scratchbird_ai.tool_schema import (
    get_tool_descriptor,
    get_tool_descriptors,
    normalize_tool_invocation,
    normalize_tool_response,
    ToolContractError,
    error_envelope,
    require_security_context,
    validate_structured_output,
    validate_tool_arguments,
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

    def test_get_tool_descriptors_contains_execute_readonly_query(self) -> None:
        tools = {tool["tool_name"]: tool for tool in get_tool_descriptors()}
        self.assertIn("execute_readonly_query", tools)
        self.assertEqual(tools["execute_readonly_query"]["output_mode"], "json_object")
        self.assertIn("get_provider_profiles", tools)

    def test_validate_tool_arguments_rejects_unknown_field(self) -> None:
        with self.assertRaises(ToolContractError) as ctx:
            validate_tool_arguments(
                "execute_readonly_query",
                {
                    "dialect": "native",
                    "query_text": "SELECT 1",
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                    },
                    "unexpected": True,
                },
            )
        self.assertEqual(ctx.exception.error_code, "E_TOOL_INPUT_INVALID")

    def test_normalize_openai_tool_call(self) -> None:
        normalized = normalize_tool_invocation(
            payload={
                "id": "call_123",
                "request_id": "req_123",
                "function": {
                    "name": "execute_readonly_query",
                    "arguments": (
                        '{"dialect":"native","query_text":"SELECT 1","security_context":'
                        '{"tenant_id":"tenant_a","actor_id":"actor_a"}}'
                    ),
                },
            },
            interface_profile_id="provider_tool_calling_v0",
            provider_profile_id="openai_tool_calling_v0",
        )
        self.assertEqual(normalized["tool_name"], "execute_readonly_query")
        self.assertEqual(normalized["call_id"], "call_123")
        self.assertEqual(normalized["arguments"]["security_context"]["tenant_id"], "tenant_a")

    def test_normalize_anthropic_tool_use(self) -> None:
        normalized = normalize_tool_invocation(
            payload={
                "id": "call_456",
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
            interface_profile_id="provider_tool_calling_v0",
            provider_profile_id="anthropic_tool_use_v0",
        )
        self.assertEqual(normalized["tool_name"], "execute_readonly_query")
        self.assertEqual(normalized["call_id"], "call_456")
        self.assertEqual(normalized["arguments"]["options"]["max_rows"], 1)

    def test_normalize_gemini_function_call(self) -> None:
        normalized = normalize_tool_invocation(
            payload={
                "functionCall": {
                    "id": "call_789",
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
                }
            },
            interface_profile_id="provider_tool_calling_v0",
            provider_profile_id="gemini_function_calling_v0",
        )
        self.assertEqual(normalized["tool_name"], "execute_readonly_query")
        self.assertEqual(normalized["call_id"], "call_789")
        self.assertEqual(normalized["arguments"]["options"]["max_rows"], 1)

    def test_validate_structured_output_json_schema(self) -> None:
        validated = validate_structured_output(
            output_mode="json_schema",
            payload={"tools": []},
            output_schema=get_tool_descriptor("get_tool_descriptors")["output_schema"],
        )
        self.assertEqual(validated["validation_status"], "valid")
        self.assertEqual(validated["schema_id"], "tool_descriptor_catalog")

    def test_validate_provider_profile_catalog_output(self) -> None:
        validated = validate_structured_output(
            output_mode="json_schema",
            payload={"profiles": []},
            output_schema=get_tool_descriptor("get_provider_profiles")["output_schema"],
        )
        self.assertEqual(validated["validation_status"], "valid")
        self.assertEqual(validated["schema_id"], "provider_profile_catalog")

    def test_validate_structured_output_invalid_json_object(self) -> None:
        with self.assertRaises(ToolContractError) as ctx:
            validate_structured_output(output_mode="json_object", payload="not-an-object")
        self.assertEqual(ctx.exception.error_code, "E_STRUCTURED_OUTPUT_INVALID")

    def test_normalize_tool_response_wraps_success(self) -> None:
        envelope = normalize_tool_response(
            tool_name="get_tool_descriptors",
            request_id="req_1",
            call_id="call_1",
            interface_profile_id="service_internal_v0",
            trace_id="tr_1",
            result={"tools": []},
        )
        self.assertEqual(envelope["status"], "success")
        self.assertEqual(envelope["structured_output"]["validation_status"], "valid")


if __name__ == "__main__":
    unittest.main()
