"""X4 spark_jobs 纯函数测试:验证查询 / 索引 / 基准的核心逻辑(不依赖集群)。"""

from __future__ import annotations

import unittest
from datetime import date

from X4.core.embedding import EmbeddingClient
from X4.core.metrics import p50, p95, report_savings, CostReport
from X4.spark_jobs.benchmark import run as benchmark_run
from X4.spark_jobs.build_index import build_index_rows, should_index
from X4.spark_jobs.query import simulate_scan, hot_query
from X4.spark_jobs.write_iceberg import build_manifest


class BuildManifestTests(unittest.TestCase):
    def test_manifest_adds_tier_and_partition(self):
        rows = build_manifest(
            [
                {"tenant": "t-aa", "modality": "text", "key": "k1",
                 "size_bytes": 10, "derived_text": "hi",
                 "created": "2026-08-17"},
            ],
            now=date(2026, 8, 17),
        )
        self.assertEqual(rows[0]["tier"], "hot")
        self.assertEqual(rows[0]["partition_dt"], "2026-08-17")


class BuildIndexTests(unittest.TestCase):
    def test_should_index_filters_cold_and_large(self):
        self.assertTrue(should_index("text", 10, "hello"))
        self.assertFalse(should_index("text", 10, ""))
        self.assertFalse(should_index("video", 2 * 1024 * 1024, "desc"))

    def test_build_index_rows_skips_non_indexable(self):
        rows = [
            {"key": "k-hot", "tenant": "t-aa", "modality": "text",
             "size_bytes": 10, "derived_text": "hello", "tier": "hot"},
            {"key": "k-cold", "tenant": "t-aa", "modality": "video",
             "size_bytes": 5 * 1024 * 1024, "derived_text": "desc", "tier": "cold"},
            {"key": "k-none", "tenant": "t-bb", "modality": "text",
             "size_bytes": 10, "derived_text": "", "tier": "warm"},
        ]
        entries = build_index_rows(rows, EmbeddingClient())
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "k-hot")


class QueryTests(unittest.TestCase):
    def test_hot_query_excludes_cold_filter(self):
        def search(query, expr):
            self.assertIn("tier = 'hot'", expr)
            return [1, 2]
        result = hot_query("q", "t-aa", search, repeats=3)
        self.assertLess(result["p50_ms"], 1.0)  # 亚毫秒/近零
        # search 每次返回 [1,2],共 6 个 rank;@1 中 3 个 -> 0.5
        self.assertEqual(result["hit_at_1"], 0.5)
        self.assertIn("tier = 'hot'", result["filter"])

    def test_cold_filter_included_in_report(self):
        # 冷层查询通过 filter_expression 表达,能在不连集群时验证过滤串。
        from X4.spark_jobs.query import cold_query

        scanned = {}

        def scan(filter_expr):
            scanned["expr"] = filter_expr
            return (3, 1200)

        result = cold_query("q", "t-aa", scan, warm_up=False)
        self.assertEqual(result["scanned_files"], 3)
        self.assertEqual(result["scanned_bytes"], 1200)
        self.assertIn("tier = 'cold'", scanned["expr"])

    def test_simulate_scan_matches_filter(self):
        files, bytes_scanned = simulate_scan(
            "tier = 'cold' AND tenant = 't-aa'",
            {"hot": 100, "cold": 500},
        )
        self.assertEqual(files, 1)
        self.assertEqual(bytes_scanned, 500)


class MetricsIntegrationTests(unittest.TestCase):
    def test_p50_p95(self):
        vals = list(range(1, 21))
        self.assertEqual(p50(vals), 10.5)
        self.assertEqual(p95(vals), 19)

    def test_benchmark_smoke_runs(self):
        result = benchmark_run("smoke")
        self.assertGreater(result["objects"], 0)
        self.assertGreater(result["dedup_ratio"], 0)
        self.assertGreater(result["index_entries"], 0)


if __name__ == "__main__":
    unittest.main()