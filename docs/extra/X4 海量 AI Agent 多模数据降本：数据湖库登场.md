---
title: X4 海量 AI Agent 多模数据降本：数据湖库登场
---

# X4：海量 AI Agent 多模数据降本 —— 数据湖库登场

## 摘要

| | |
|------|------|
| **解决什么痛点** | 当 AI Agent 产生海量多模数据（文本、日志、图片、音频、视频）时，全量塞进向量库的存储与 Embedding 成本失控 |
| **核心价值** | 用「数据湖库」承接原始对象与历史冷数据，向量库只保留热数据与高价值派生文本，打通「湖 → RAG」并把降本幅度量成可复现的数字 |
| **适用场景** | 多租户 Agent 记忆、多模附件去重、长期记忆冷热分层、湖到 RAG 完整链路 |
| **关联正文** | D2（数据层与混合检索）、D4（记忆存储与冷热分层） |
| **关键限制** | 主链路需 Spark 集群（本仓库提供 docker-compose 编排）；benchmark 档需本地较高算力复现 |

> X4 在 D2 / D4 的基础上，把「单机记忆的冷热分层、多租户隔离」推到海量、多模、多租户的规模上。核心思路就一句话：原始对象和历史冷数据留在数据湖，向量库只装热数据和高价值派生文本。检索效果不受影响，存储和 Embedding 的账单却小了一大截。

**目录**

- [1. 一句话理解](#1-一句话理解) — 60 秒看懂湖到 RAG 的分工
- [2. 背景：为什么不能把全部多模数据放到向量库](#2-背景为什么不能把全部多模数据放到向量库)
- [3. 架构与职责边界](#3-架构与职责边界)
- [4. 降本手段逐项拆解](#4-降本手段逐项拆解)
- [5. 动手实验：从数据生成到 RAG 全链路](#5-动手实验从数据生成到-rag-全链路)
- [6. 可复现实验与指标定义](#6-可复现实验与指标定义)
- [7. 关联与延伸](#7-关联与延伸)
- [8. 总结](#8-总结)

## 1. 一句话理解

湖管全量和冷，向量库管热和检索。去重、冷热分层、按需索引、Embedding 缓存，四件事一起做，才能把 Agent 多模数据的存储成本真正降下来。

先看一个对比。假设 `t1` 租户的 7 条消息重复引用同一份附件：

| 方案 | 存储 | 说明 |
|------|------|------|
| 基线（不去重） | 同一份对象重复存 7 份 | 存储与 Embedding 一起翻倍 |
| 优化（内容寻址去重） | 物理只存 1 份，其余记引用 | 省空间，也省 Embedding |

`code/X4` 把这些做法的收益跑成了实际数字，后面章节会直接引用。

## 2. 背景：为什么不能把全部多模数据放到向量库

一句话文本几百字节，一段视频几 MB，把二者一律 Embedding 后灌进向量库，代价和收益完全不成比例。更麻烦的是，大量 Agent 历史数据几乎没人再查，却长期占着昂贵的热索引；同一份附件还会被多个会话、多个租户反复保存，存储和 Embedding 都白付。

向量库适合当热点检索面，不适合当归档物理存储。D4 的 `d4_7_hot_cold_tier.py` 在单机上讲过这套分层思路，这里把它推到真实湖仓和海量多租户数据的规模上。

## 3. 架构与职责边界

```
         ┌────────────────────────────────────────────┐
 原始对象 │   MinIO  （数据湖存储层）                     │
 文本/日志│    只存物理对象，内容寻址(SHA-256)去重        │
 PNG/WAV/ │                                              │
 MP4      └────────────────────────────────────────────┘
                    │  对象清单 / 派生文本
         ┌────────────────────────────────────────────┐
         │  Apache Iceberg （湖仓表）  —— 写在 Spark    │
         │   事件、对象清单、OCR/ASR 派生文本、租户、     │
         │   冷热状态、生命周期 (Parquet/Zstd 分区)      │
         └────────────────────────────────────────────┘
                    │  按需索引（仅热/高价值）
         ┌────────────────────────────────────────────┐
         │  seekdb （热检索面）                          │
         │   文本分块 + Embedding + 全文 + 过滤字段       │
         └────────────────────────────────────────────┘
```

| 层 | 职责 | 关键词 |
|----|------|--------|
| `MinIO` | 保存文本/图片/音频/视频/日志等**原始对象** | 内容寻址、去重 |
| `Apache Iceberg` | 管理 Agent 事件、**对象清单**、OCR/ASR 派生文本、租户、冷热状态、生命周期 | Parquet / Zstd、分区裁剪 |
| `Spark` | 完成 Iceberg 表写入、分区裁剪、冷热筛选、实验统计 | 严格 Spark 集群 |
| `seekdb` | 仅保存**热数据及高价值**的文本分块、Embedding、全文索引、过滤字段 | 混合检索 + 标量过滤 |
| `Embedding` | OpenAI 兼容 `text-embedding-v4` | 缓存、批量、重试 |

> 一条红线：不要让向量库承载全部多模原始数据和长期冷数据。物理存档交给 MinIO + Iceberg，向量库只做热检索面。

## 4. 降本手段逐项拆解

1. SHA-256 内容寻址去重：同一份附件多个会话只存一次（`core/assets.py`）。
2. JSONL 与 Parquet/Zstd 占用对比：同一份元数据两种序列化，量化压缩收益。
3. 按租户 / 日期 / 模态 / 冷热组织数据：分区键对齐检索与裁剪（`core/tiering.py`）。
4. 冷热分层：原始对象和历史数据留在湖仓，不进热索引。
5. 按需索引：只把热模态和高价值派生文本写入 seekdb。
6. Embedding 降本：结果缓存、批量请求、失败重试（`core/embedding.py`）。

其中冷热分层对应共建任务 [#32（长期记忆的存储成本控制）](https://github.com/datawhalechina/easy-data-x-ai/issues/32)，下面的多租户隔离对应 [#33（多用户记忆隔离）](https://github.com/datawhalechina/easy-data-x-ai/issues/33)。

### 多租户隔离的工程实践

D4 的 `d4_5_multi_user_isolation` 在单机上用内存结构做过用户隔离，到了湖仓规模，隔离要落在三个层面上：

- 湖仓表：`tenant` 是 Iceberg 分区键之一（`tier / tenant / dt`）。查询时带上租户谓词，分区裁剪会直接跳过其他租户的数据文件，误读在物理层面就不会发生（`core/tiering.py` 的 `partition_key` / `filter_expression`）。
- 热索引：seekdb 的每条索引都带 `tenant` 元数据（`build_index.py`），检索时用标量过滤限定租户，和 D4 的做法一致。
- 对象层：这里有个容易踩的坑。内容寻址去重是跨租户的，两个租户上传同一份附件时物理只存一份。省空间没错，但访问控制就不能建在物理对象上，必须建在清单（manifest）的引用记录上：谁能访问哪条引用，由清单表里的 `tenant` 字段决定，而不是由对象存在与否决定（`core/assets.py` 的 `ObjectEntry.source` 记录了每条引用的归属）。如果租户间要求彻底的物理隔离（比如合规场景），去重范围就得退到租户内，用空间换隔离强度。

## 5. 动手实验：从数据生成到 RAG 全链路

配套代码在 `code/X4`（完整命令见 [code/X4/README](../code/X4/README.md)）。

**Step 0 — 纯函数单测（无需任何服务，CI 即此）**
```bash
PYTHONPATH=code python3 -m unittest discover -s code/X4/tests -t code
```

**Step 1 — 启动 Spark 集群（严格编排）**
```bash
docker compose -f code/X4/docker-compose.yml up -d --build
docker compose -f code/X4/docker-compose.yml run --rm init-minio
```

**Step 2 — 生成两档数据（固定种子可复现）**
```bash
python3 -m X4.spark_jobs.gen_data --tier smoke       # ≈100MB
python3 -m X4.spark_jobs.gen_data --tier benchmark  # ≈2GB
```

**Step 3 — 写 Iceberg + 建索引 + 查询**
```bash
docker compose -f code/X4/docker-compose.yml exec spark-submit \
  spark-submit --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.2 \
    --master spark://spark-master:7077 \
    spark_jobs/write_iceberg.py --table x4.agent_objects
```

**Step 4 — benchmark（基线 vs 优化）**
```bash
python3 -m X4.spark_jobs.benchmark --tier smoke
```

## 6. 可复现实验与指标定义

每个指标都说明「测什么 + 怎么测」，并落在 `spark_jobs/benchmark.py` 与 `query.py`；`benchmark` 档真实场景均可复现，`smoke` 档本地纯 Python 就能出数。

| 指标 | 类别 | 怎样测量 |
|------|------|---------|
| 原始对象 / 去重后字节 | 存储 | `core/assets.py` 内容寻址记账 |
| JSONL 与 Parquet/Zstd 占用 | 存储 | 同元数据两种序列化对比 |
| Iceberg 元数据开销 | 存储 | 表仓库 `.metadata` 目录大小 |
| 全量 vs 按需索引条数与目录大小 | 索引 | seekdb 目录字节 + 向量条数 |
| Embedding 请求数 / Token | Embedding | `core/embedding.py` 的 `stats` |
| 热查询 p50 / p95 与 Hit@K | 检索质量 | `spark_jobs/query.py` 只扫热检索面 |
| 冷查询扫描文件/字节、回温时间 | 冷层代价 | `cold_query` 的（首次访问变慢） |

> **实测（本地可复现）**。分两层：对象层去重（MinIO 原始对象）和湖仓压缩（Iceberg 表）。
>
> （a）纯函数 smoke（`code/X4/spark_jobs/benchmark.py`），验证链路逻辑和去重记账：
>
> ```
> === X4 benchmark(smoke) ===
>   原始对象字节(raw): 3000
>   去重后字节: 420
>   JSONL 元数据字节: 4295
>   Parquet 字节: 0
>   Parquet+Zstd 字节: 0
>   Iceberg 元数据开销: 0
>   seekdb 索引目录字节: 672
>   Embedding 请求次数: 21
>   Embedding Token 用量: 137
>   -> 去重比 0.86, 索引条目 21
> ```
>
> （b）真实湖仓链路（`real_iceberg_bench.py`，Spark local → Iceberg，底层 MinIO）。
>
> **对象层去重**（`gen_data` 用 3 租户加固定共享池，模拟同一附件跨会话复用；smoke 档原始总量 ≈99.5 MiB）：
>
> | 度量 | 数值 |
> |------|------|
> | 唯一对象数 | 1979 |
> | 原始总字节 | 104,348,219 B（≈99.5 MiB） |
> | 去重省下字节 | 2,543,139 B（≈2.4 MiB） |
> | 去重比 | 0.024（616 次重复引用） |
>
> **benchmark 档**（同一命令 `--tier benchmark`，实测原始总量 ≈1966 MiB ≈ 2GB）：唯一对象 36,072 个，去重省下 50,778,500 B（≈48.4 MiB），去重比 0.025。
>
> **湖仓压缩**（50 万行分区表，分区键 `tier / tenant / dt`）：
>
> | 度量 | 数值 |
> |------|------|
> | Iceberg data（Parquet）体积 | 1.6 MiB |
> | Iceberg `.metadata` 开销 | 15 KiB |
> | 文件数 | 13 |
> | 等量 JSONL 体积 | ≈15.6 MiB |
> | JSONL → Parquet 压缩比 | ≈9.6× |
> | 分区剪裁 `tier='hot'` | 命中 200000 |
> | 分区剪裁 `tier='warm'` | 命中 200000 |
> | 分区剪裁 `tier='cold'` | 命中 100000 |
>
> 复现命令（禁代理直连本地 MinIO）：
> ```bash
> env -u http_proxy -u https_proxy PYTHONPATH=code .venv/bin/python \
>   code/X4/spark_jobs/real_iceberg_bench.py 500000
> ```
> 该脚本用 Spark 本地引擎 + MinIO（S3）完成 Iceberg 写表、元数据统计与分区裁剪，输出上表。benchmark 档（约 2GB）在同一命令换更大 N 即可扩展。

## 7. 关联与延伸

D4 的 `d4_7_hot_cold_tier` 在单机上演示过冷热分层，`d4_5_multi_user_isolation` 演示过多用户隔离，本章把两者搬到了真实的 MinIO + Iceberg 湖仓上：冷热变成分区键，租户隔离变成 `tenant` 分区加清单层访问控制。D2 讲过的混合检索和 Embedding，在这里接上了湖仓这个上游，凑成完整的「湖 → RAG」链路。对应的共建任务是 [#32](https://github.com/datawhalechina/easy-data-x-ai/issues/32)（存储成本控制）和 [#33](https://github.com/datawhalechina/easy-data-x-ai/issues/33)（多用户记忆隔离）。

## 8. 总结

回到开头那句话：湖管全量和冷，向量库管热和检索。去重、冷热分层、按需索引、Embedding 缓存这四件事都不复杂，难的是把它们串成一条可验证的链路。本章的全部数字都能用固定种子和两档数据在你自己机器上重跑出来；如果跑出了不一样的结果，欢迎到 Issue 里聊。

> 本节为 Datawhale《Easy Data x AI》扩展篇 X4，认领 Issue `#39` / 任务 `#96`。欢迎在 Issue 下交流与共建。