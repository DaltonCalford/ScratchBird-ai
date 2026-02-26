from __future__ import annotations

import json
import threading
import unittest
from typing import Any
from urllib import error, request

from scratchbird_ai.http_bridge import (
    BridgeCompileResult,
    BridgeError,
    BridgeExecuteResult,
    BridgeSettings,
    ScratchBirdDriverBackend,
    ScratchBirdBridgeApp,
    build_http_server,
)


class FakeBridgeBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Any]] = []

    def compile_query(
        self,
        *,
        dialect: str,
        query_text: str,
        context: dict[str, Any],
    ) -> BridgeCompileResult:
        self.calls.append(("compile", dialect, {"query_text": query_text, "context": context}))
        return BridgeCompileResult(
            statement_kind="read",
            sblr_hash="abc123",
            diagnostics=[],
            warnings=[],
        )

    def execute_query(
        self,
        *,
        dialect: str,
        query_text: str,
        options: dict[str, Any],
        compile_artifact_id: str,
    ) -> BridgeExecuteResult:
        self.calls.append(
            (
                "execute",
                dialect,
                {
                    "query_text": query_text,
                    "options": options,
                    "compile_artifact_id": compile_artifact_id,
                },
            )
        )
        return BridgeExecuteResult(rows=[{"id": 1}], notices=["ok"])

    def list_schemas(self, *, dialect: str, database: str | None = None) -> list[str]:
        self.calls.append(("list_schemas", dialect, {"database": database}))
        return ["public", "analytics"]

    def list_tables(self, *, dialect: str, schema: str) -> list[str]:
        self.calls.append(("list_tables", dialect, {"schema": schema}))
        return ["customers", "orders"]

    def describe_table(self, *, dialect: str, schema: str, table: str) -> dict[str, Any]:
        self.calls.append(("describe_table", dialect, {"schema": schema, "table": table}))
        return {
            "dialect": dialect,
            "schema": schema,
            "table": table,
            "columns": [{"name": "id", "type": "uuid", "nullable": False}],
        }


class HttpBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeBridgeBackend()
        self.settings = BridgeSettings(
            host="127.0.0.1",
            port=0,
            api_token="secret-token",
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@localhost:3092/db",
        )
        app = ScratchBirdBridgeApp(settings=self.settings, backend=self.backend)
        self.server = build_http_server(app=app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        authorized: bool = True,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        if authorized:
            headers["Authorization"] = "Bearer secret-token"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = request.Request(url=url, method=method, data=data, headers=headers)
        try:
            with request.urlopen(req, timeout=3) as resp:
                status = resp.status
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            status = exc.code
            body = exc.read().decode("utf-8")

        parsed = json.loads(body) if body else {}
        self.assertIsInstance(parsed, dict)
        return status, parsed

    def test_compile_endpoint(self) -> None:
        status, doc = self._request(
            method="POST",
            path="/v1/dialects/native/compile",
            payload={"query_text": "SELECT 1", "context": {"tenant": "t1"}},
        )
        self.assertEqual(status, 200)
        self.assertEqual(doc["statement_kind"], "read")
        self.assertEqual(doc["sblr_hash"], "abc123")
        self.assertEqual(self.backend.calls[0][0], "compile")

    def test_execute_endpoint(self) -> None:
        status, doc = self._request(
            method="POST",
            path="/v1/dialects/native/execute",
            payload={
                "compile_artifact_id": "cmp_1",
                "query_text": "SELECT 1",
                "options": {"max_rows": 10},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(doc["rows"], [{"id": 1}])
        self.assertEqual(doc["notices"], ["ok"])
        self.assertEqual(self.backend.calls[0][0], "execute")

    def test_metadata_endpoints(self) -> None:
        status, schemas_doc = self._request(
            method="GET",
            path="/v1/dialects/native/schemas?database=testdb",
        )
        self.assertEqual(status, 200)
        self.assertEqual(schemas_doc["schemas"], ["public", "analytics"])

        status, tables_doc = self._request(
            method="GET",
            path="/v1/dialects/native/schemas/public/tables",
        )
        self.assertEqual(status, 200)
        self.assertEqual(tables_doc["tables"], ["customers", "orders"])

        status, desc_doc = self._request(
            method="GET",
            path="/v1/dialects/native/schemas/public/tables/customers",
        )
        self.assertEqual(status, 200)
        self.assertEqual(desc_doc["table"], "customers")
        self.assertEqual(desc_doc["columns"][0]["name"], "id")

    def test_auth_rejection(self) -> None:
        status, doc = self._request(
            method="GET",
            path="/v1/dialects/native/schemas",
            authorized=False,
        )
        self.assertEqual(status, 401)
        self.assertIn("error", doc)

    def test_non_native_dialect_rejection_message(self) -> None:
        status, doc = self._request(
            method="GET",
            path="/v1/dialects/postgresql/schemas",
        )
        self.assertEqual(status, 404)
        self.assertIn("error", doc)
        self.assertIn("Unsupported dialect", doc["error"]["message"])
        self.assertIn("native", doc["error"]["message"])


class BridgeConnectionSettingsTests(unittest.TestCase):
    def test_listener_only_setup_maps_to_direct_listener(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="listener-only",
        )
        kwargs = settings.resolve_connect_kwargs("native")
        self.assertEqual(kwargs["dsn"], "scratchbird://user:pass@127.0.0.1:3092/main")
        self.assertEqual(kwargs["protocol"], "native")
        self.assertEqual(kwargs["transport_mode"], "inet_listener")
        self.assertEqual(kwargs["front_door_mode"], "direct")

    def test_managed_setup_maps_to_manager_proxy_and_includes_manager_fields(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="managed",
            manager_auth_token="token123",
            manager_username="admin",
            manager_database="main",
            manager_connection_profile="native_v3",
            manager_client_intent="native_v3",
            manager_client_flags=7,
            manager_auth_fast_path=False,
        )
        kwargs = settings.resolve_connect_kwargs("native")
        self.assertEqual(kwargs["transport_mode"], "managed")
        self.assertEqual(kwargs["front_door_mode"], "manager_proxy")
        self.assertEqual(kwargs["manager_auth_token"], "token123")
        self.assertEqual(kwargs["manager_username"], "admin")
        self.assertEqual(kwargs["manager_database"], "main")
        self.assertEqual(kwargs["manager_connection_profile"], "native_v3")
        self.assertEqual(kwargs["manager_client_intent"], "native_v3")
        self.assertEqual(kwargs["manager_client_flags"], 7)
        self.assertFalse(kwargs["manager_auth_fast_path"])

    def test_managed_setup_requires_manager_token(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="managed",
        )
        with self.assertRaisesRegex(BridgeError, "manager_auth_token"):
            settings.resolve_connect_kwargs("native")

    def test_managed_setup_accepts_manager_token_from_dsn(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main?manager_auth_token=abc123",
            server_setup="managed",
        )
        kwargs = settings.resolve_connect_kwargs("native")
        self.assertEqual(kwargs["transport_mode"], "managed")
        self.assertEqual(kwargs["front_door_mode"], "manager_proxy")

    def test_front_door_manager_proxy_forces_managed_transport(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="listener-only",
            front_door_mode="managed",
            manager_auth_token="abc123",
        )
        kwargs = settings.resolve_connect_kwargs("native")
        self.assertEqual(kwargs["front_door_mode"], "manager_proxy")
        self.assertEqual(kwargs["transport_mode"], "managed")

    def test_ipc_and_embedded_setup_mapping(self) -> None:
        ipc_settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="ipc-only",
            ipc_method="unix",
            ipc_path="/tmp/scratchbird-main.sock",
        )
        ipc_kwargs = ipc_settings.resolve_connect_kwargs("native")
        self.assertEqual(ipc_kwargs["transport_mode"], "local_ipc")
        self.assertEqual(ipc_kwargs["front_door_mode"], "direct")
        self.assertEqual(ipc_kwargs["ipc_method"], "unix")
        self.assertEqual(ipc_kwargs["ipc_path"], "/tmp/scratchbird-main.sock")

        embedded_settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="embedded",
        )
        embedded_kwargs = embedded_settings.resolve_connect_kwargs("native")
        self.assertEqual(embedded_kwargs["transport_mode"], "embedded")
        self.assertEqual(embedded_kwargs["front_door_mode"], "direct")
        self.assertFalse(embedded_kwargs["shared"])
        self.assertEqual(embedded_kwargs["connection_scope"], "private")
        self.assertTrue(embedded_kwargs["embedded_single_connection"])

    def test_auth_plugin_connect_kwargs_are_forwarded(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="listener-only",
            auth_method_id="scratchbird.auth.proxy_assertion",
            auth_method_payload="assertion.jwt",
            auth_payload_json='{"principal":"proxy"}',
            auth_payload_b64="cHJveHk=",
            auth_provider_profile="corp_ldap_primary",
            auth_required_methods=("scratchbird.auth.proxy_assertion",),
            auth_forbidden_methods=("scratchbird.auth.password_compat",),
            auth_require_channel_binding=True,
            workload_identity_token="workload.jwt",
            proxy_principal_assertion="proxy.jwt",
            ldap_bind_dn="uid=alice,ou=people,dc=example,dc=com",
            kerberos_spn="postgres/db.internal@EXAMPLE.COM",
            radius_username="ops_user",
            pam_service="scratchbird-login",
        )
        kwargs = settings.resolve_connect_kwargs("native")
        self.assertEqual(kwargs["auth_method_id"], "scratchbird.auth.proxy_assertion")
        self.assertEqual(kwargs["auth_method_payload"], "assertion.jwt")
        self.assertEqual(kwargs["auth_payload_json"], '{"principal":"proxy"}')
        self.assertEqual(kwargs["auth_payload_b64"], "cHJveHk=")
        self.assertEqual(kwargs["auth_provider_profile"], "corp_ldap_primary")
        self.assertEqual(kwargs["auth_required_methods"], ["scratchbird.auth.proxy_assertion"])
        self.assertEqual(kwargs["auth_forbidden_methods"], ["scratchbird.auth.password_compat"])
        self.assertTrue(kwargs["auth_require_channel_binding"])
        self.assertEqual(kwargs["workload_identity_token"], "workload.jwt")
        self.assertEqual(kwargs["proxy_principal_assertion"], "proxy.jwt")
        self.assertEqual(kwargs["ldap_bind_dn"], "uid=alice,ou=people,dc=example,dc=com")
        self.assertEqual(kwargs["kerberos_spn"], "postgres/db.internal@EXAMPLE.COM")
        self.assertEqual(kwargs["radius_username"], "ops_user")
        self.assertEqual(kwargs["pam_service"], "scratchbird-login")

    def test_rejects_overlapping_auth_pinning_methods(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            auth_required_methods=("scratchbird.auth.scram_sha_256",),
            auth_forbidden_methods=("scratchbird.auth.scram_sha_256",),
        )
        with self.assertRaisesRegex(BridgeError, "required and forbidden"):
            settings.resolve_connect_kwargs("native")


class DriverConnectWiringTests(unittest.TestCase):
    class _FakeConnection:
        def close(self) -> None:
            return

    class _FakeScratchBirdModule:
        def __init__(self) -> None:
            self.last_kwargs: dict[str, Any] | None = None

        def connect(self, **kwargs: Any) -> "DriverConnectWiringTests._FakeConnection":
            self.last_kwargs = kwargs
            return DriverConnectWiringTests._FakeConnection()

    def test_backend_connect_uses_resolved_kwargs(self) -> None:
        settings = BridgeSettings(
            enabled_dialects=("native",),
            default_dsn="scratchbird://user:pass@127.0.0.1:3092/main",
            server_setup="managed",
            manager_auth_token="token123",
            manager_client_flags=3,
            auth_required_methods=("scratchbird.auth.scram_sha_256",),
        )

        backend = object.__new__(ScratchBirdDriverBackend)
        backend.settings = settings
        fake_driver = self._FakeScratchBirdModule()
        backend._scratchbird = fake_driver
        backend._protocol = None

        conn = backend._connect("native")
        try:
            self.assertIsNotNone(fake_driver.last_kwargs)
            kwargs = fake_driver.last_kwargs or {}
            self.assertEqual(kwargs["transport_mode"], "managed")
            self.assertEqual(kwargs["front_door_mode"], "manager_proxy")
            self.assertEqual(kwargs["manager_auth_token"], "token123")
            self.assertEqual(kwargs["manager_client_flags"], 3)
            self.assertEqual(kwargs["auth_required_methods"], ["scratchbird.auth.scram_sha_256"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
