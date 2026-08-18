# X4 · 海量 AI Agent 多模数据降本：数据湖库登场

对应计划：`docs/extra/X4 海量 AI Agent 多模数据降本：数据湖库登场.md`（本处为配套可运行代码）。

演示「数据湖 → RAG」降本链路：SHA-256 去重、Iceberg 冷热分层、按需索引、Embedding 缓存/批量/重试，以及两份 benchmark 对比。

## 分层原则

| 层 | 技术 | 是否需集群 |
| --- | --- | --- |
| `core/` | 纯 Python 标准库(去重/分层/Embedding/指标) | 否，可单测、可进 CI |
| `spark_jobs/` | Spark + Iceberg + MinIO 主链路 | 是(spark-submit) |
| `tests/` | 纯 Python 单测 | 否，进 CI，不连集群 |

这样划分后，单元测试和 GitHub Actions CI 全程纯 Python，不需要启动 Spark 集群；大数据链路由 `docker-compose` 按需拉起。

## 目录结构

```
code/X4/
├── docker-compose.yml     # spark-master + spark-worker + minio 集群编排
├── .env.example           # MinIO / Embedding / seekdb 配置模板
├── requirements.txt       # 依赖说明(核心层零第三方;本地基准需 pyspark/pyiceberg/boto3 ...)
├── core/
│   ├── assets.py          # SHA-256 内容寻址去重 + 对象清单
│   ├── embedding.py       # Embedding 缓存/批量/失败重试(OpenAI 兼容 text-embedding-v4)
│   ├── tiering.py         # 冷热分层规则 + 分区键/过滤谓词推导
│   └── metrics.py         # p50/p95、Hit@K、成本汇总与降本收益
├── spark_jobs/
│   ├── gen_data.py        # 固定种子生成 smoke(≈100MB)/benchmark(≈2GB) 多模数据 → MinIO
│   ├── write_iceberg.py   # Iceberg 建表/写/分区(Spark,含 S3A↔MinIO 配置)
│   ├── build_index.py     # 按需索引:热数据/派生文本 → Embedding → seekdb
│   ├── query.py           # 热查询(延迟/Hit@K) 与 冷查询(扫描文件/字节/回温)
│   └── benchmark.py       # 基线 vs 优化对比,输出章节可引用的数字表
└── tests/                 # 纯 Python 单测(不连集群),test*.py
```

## 快速开始

### 0. 前提
- Python 3.11+（仓库 CI 固定 3.11;本地建议用 `.venv`）。
- Docker + Docker Compose（跑 Spark 集群 / MinIO 用）。
- API Key（Embedding 需 `text-embedding-v4`）:复制并填写 `.env`。

### 1. 纯函数单测（无需任何服务，CI 即此）

macOS/Linux：
```bash
PYTHONPATH=code python3 -m unittest discover -s code/X4/tests -t code
```
Windows PowerShell：
```powershell
$env:PYTHONPATH="code"
python -m unittest discover -s code/X4/tests -t code
```

### 2. 启动 Spark 集群与 MinIO

```bash
docker compose -f code/X4/docker-compose.yml up -d --build
# 等待 MinIO 与 Spark 就绪后,初始化桶
docker compose -f code/X4/docker-compose.yml run --rm init-minio
```
Windows PowerShell 同样命令即可。

### 3. 生成数据（两档可复现）

macOS/Linux（本地进程直接跑,需 `pip install boto3`）：

```bash
python3 -m X4.spark_jobs.gen_data --tier smoke      # ≈100MB,快速验证
python3 -m X4.spark_jobs.gen_data --tier benchmark  # ≈2GB,章节正式数据
```
Windows PowerShell：
```powershell
python -m X4.spark_jobs.gen_data --tier smoke
```

### 4. 写 Iceberg + 建索引 + 查询（主链路）

在 spark-submit 容器内执行：

```bash
docker compose -f code/X4/docker-compose.yml exec spark-submit \
  spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2 \
    --master spark://spark-master:7077 \
    spark_jobs/write_iceberg.py --table x4.agent_objects
```

### 5. benchmark（基线 vs 优化）

```bash
python3 -m X4.spark_jobs.benchmark --tier smoke
```

### 6. 本地 Spark 引擎实测（不拉集群的替代路径）

`spark_jobs/real_iceberg_bench.py` 用 Spark local + Iceberg + MinIO 跑出真实数字。
需先在仓库根目录准备 `jars/`（已 gitignore，不入库）：

```bash
mkdir -p jars
curl -L -o jars/iceberg-spark-runtime.jar https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.5.2/iceberg-spark-runtime-3.5_2.12-1.5.2.jar
curl -L -o jars/hadoop-aws.jar https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
curl -L -o jars/aws-java-sdk-bundle.jar https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar
```

运行（若有代理需禁用以直连本地 MinIO）：

```bash
env -u http_proxy -u https_proxy PYTHONPATH=code python3 \
  code/X4/spark_jobs/real_iceberg_bench.py 500000
```

## 测试

```bash
PYTHONPATH=code python3 -m unittest discover -s code/X4/tests -t code
PYTHONPATH=code python3 -m compileall -q code/X4
```

仓库级：`code/run_tests.py` 已注册 X4 测试组（纯 Python,不连集群）。

## 复现说明

- 数据生成用固定随机种子（`SEED=42`），两档都可复现；
- smoke 档供 PR 自检和快速验证；benchmark 档需要较多本地资源（建议内存 ≥8G、磁盘 ≥50G），不进 CI；
- API Key 只从本地 `.env` 读取，仓库仅提交无真实值的 `.env.example`。