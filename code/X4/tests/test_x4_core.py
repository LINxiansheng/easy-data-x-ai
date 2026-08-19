"""X4 core 纯函数层单元测试(不依赖 Spark / seekdb / 集群)。"""

from __future__ import annotations

import unittest
from datetime import date

from X4.core.assets import (
    DedupStore,
    content_hash,
    ingest_bytes,
    savings_report,
)
from X4.core.embedding import EmbeddingClient, _vector_fingerprint
from X4.core.metrics import hit_at_k, p95
from X4.core.tiering import (
    HOT_MODALITIES,
    Tier,
    asset_to_indexed_text,
    compute_tier,
    filter_expression,
    hot_scan_window,
    partition_key,
)


class ContentHashTests(unittest.TestCase):
    def test_content_hash_is_sha256_hex(self):
        digest = content_hash(b"demo")
        self.assertEqual(len(digest), 64)
        self.assertTrue(digest.isalnum())

    def test_same_content_same_hash(self):
        self.assertEqual(content_hash(b"a"), content_hash(b"a"))
        self.assertNotEqual(content_hash(b"a"), content_hash(b"b"))

    def test_known_sha256_vector(self):
        # sha256(b"hi")
        self.assertEqual(
            content_hash(b"hi"),
            "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        )


class DedupStoreTests(unittest.TestCase):
    def test_duplicate_content_only_counts_reference(self):
        store = DedupStore()
        k1, new1 = ingest_bytes(store, b"demo", tenant="t1", modality="text", source="a")
        k2, new2 = ingest_bytes(store, b"demo", tenant="t1", modality="text", source="b")
        self.assertTrue(new1)
        self.assertFalse(new2)
        self.assertEqual(k1, k2)
        self.assertEqual(len(store.unique_entries), 1)

    def test_savings_report_measures_dedup_gain(self):
        store = DedupStore()
        ingest_bytes(store, b"demo", tenant="t1", modality="text", source="a")
        ingest_bytes(store, b"demo", tenant="t1", modality="text", source="b")
        report = savings_report(store)
        # bytes(len(b"demo")) == 4
        self.assertEqual(report["unique_bytes"], 4)
        self.assertEqual(report["dedup_saved_bytes"], 4)  # 第二次引用省下 4B
        self.assertEqual(report["dup_objects"], 1)

    def test_manifest_has_one_row_per_unique_object(self):
        store = DedupStore()
        ingest_bytes(store, b"x", tenant="t1", modality="image", source="p")
        ingest_bytes(store, b"x", tenant="t1", modality="image", source="q")
        ingest_bytes(store, b"y", tenant="t2", modality="text", source="r")
        self.assertEqual(len(store.manifest()), 2)
        first = next(r for r in store.manifest() if r["key"] == content_hash(b"x"))
        self.assertEqual(first["refs"], 2)


class TieringTests(unittest.TestCase):
    def test_compute_tier_by_recency(self):
        self.assertEqual(compute_tier(0), Tier.HOT)
        self.assertEqual(compute_tier(9), Tier.WARM)
        self.assertEqual(compute_tier(99), Tier.COLD)

    def test_high_value_stays_hot(self):
        self.assertEqual(compute_tier(99, is_high_value=True), Tier.HOT)

    def test_threshold_override(self):
        self.assertEqual(
            compute_tier(5, thresholds={"hot_after_days": 10, "cold_after_days": 20}),
            Tier.HOT,
        )

    def test_partition_key_shape(self):
        key = partition_key(Tier.WARM, "t-aa", date(2026, 8, 17))
        self.assertEqual(key["tier"], "warm")
        self.assertEqual(key["tenant"], "t-aa")
        self.assertEqual(key["dt"], "2026-08-17")

    def test_filter_expression(self):
        expr = filter_expression(
            Tier.HOT, "t-aa", (date(2026, 8, 1), date(2026, 8, 31))
        )
        self.assertIn("tier = 'hot'", expr)
        self.assertIn("tenant = 't-aa'", expr)
        self.assertIn("dt >= '2026-08-01'", expr)
        self.assertIn("dt <= '2026-08-31'", expr)
        self.assertEqual(filter_expression(), "TRUE")

    def test_asset_to_indexed_text(self):
        self.assertTrue(asset_to_indexed_text("text", 10, "hello"))
        self.assertFalse(asset_to_indexed_text("text", 10, ""))
        # >1MB 视频不入索引
        self.assertFalse(
            asset_to_indexed_text("video", 2 * 1024 * 1024, "desc")
        )

    def test_hot_scan_window_default(self):
        start, end = hot_scan_window(date(2026, 8, 17))
        self.assertEqual(end, date(2026, 8, 17))
        self.assertEqual(start, date(2026, 8, 10))
        self.assertIn("text", HOT_MODALITIES)


class EmbeddingTests(unittest.TestCase):
    def test_embed_many_uses_cache(self):
        client = EmbeddingClient()
        first = client.embed_many(["hello", "world"])
        second = client.embed_many(["hello"])
        self.assertEqual(len(client.cache), 2)
        self.assertEqual(first[0], second[0])
        self.assertEqual(client.cache.misses, 2)
        self.assertEqual(client.cache.hits, 1)

    def test_offline_pseudo_vectors_deterministic(self):
        client = EmbeddingClient()
        a = client.embed_one("x")
        b = client.embed_one("x")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 8)

    def test_vector_fingerprint_stable(self):
        self.assertEqual(
            _vector_fingerprint([[0.1, 0.2], [0.3]]),
            _vector_fingerprint([[0.1, 0.2], [0.3]]),
        )


class MetricsTests(unittest.TestCase):
    def test_p95(self):
        self.assertEqual(p95(list(range(1, 21))), 19)

    def test_hit_at_k(self):
        self.assertAlmostEqual(hit_at_k([1, 2, 3], 1), 1 / 3, places=4)
        self.assertEqual(hit_at_k([], 1), 0.0)


if __name__ == "__main__":
    unittest.main()