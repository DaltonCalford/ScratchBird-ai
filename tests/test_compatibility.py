from __future__ import annotations

import unittest

from scratchbird_ai.service import build_default_service
from scratchbird_ai.tool_schema import ToolContractError


class CompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_default_service()

    def test_get_compatibility_manifest_is_machine_readable(self) -> None:
        manifest = self.service.get_compatibility_manifest()
        self.assertEqual(manifest["manifest_version"], "2026-03-07")
        self.assertEqual(manifest["release_version"], "0.1.0")
        self.assertTrue(manifest["interface_profiles"])
        self.assertTrue(manifest["transport_support"])

    def test_negotiate_compatibility_supports_local_service_profile(self) -> None:
        response = self.service.negotiate_compatibility(
            {
                "request_id": "req_compat_ok",
                "interface_profile_id": "service_internal_v0",
                "requested_profile_version": "v0",
                "requested_transport": "in_process",
                "client_component_versions": {"scratchbird_ai": "0.1.0"},
            }
        )
        self.assertEqual(response["negotiation_status"], "supported")
        self.assertIsNone(response["error"])

    def test_negotiate_compatibility_blocks_draft_profile(self) -> None:
        response = self.service.negotiate_compatibility(
            {
                "request_id": "req_compat_blocked",
                "interface_profile_id": "mcp_remote_v0",
                "requested_profile_version": "v0",
                "requested_transport": "https_json_request_response",
            }
        )
        self.assertEqual(response["negotiation_status"], "blocked")
        self.assertEqual(response["error"]["error_code"], "E_INTERFACE_PROFILE_UNSUPPORTED")

    def test_compile_query_rejects_incompatible_client_request(self) -> None:
        with self.assertRaises(ToolContractError) as ctx:
            self.service.compile_query(
                dialect="native",
                query_text="SELECT 1",
                context={
                    "security_context": {
                        "tenant_id": "tenant_a",
                        "actor_id": "actor_a",
                        "roles": ["analyst"],
                        "session_id": "sess_1",
                        "context_version": 1,
                    },
                    "client_capabilities": {
                        "interface_profile_id": "mcp_remote_v0",
                        "requested_profile_version": "v0",
                        "requested_transport": "https_json_request_response",
                    },
                },
            )
        self.assertEqual(ctx.exception.error_code, "E_INTERFACE_PROFILE_UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
