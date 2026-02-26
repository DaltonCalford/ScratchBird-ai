from __future__ import annotations

import unittest

from scratchbird_ai.retrieval import InMemoryRetrievalStore, RetrievalError


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryRetrievalStore()
        self.security_context = {
            "tenant_id": "tenant_a",
            "actor_id": "actor_a",
            "roles": ["analyst"],
            "session_id": "sess_1",
            "context_version": 1,
        }
        self.store.add_embeddings(
            index_id="idx_docs",
            dimension=3,
            records=[
                {
                    "vector_id": "doc-1#1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"document_id": "doc-1", "text": "north overdue invoice"},
                },
                {
                    "vector_id": "doc-2#1",
                    "embedding": [0.3, 0.1, 0.0],
                    "metadata": {"document_id": "doc-2", "text": "south paid invoice"},
                },
            ],
            security_context=self.security_context,
        )

    def test_vector_search_returns_deterministic_order(self) -> None:
        result = self.store.vector_search(
            index_id="idx_docs",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=2,
            filters={},
            include_vectors=False,
            security_context=self.security_context,
        )
        ids = [row["vector_id"] for row in result["results"]]
        self.assertEqual(ids, ["doc-1#1", "doc-2#1"])
        self.assertTrue(result["rls_applied"])

    def test_hybrid_search_is_supported_offline_for_metadata_filter(self) -> None:
        result = self.store.hybrid_search(
            dialect="native",
            query_text="overdue invoice north",
            query_embedding=[0.1, 0.2, 0.3],
            vector_index_id="idx_docs",
            sql_filter={"metadata": {"document_id": "doc-1"}},
            weights={"vector": 0.6, "lexical": 0.3, "structured": 0.1},
            top_k=5,
            security_context=self.security_context,
        )
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["document_id"], "doc-1")

    def test_hybrid_search_rejects_where_filter_without_engine_pushdown(self) -> None:
        with self.assertRaises(RetrievalError) as ctx:
            self.store.hybrid_search(
                dialect="native",
                query_text="invoice",
                query_embedding=[0.1, 0.2, 0.3],
                vector_index_id="idx_docs",
                sql_filter={"where": "status = 'OVERDUE'"},
                weights=None,
                top_k=5,
                security_context=self.security_context,
            )
        self.assertEqual(ctx.exception.error_code, "E_FILTER_PUSHDOWN_UNAVAILABLE")

    def test_add_embeddings_blocks_cross_tenant_records(self) -> None:
        with self.assertRaises(RetrievalError) as ctx:
            self.store.add_embeddings(
                index_id="idx_docs",
                dimension=3,
                records=[
                    {
                        "vector_id": "doc-x#1",
                        "embedding": [0.0, 0.1, 0.2],
                        "metadata": {"tenant_id": "tenant_b"},
                    }
                ],
                security_context=self.security_context,
            )
        self.assertEqual(ctx.exception.error_code, "E_POLICY_DENY")


if __name__ == "__main__":
    unittest.main()
