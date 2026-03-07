from __future__ import annotations

import unittest

from scratchbird_ai.service import build_default_service


class ProviderProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_default_service()

    def test_provider_profile_catalog_marks_all_child_profiles_implemented(self) -> None:
        catalog = self.service.get_provider_profiles()
        profiles = {profile["profile_id"]: profile for profile in catalog["profiles"]}
        self.assertEqual(profiles["openai_tool_calling_v0"]["state"], "implemented")
        self.assertEqual(profiles["anthropic_tool_use_v0"]["state"], "implemented")
        self.assertEqual(profiles["gemini_function_calling_v0"]["state"], "implemented")

    def test_openai_provider_profile_executes_read_query(self) -> None:
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
        self.assertEqual(response["result"]["row_count"], 1)

    def test_anthropic_provider_profile_executes_read_query(self) -> None:
        response = self.service.invoke_provider_tool(
            provider_profile_id="anthropic_tool_use_v0",
            payload={
                "request_id": "req_provider_anthropic",
                "id": "call_provider_anthropic",
                "name": "execute_readonly_query",
                "input": {
                    "dialect": "native",
                    "query_text": "SELECT 1",
                    "security_context": {"tenant_id": "tenant_a", "actor_id": "actor_a"},
                    "options": {"max_rows": 1},
                },
            },
        )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"]["row_count"], 1)

    def test_gemini_provider_profile_executes_read_query(self) -> None:
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
                        "security_context": {"tenant_id": "tenant_a", "actor_id": "actor_a"},
                        "options": {"max_rows": 1},
                    },
                },
            },
        )
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["result"]["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
