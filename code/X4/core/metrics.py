"""指标汇总与基准对比计算(纯 Python,可单测)。

供 benchmark.py 生成章节可直接引用的数字表,并保证同一套计算逻辑
在 CI(纯函数)与真实集群(实际测量)上都能复用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median


@dataclass
class Provenance:
    """一次测量的来源说明,保证「数字可复现」。"""
    label: str
    generated_bytes: int
    saved_bytes: int
    dedup_ratio: float
    vector_count: int = 0
    index_dir_bytes: int = 0


@dataclass
class LatencySample:
    """一次检索延迟采样(用于 p50/p95 统计)。"""
    duration_ms: float
    scanned_bytes: int = 0
    scanned_files: int = 0
    hit: bool = True


def p50(values: list[float]) -> float:
    return round(median(sorted(values)), 3)


def p95(values: list[float]) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    idx = min(len(s) - 1, int(round(0.95 * (len(s) - 1))))
    return round(s[idx], 3)


def hit_at_k(ranks: list[int], k: int) -> float:
    """给定命中位置列表,计算 Hit@K。rank 越小越靠前(1 表示首位)。"""
    if not ranks:
        return 0.0
    hit = sum(1 for r in ranks if r <= k)
    return round(hit / len(ranks), 4)


@dataclass
class CostReport:
    """存储/索引/查询成本汇总,直接生成 benchmark 数字表。"""
    raw_bytes: int = 0
    jsonl_bytes: int = 0
    dedup_bytes: int = 0
    parquet_bytes: int = 0
    zstd_bytes: int = 0
    iceberg_metadata_bytes: int = 0
    index_bytes: int = 0
    embedding_calls: int = 0
    embedding_tokens: int = 0

    def summary(self) -> dict:
        """输出课程稿可引用的关键指标。"""
        return {
            "原始对象字节(raw)": self.raw_bytes,
            "去重后字节": self.dedup_bytes,
            "JSONL 元数据字节": self.jsonl_bytes,
            "Parquet 字节": self.parquet_bytes,
            "Parquet+Zstd 字节": self.zstd_bytes,
            "Iceberg 元数据开销": self.iceberg_metadata_bytes,
            "seekdb 索引目录字节": self.index_bytes,
            "Embedding 请求次数": self.embedding_calls,
            "Embedding Token 用量": self.embedding_tokens,
        }


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def report_savings(report: CostReport) -> dict:
    """降本收益:各环节节省的相对百分比(分母为 0 时记为 0)。"""
    return {
        "去重省空间": _ratio(report.raw_bytes - report.dedup_bytes, report.raw_bytes),
        "Parquet 压缩省空间": _ratio(report.dedup_bytes - report.parquet_bytes, report.dedup_bytes),
        "Zstd 再省空间": _ratio(report.parquet_bytes - report.zstd_bytes, report.parquet_bytes),
    }