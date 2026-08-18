"""Embedding 请求封装:缓存 + 批量 + 失败重试(纯 Python,可单测)。

不直接依赖 openai 库;底层调用通过注入的 `client.embeddings.create(...)`
完成,便于离线测试(用假客户端)与真实使用(OpenAI 兼容 text-embedding-v4)切换。
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

EmbedClient = Callable[[Sequence[str], str], list[list[float]]]


def _vector_fingerprint(vecs: list[list[float]]) -> str:
    """对向量做确定性指纹,便于按内容缓存。"""
    payload = json.dumps(
        [round(float(v), 6) for vec in vecs for v in vec],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """按文本内容作键的 Embedding 缓存(内存版,可替换为磁盘/Redis)。"""

    def __init__(self) -> None:
        self._store: dict[str, list[float]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, text: str) -> list[float] | None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def put(self, text: str, vector: list[float]) -> None:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._store[key] = vector

    def cache_hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else 0.0

    def __len__(self) -> int:
        return len(self._store)


@dataclass
class EmbeddingCallStats:
    calls: int = 0
    retries: int = 0
    tokens: int = 0
    failures: int = 0


class EmbeddingClient:
    """带缓存、批量、重试的 Embedding 客户端封装。

    Args:
        client: 实现 ``embeddings.create(model=..., input=[...])`` 返回项,
                每项有 ``embedding`` 字段;通过 OpenAI 兼容接口调用
                ``text-embedding-v4``。None 表示离线/测试模式,直接落缓存。
        model: 模型名,默认 text-embedding-v4。
        batch_size: 每次请求的文本条数。
        max_retries / backoff: 失败重试策略。
    """

    def __init__(
        self,
        client: object | None = None,
        model: str = "text-embedding-v4",
        batch_size: int | None = None,
        max_retries: int = 3,
        backoff: float = 0.5,
    ) -> None:
        self._client = client
        self._model = model
        self._batch = batch_size or 16
        self._max_retries = max_retries
        self._backoff = backoff
        self.cache: EmbeddingCache = EmbeddingCache()
        self.stats: EmbeddingCallStats = EmbeddingCallStats()

    def _call(self, batch: list[str]) -> list[list[float]]:
        if self._client is None:
            # 离线模式:确定性伪向量,便于无外网跑通链路。
            return [
                [0.01 * (i + 1) / len(batch) for i in range(8)]
                for _ in batch
            ]
        response = self._client.embeddings.create(
            model=self._model, input=batch
        )
        rows = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in rows]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """批量安全 Embedding:去重命中缓存 -> 分批 -> 重试。返回与输入同序的向量。"""
        results: list[list[float] | None] = [None] * len(texts)
        to_call: list[int] = []
        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                results[i] = cached
            else:
                to_call.append(i)

        # 按批调用,并对每批做失败重试(指数退避)。
        for start in range(0, len(to_call), self._batch):
            batch = to_call[start : start + self._batch]
            batch_texts = [texts[i] for i in batch]
            self.stats.calls += 1
            self.stats.tokens += sum(len(str(t)) for t in batch_texts)
            attempt = 0
            while True:
                try:
                    vectors = self._call(batch_texts)
                    for idx, vec in zip(batch, vectors):
                        self.cache.put(texts[idx], vec)
                        results[idx] = vec
                    break
                except Exception:
                    self.stats.failures += 1
                    attempt += 1
                    if attempt > self._max_retries:
                        raise
                    self.stats.retries += 1
                    time.sleep(self._backoff * (2 ** (attempt - 1)))
        assert all(v is not None for v in results)
        return [v for v in results if v is not None]  # type: ignore[misc]

    def embed_one(self, text: str) -> list[float]:
        return self.embed_many([text])[0]