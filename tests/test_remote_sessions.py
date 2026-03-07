from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from scratchbird_ai.remote_sessions import RemoteSessionManager
from scratchbird_ai.tool_schema import ToolContractError


class RemoteSessionManagerTests(unittest.TestCase):
    def _manager(self) -> RemoteSessionManager:
        return RemoteSessionManager(auth_token="secret-token")

    def _capabilities(self) -> dict:
        return {"service": "scratchbird-ai", "interface_profiles": [{"profile_id": "mcp_remote_v0"}]}

    def _request(self) -> dict:
        return {
            "request_id": "req_remote_open",
            "interface_profile_id": "mcp_remote_v0",
            "protocol_version": "v0",
            "requested_transport": "https_json_request_response",
            "client_id": "remote-client",
            "client_version": "0.0.1",
            "client_capabilities": {"streaming": False},
            "auth_envelope": {
                "auth_type": "bearer",
                "token": "secret-token",
            },
            "security_context_hint": {
                "tenant_id": "tenant_remote",
                "actor_id": "actor_remote",
                "roles": ["reader"],
                "session_id": "sess_remote",
                "context_version": 1,
            },
        }

    def test_open_session_accepts_top_level_security_context_hint(self) -> None:
        opened = self._manager().open_session(
            self._request(),
            capability_advertisement=self._capabilities(),
        )

        self.assertEqual(opened["request_id"], "req_remote_open")
        self.assertEqual(opened["interface_profile_id"], "mcp_remote_v0")
        self.assertEqual(opened["negotiated_transport"], "https_json_request_response")
        self.assertEqual(opened["capability_advertisement"]["service"], "scratchbird-ai")
        self.assertTrue(opened["session_id"].startswith("sess_"))

    def test_open_session_rejects_bad_token(self) -> None:
        request = self._request()
        request["auth_envelope"] = {
            "auth_type": "bearer",
            "token": "wrong-token",
            "security_context": request["security_context_hint"],
        }
        request.pop("security_context_hint", None)

        with self.assertRaises(ToolContractError) as ctx:
            self._manager().open_session(
                request,
                capability_advertisement=self._capabilities(),
            )
        self.assertEqual(ctx.exception.error_code, "E_POLICY_DENY")

    def test_require_session_expires_after_ttl(self) -> None:
        manager = RemoteSessionManager(auth_token="secret-token", session_ttl_sec=60)
        opened_at = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        opened = manager.open_session(
            self._request(),
            capability_advertisement=self._capabilities(),
            now_utc=opened_at,
        )

        with self.assertRaises(ToolContractError) as ctx:
            manager.require_session(
                opened["session_id"],
                now_utc=opened_at + timedelta(seconds=61),
            )
        self.assertEqual(ctx.exception.error_code, "E_SESSION_REQUIRED")

    def test_close_session_is_idempotent(self) -> None:
        manager = self._manager()
        opened = manager.open_session(
            self._request(),
            capability_advertisement=self._capabilities(),
        )

        first = manager.close_session(session_id=opened["session_id"], request_id="req_close_1")
        second = manager.close_session(session_id=opened["session_id"], request_id="req_close_2")

        self.assertEqual(first["status"], "closed")
        self.assertEqual(second["status"], "already_closed")


if __name__ == "__main__":
    unittest.main()
