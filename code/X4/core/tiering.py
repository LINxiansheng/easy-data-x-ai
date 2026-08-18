"""冷热分层规则与分区键/过滤条件推导(纯 Python,可单测)。

对应计划中「冷热分层,原始对象和历史数据保留在湖仓中;按需索引,
仅将热数据和高价值派生文本写入 seekdb」。

设计目标:把「某条数据属于 hot / warm / cold」的判定与「如何拼 Iceberg
分区键 / 过滤条件 / seekdb 索引标记」收敛到纯函数,让 Spark / seekdb
层只是机械执行这些规则。这样规则可单测、可进 CI。
"""

from __future__ import annotations

from datetime import date, timedelta
from enum import Enum


class Tier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


# 阈值(天):距最近访问超过该天数即降一级。可被外部覆盖。
DEFAULT_THRESHOLDS = {"hot_after_days": 2, "cold_after_days": 14}

# 哪些模态默认保留原文进入在线热索引(其余只走派生文本/冷区)。
HOT_MODALITIES = {"text", "log"}


def compute_tier(
    days_since_access: int,
    is_high_value: bool = False,
    thresholds: dict[str, int] | None = None,
) -> Tier:
    """按访问新鲜度 + 是否高价值给出一条数据的层级。

    - 高价值数据(如用户画像、会话摘要)即使久未访问也保持 hot。
    - 普通数据按距最近访问天数降级 warm -> cold。
    """
    th = thresholds or DEFAULT_THRESHOLDS
    if is_high_value:
        return Tier.HOT
    if days_since_access <= th["hot_after_days"]:
        return Tier.HOT
    if days_since_access <= th["cold_after_days"]:
        return Tier.WARM
    return Tier.COLD


def partition_key(tier: Tier, tenant: str, dt: date) -> dict[str, str]:
    """推导 Iceberg 分区键(层级/租户/日期组合,便于分区裁剪)。"""
    return {
        "tier": tier.value,
        "tenant": tenant,
        "dt": dt.isoformat(),
    }


def filter_expression(
    tier: Tier | None = None,
    tenant: str | None = None,
    date_range: tuple[date, date] | None = None,
) -> str:
    """推导用于 Iceberg 分区裁剪 / seekdb metadata 过滤的过滤条件。

    返回形如 ``dt >= '2026-08-01' AND dt <= '2026-08-31'`` 的谓词字符串,
    便于在 Spark SQL / seekdb metadata 中传入,达到只扫热面、跳过冷区的效果。
    """
    clauses: list[str] = []
    if tier is not None:
        clauses.append(f"tier = '{tier.value}'")
    if tenant is not None:
        clauses.append(f"tenant = '{tenant}'")
    if date_range is not None:
        start, end = date_range
        clauses.append(f"dt >= '{start.isoformat()}'")
        clauses.append(f"dt <= '{end.isoformat()}'")
    return " AND ".join(clauses) if clauses else "TRUE"


def asset_to_indexed_text(
    modality: str,
    size_bytes: int,
    derived_text: str,
) -> bool:
    """决定某个持久化对象是否应「写入 seekdb 索引」(按需索引)。

    规则:仅热模态与有派生文本的对象入索引;大规模模态(视频/音频)
    或早期冷态超大对象不进入在线索引。
    """
    if not derived_text.strip():
        return False
    if modality in {"video", "audio"} and size_bytes > (1 << 20):  # >1MB
        return False
    return modality in HOT_MODALITIES or bool(derived_text.strip())


def hot_scan_window(now: date, hot_days: int = 7) -> tuple[date, date]:
    """给「日常检索只扫热面」一个默认时间窗:返回 [now - hot_days, now]。"""
    return (now - timedelta(days=hot_days), now)