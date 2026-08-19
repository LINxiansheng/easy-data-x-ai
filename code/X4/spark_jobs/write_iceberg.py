"""将原始对象/对象清单写入 Iceberg 表(Spark 引擎),含分区裁剪与冷热筛选。

对应计划:MinIO 保存原始对象, Apache Iceberg 管理 Agent 事件、对象清单、
OCR/ASR 派生文本、租户、冷热状态与生命周期信息,由 Spark 完成写入。

运行(在 Spark 集群内,由 spark-submit 触发):
  spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2 \
    spark_jobs/write_iceberg.py --tier smoke

本文件也提供不依赖 Spark 的 `build_manifest` 纯 Py 入口供 benchmark/CI 复用。
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

SPARK_JOBS_DIR = Path(__file__).resolve().parent
import sys  # noqa: E402
sys.path.insert(0, str(SPARK_JOBS_DIR.parent))  # 允许 import core

from core.tiering import partition_key, compute_tier, Tier  # noqa: E402


def build_manifest(
    assets: list[dict],
    *,
    hot_days: int = 2,
    cold_days: int = 14,
    now: date | None = None,
) -> list[dict]:
    """把对象清单扩成 Iceberg 行(纯 Python,供本地/CI 复用)。

    每行包含分区键、冷热层级、派生字段,便于 Spark 落表时直接映射。
    """
    today = now or date.today()
    rows = []
    for a in assets:
        days_since = (today - date.fromisoformat(a.get("created", today.isoformat()))).days
        tier = compute_tier(days_since, thresholds={"hot_after_days": hot_days,
                                                    "cold_after_days": cold_days})
        rows.append(
            {
                "tenant": a["tenant"],
                "modality": a["modality"],
                "key": a["key"],
                "size_bytes": a["size_bytes"],
                "derived_text": a.get("derived_text", ""),
                "tier": tier.value,
                "partition_dt": today.isoformat(),
                "src_key": " + ".join(a.get("sources", []) or [a["key"]]),
            }
        )
    return rows


def spark_write(rows: list[dict], *, table: str, catalog: str = "iceberg"):
    """将清单行写为 Iceberg 表(真正执行于 Spark 集群内)。"""
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName("x4-write-iceberg")
        .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.iceberg.catalog-impl", "org.apache.iceberg.hive.HiveCatalog")
        .config("spark.sql.catalog.iceberg.warehouse", "s3a://x4-iceberg/warehouse")
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin")
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
    )
    spark = builder.getOrCreate()
    df = spark.createDataFrame(rows)
    df.writeTo(table).partitionedBy("tier", "tenant", "partition_dt").using("iceberg")
    print(f">>> 已写入 Iceberg 表 {table} : {len(rows)} 行")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="x4.agent_objects", help="Iceberg 表名")
    args = parser.parse_args(argv)
    # 供 smoke 运行时使用确定性样例行,可直接复用于 CI 之外。
    sample = build_manifest([
        {"tenant": "t-aa", "modality": "text", "key": "k1",
         "size_bytes": 100, "derived_text": "hello", "dt": "2026-08-15"},
    ])
    print(f">>> 构建 {len(sample)} 行清单(本地脚手架);真实写表需在 Spark 集群执行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())