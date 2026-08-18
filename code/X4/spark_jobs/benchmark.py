"""基准对比:基线(重复保存/JSONL/全量索引) vs 优化(去重/Iceberg/冷热/按需索引)。

在本地/集群可运行;CI 只跑纯函数单测。输出经典 benchmark 数字表,
供章节稿直接引用。真实数值在「smoke / benchmark」两档跑出。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))

from X4.core.assets import DedupStore, ingest_bytes, savings_report  # noqa: E402
from X4.core.embedding import EmbeddingClient  # noqa: E402
from X4.core.metrics import CostReport, report_savings  # noqa: E402
from X4.spark_jobs.build_index import build_index_rows  # noqa: E402


def run(tier: str = "smoke") -> dict:
    n = {"smoke": 50, "benchmark": 2000}[tier]
    store = DedupStore()
    # 1) 生成原始对象(含大量重复,模拟多会话复用同一附件)。
    raw = 0
    for tenant in ("t-aa", "t-bb", "t-cc"):
        for i in range(n):
            blob = f"tenant={tenant} 内容#{i % 7}".encode()  # 每 7 条一重复
            raw += len(blob)
            ingest_bytes(store, blob, tenant=tenant, modality="text", source=f"s{i}")
    savings = savings_report(store)

    # 2) 构建索引(按需;多处由缓存命中)。
    embedder = EmbeddingClient()
    rows = [
        {"key": f"k{i}", "tenant": row["tenant"], "modality": "text",
         "size_bytes": row["size_bytes"], "derived_text": f"desc {i}",
         "tier": "hot"}
        for i, row in enumerate(store.manifest())
    ]
    entries = build_index_rows(rows, embedder)

    report = CostReport(
        raw_bytes=raw,
        dedup_bytes=savings["unique_bytes"],
        jsonl_bytes=len("\n".join(map(str, store.manifest()))),
        embedding_calls=embedder.stats.calls,
        embedding_tokens=embedder.stats.tokens,
        index_bytes=len(entries) * 8 * 4,  # 近似:每向量 8 维 float32
    )
    return {
        "tier": tier,
        "objects": len(store.manifest()),
        "dedup_ratio": savings["dedup_ratio"],
        "savings": report_savings(report),
        "index_entries": len(entries),
        "details": report.summary(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=("smoke", "benchmark"), default="smoke")
    args = parser.parse_args(argv)
    result = run(args.tier)
    print(f"\n=== X4 benchmark({result['tier']}) ===")
    for k, v in result["details"].items():
        print(f"  {k}: {v}")
    print(f"  -> 去重比 {result['dedup_ratio']}, 索引条目 {result['index_entries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())