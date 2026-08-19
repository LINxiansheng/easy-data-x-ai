"""按需索引:仅将热数据和高价值派生文本写入 seekdb(纯 Python 逻辑 + 可选写库入口)。

对应计划:seekdb 仅保存热数据及高价值数据的文本分块、Embedding、全文索引和过滤字段;
「按需索引」由 core.tiering.asset_to_indexed_text 决策。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

CORE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE))

from X4.core.embedding import EmbeddingClient  # noqa: E402
from X4.core.tiering import asset_to_indexed_text  # noqa: E402

IndexSink = Callable[[str, list[float], dict], None]


def should_index(
    modality: str, size_bytes: int, derived_text: str
) -> bool:
    """按需求索引规则判断某对象是否应进入在线索引。"""
    return asset_to_indexed_text(modality, size_bytes, derived_text)


def build_index_rows(
    rows: list[dict],
    embedder: EmbeddingClient,
    *,
    index_filter=asset_to_indexed_text,
) -> list[dict]:
    """对对象清单行运行索引:过滤 -> 生成 Embedding -> 拼索引条目。

    返回: [{id, vector, text, metadata}] —— 仅含被判定为「入索引」的条目。
    """
    out: list[dict] = []
    for row in rows:
        text = row.get("derived_text") or row.get("text") or ""
        if not index_filter(
            row.get("modality", "text"),
            row.get("size_bytes", 0),
            text,
        ):
            continue
        vector = embedder.embed_one(text)
        out.append(
            {
                "id": row["key"] or row.get("id"),
                "text": text,
                "vector": vector,
                "metadata": {
                    "tenant": row.get("tenant"),
                    "modality": row.get("modality"),
                    "tier": row.get("tier"),
                },
            }
        )
    return out


def write_to_seekdb(entries: list[dict], *, has_collection, create_collection) -> int:
    """把索引条目写入 seekdb collection(需在 runtime 构造 db 后调用)。

    Args:
        entries: build_index_rows 的输出。
        has_collection / get_collection: seekdb 客户端实例方法,便于离线注入。
    """
    raise NotImplementedError(
        "X4 提供 build_index_rows(纯函数)供 CI 与 benchmark 复用;"
        "实际的 seekdb 写入由运行时调用方基于 create_seekdb_client 完成,"
        "避免让测试依赖真实数据库。"
    )


def main(argv=None) -> int:
    """示意入口;真实写库在 README 的 smoke 流程中执行。"""
    embedder = EmbeddingClient()
    rows = build_index_rows(
        [
            {"key": "k1", "tenant": "t-aa", "modality": "text",
             "size_bytes": 10, "derived_text": "hello world",
             "tier": "hot"},
            {"key": "k2", "tenant": "t-aa", "modality": "video",
             "size_bytes": 5 * 1024 * 1024, "derived_text": "desc",
             "tier": "cold"},
        ],
        embedder,
    )
    print(f">>> 按需索引: {len(rows)} 条入索引(冷/超大默认跳过)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())