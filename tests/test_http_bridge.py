from __future__ import annotations

import json
import threading
import unittest
from typing import Any
from urllib import error, request

from scratchbird_ai.http_bridge import (
    BridgeCompileResult,
    BridgeExecuteResult,
    BridgeSettings,
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


if __name__ == "__main__":
    unittest.main()
