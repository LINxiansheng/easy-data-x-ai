"""内容寻址去重与对象清单(纯 Python,可单测)。

对应计划中「SHA-256 内容寻址去重,避免同一附件被多个会话重复保存」。
核心思路:对每个原始对象的字节算 SHA-256,以摘要作为存储键(内容寻址),
相同内容只存一份,清单(manifest)记录逻辑引用 -> 物理对象。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable


def content_hash(data: bytes, algorithm: str = "sha256") -> str:
    """计算数据的摘要,默认 SHA-256。

    >>> content_hash(b"hi").startswith("ba7d")
    True
    """
    return getattr(hashlib, algorithm)(data).hexdigest()


def hash_file(path: str, algorithm: str = "sha256") -> str:
    """流式计算文件摘要,避免一次性载入大文件。"""
    digest = getattr(hashlib, algorithm)()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class ObjectEntry:
    """清单中的一条原始对象记录。"""

    key: str            # 内容寻址键(即 SHA-256)
    tenant: str
    modality: str       # text / log / image / audio / video
    size_bytes: int
    is_duplicate: bool = False
    source: list[str] = field(default_factory=list)  # 引用它的会话/路径


class DedupStore:
    """以内容寻址记录对象去重与占用的记账表。"""

    def __init__(self) -> None:
        self._by_key: dict[str, ObjectEntry] = {}
        self._dup_count = 0

    def add(self, key: str, *, tenant: str, modality: str,
            size_bytes: int, source: str) -> bool:
        """录入一个对象。返回 False 表示该内容此前已存在(重复,只记引用)。"""
        existing = self._by_key.get(key)
        if existing is not None:
            self._dup_count += 1
            existing.source.append(source)
            return False
        self._by_key[key] = ObjectEntry(
            key=key, tenant=tenant, modality=modality,
            size_bytes=size_bytes, source=[source],
        )
        return True

    @property
    def unique_entries(self) -> list[ObjectEntry]:
        return list(self._by_key.values())

    @property
    def duplicate_misses(self) -> int:
        return self._dup_count

    def unique_bytes(self) -> int:
        return sum(e.size_bytes for e in self._by_key.values())

    def repeated_bytes(self) -> int:
        """若不去重,重复内容会再次占用的字节 = (引用数-1)*大小。"""
        return sum(
            (len(e.source) - 1) * e.size_bytes for e in self._by_key.values()
        )

    def manifest(self) -> list[dict]:
        """导出可落 JSONL 的清单(对象清单表)。"""
        return [
            {
                "key": e.key,
                "tenant": e.tenant,
                "modality": e.modality,
                "size_bytes": e.size_bytes,
                "refs": len(e.source),
                "sources": e.source,
            }
            for e in self._by_key.values()
        ]

    def dump_manifest(self, path: str) -> None:
        """以 JSONL 写出完整清单(幂等,仅用于可比对清单大小)。"""
        with open(path, "w", encoding="utf-8") as fh:
            for row in self.manifest():
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def savings_report(store: DedupStore) -> dict:
    """统计去重带来的字节收益(供 benchmark 数字表引用)。"""
    unique = store.unique_bytes()
    wasted = store.repeated_bytes()
    if unique + wasted == 0:
        ratio = 0.0
    else:
        ratio = wasted / (unique + wasted)
    return {
        "unique_bytes": unique,
        "dedup_saved_bytes": wasted,
        "dedup_ratio": round(ratio, 4),
        "dup_objects": store.duplicate_misses,
    }


def ingest_bytes(store: DedupStore, data: bytes, *, tenant: str,
                 modality: str, source: str) -> tuple[str, bool]:
    """入库一条原始对象。返回 (key, 是否为新对象)。"""
    key = content_hash(data)
    return key, store.add(
        key, tenant=tenant, modality=modality,
        size_bytes=len(data), source=source,
    )