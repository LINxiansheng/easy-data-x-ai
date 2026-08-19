"""X4 实测:Spark local → Iceberg(MinIO S3) 全链路。

跑出真实数字:Parquet/Zstd 体积、Iceberg 元数据、分区剪裁扫描量。
这是把『严格 Spark 方案』落到当前环境(本地引擎 + MinIO)的可复现入口。

用法:
  env -u http_proxy -u https_proxy ... .venv/bin/python code/X4/spark_jobs/real_iceberg_bench.py [N]
"""

import os
import sys
import time

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

JARS = "jars/iceberg-spark-runtime.jar,jars/hadoop-aws.jar,jars/aws-java-sdk-bundle.jar"
# 连接信息从环境变量(.env)读取,默认对齐 docker-compose 本地编排。
ENDPOINT = os.getenv("X4_MINIO_ENDPOINT", "http://127.0.0.1:9000")
ACCESS = os.getenv("X4_MINIO_ACCESS_KEY", "minioadmin")
SECRET = os.getenv("X4_MINIO_SECRET_KEY", "minioadmin")
WAREHOUSE = f"s3a://{os.getenv('X4_ICEBERG_BUCKET', 'x4-iceberg')}/warehouse"
TABLE = "x4.agent_objects"

t_start = time.time()
spark = (
    SparkSession.builder.master("local[2]").appName("x4-iceberg-minio")
    .config("spark.jars", JARS)
    .config("spark.sql.catalog.x4", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.x4.type", "hadoop")
    .config("spark.sql.catalog.x4.warehouse", WAREHOUSE)
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.hadoop.fs.s3a.endpoint", ENDPOINT)
    .config("spark.hadoop.fs.s3a.access.key", ACCESS)
    .config("spark.hadoop.fs.s3a.secret.key", SECRET)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.connection.timeout", "30000")
    .config("spark.hadoop.fs.s3a.attempts.maximum", "2")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")


def gen_df(rows: int):
    return (
        spark.range(1, rows + 1)
        .withColumn("tenant", F.when(F.col("id") % 3 == 0, "t-aa")
                    .when(F.col("id") % 3 == 1, "t-bb").otherwise("t-cc"))
        .withColumn("modality", F.when(F.col("id") % 4 == 0, "text").otherwise("log"))
        .withColumn("tier", F.when(F.col("id") % 5 == 0, "cold")
                    .when(F.col("id") % 2 == 0, "warm").otherwise("hot"))
        .withColumn("dt", F.lit("2026-08-17"))
        .withColumn("size_bytes", (F.col("id") * 10).cast("long"))
        .withColumn("derived_text", F.concat(
            F.col("modality"), F.lit(" desc of id="), F.col("id").cast("string")))
    )


def fmt(b):
    if b is None:
        return "0B"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TiB"


def list_under(fs, path, jpath):
    """聚合目录内文件大小:返回 (metadata_bytes, data_bytes, files)。"""
    meta = data = 0
    nf = 0
    it = fs.listFiles(jpath, True)
    while it.hasNext():
        st = it.next()
        nf += 1
        if "/metadata/" in str(st.getPath()):
            meta += st.getLen()
        else:
            data += st.getLen()
    return meta, data, nf


def main() -> int:
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    df = gen_df(N)
    start = time.time()
    df.writeTo(TABLE).partitionedBy("tier", "tenant", "dt").using("iceberg").createOrReplace()
    print(f"[ice] 写出 {N} 行 / 耗时 {time.time()-start:.1f}s")

    total = spark.table(TABLE).count()
    print(f"[ice] 表行数 total={total}")

    # 对照:同一批行导出为 JSONL 的字节数,与 Iceberg Parquet 体积对比。
    df_collect = spark.table(TABLE).collect()
    jsonl_bytes = sum(
        len(row["derived_text"]) + len(row["tier"]) + len(row["tenant"])
        for row in df_collect
    ) + total * 4  # 近似分隔符与字段开销

    # Iceberg 元数据与 data 文件体积:直接在 MinIO 里按前缀汇总对象字节。
    try:
        from boto3 import client as s3_client
        s3 = s3_client(
            "s3", endpoint_url=ENDPOINT,
            aws_access_key_id=ACCESS, aws_secret_access_key=SECRET,
        )
        meta = data = 0
        nf = 0
        paginator = s3.get_paginator("list_objects_v2")
        bucket = os.getenv("X4_ICEBERG_BUCKET", "x4-iceberg")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                nf += 1
                key = obj["Key"]
                if "/metadata/" in key or key.endswith(".metadata.json"):
                    meta += obj["Size"]
                else:
                    data += obj["Size"]
        print(f"[ice] total={total} jsonl≈{fmt(jsonl_bytes)} "
              f"parquet(data)={fmt(data)} metadata={fmt(meta)} files={nf}")
        print(f"[ice] jsonl/parquet 压缩比={jsonl_bytes / max(data, 1):.1f}x")
    except Exception as exc:  # noqa: BLE001
        print("[ice] (metadata 统计跳过)", exc)

    for tier in ("hot", "warm", "cold"):
        n = spark.sql(f"select * from {TABLE} where tier='{tier}'").count()
        print(f"[ice] tier={tier:4s} 命中行数={n}")

    spark.stop()
    print(f"[ice] done in {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    raise SystemExit(main())