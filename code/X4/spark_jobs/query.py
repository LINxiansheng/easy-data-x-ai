"""查询层:热查询(扫热面+Hit@K+延迟)与冷查询(扫描文件数/字节+回温)。

纯 Python 单测优先;真实 seekdb 调用由运行时按 README 注入。
核心区别对应计划「热查询 p50/p95 延迟与 Hit@K」与
「冷查询扫描文件数、扫描字节数和回温时间」。
"""

from __future__ import annotations

import random
import sys
import time as _time
from pathlib import Path
from typing import Callable, Sequence

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))

from X4.core.metrics import LatencySample, hit_at_k, p50, p95  # noqa: E402
from X4.core.tiering import Tier, filter_expression, hot_scan_window  # noqa: E402

# 检索函数: 输入 query + 过滤谓词, 返回排序后的命中 rank 列表(越前越相关)。
SearchFn = Callable[[str, str], list[int]]


def hot_query(
    query: str,
    tenant: str,
    search: SearchFn,
    *,
    repeats: int = 10,
) -> dict:
    """热层查询:默认只扫 hot 检索面,测 p50/p95 与 Hit@K。"""
    expr = filter_expression(Tier.HOT, tenant)
    latencies: list[float] = []
    ranks: list[int] = []
    for _ in range(repeats):
        start = _time.perf_counter()
        result = search(query, expr)
        latencies.append((_time.perf_counter() - start) * 1000)
        ranks.extend(result)
    return {
        "filter": expr,
        "p50_ms": p50(latencies),
        "p95_ms": p95(latencies),
        "hit_at_1": hit_at_k(ranks, 1),
        "hit_at_3": hit_at_k(ranks, 3),
        "candidates": len(ranks),
    }


def cold_query(
    query: str,
    tenant: str,
    scan_metadata: Callable[[str], tuple[int, int]],
    *,
    warm_up: bool = False,
) -> dict:
    """冷层查询:记录扫描文件数与字节,可测回温(首次冷访问变慢的代价)。"""
    expr = filter_expression(Tier.COLD, tenant)
    total_ms = 0.0
    files, bytes_scanned = scan_metadata(expr)
    # 回温:首次访问冷区需执行一次全量扫描(体现"冷数据首次访问变慢")。
    if warm_up:
        start = _time.perf_counter()
        files, bytes_scanned = scan_metadata(expr)
        total_ms = (_time.perf_counter() - start) * 1000
    return {
        "filter": expr,
        "scanned_files": files,
        "scanned_bytes": bytes_scanned,
        "warm_up_ms": round(total_ms, 3),
    }


def simulate_scan(filter_expr: str, fake_tables: dict) -> tuple[int, int]:
    """极简模拟:给定过滤谓词,返回被扫描的 (文件数, 字节数),便于本地演示。"""
    files = 0
    bytes_scanned = 0
    for tier, size in fake_tables.items():
        if tier in filter_expr:
            bytes_scanned += size
            files += 1
    return files, bytes_scanned


if __name__ == "__main__":
    expr = filter_expression(Tier.HOT, "t-aa")
    print(f">>> 热查询过滤: {expr}")
    print(">>> p50/p95/Hit@K 与真实扫描需在集群/运行时注入 search 使用。")