"""程序化生成无版权的模拟多模 Agent 数据,写回 MinIO(原始对象桶)。

生成内容(固定随机种子保证可复现):
  - text / log  : 确定性文本与日志行
  - image       : 无版权 PNG(纯色/噪声画布)
  - audio       : 无版权 WAV(合成正弦波)
  - video       : 无版权 MP4(极小的合成容器占位帧)
同时为每类派生 OCR / ASR 文本(模拟),供后续索引。

运行: python spark_jobs/gen_data.py --tier smoke
  或 docker compose exec spark-submit python spark_jobs/gen_data.py --tier smoke
依赖本地需 `pip install boto3`;Spark 镜像内由 README 指引安装。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import random
import struct
import sys
import wave
from pathlib import Path

SPARK_JOBS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPARK_JOBS_DIR.parent))  # 允许 import core

from core.assets import DedupStore, content_hash, savings_report  # noqa: E402

TIER_SIZES = {
    "smoke": {"text": 400, "log": 400, "image": 40, "audio": 20, "video": 5},
    "benchmark": {"text": 8000, "log": 8000, "image": 600, "audio": 300, "video": 40},
}
# 媒体对象体积配置:使两档总量分别达到 ≈100MB / ≈2GB(3 租户合计,去重前)。
TIER_MEDIA = {
    "smoke": {"image_px": 160, "audio_seconds": 30.0,
              "video_bytes": 4 * 1024 * 1024},
    "benchmark": {"image_px": 160, "audio_seconds": 60.0,
                  "video_bytes": 8 * 1024 * 1024},
}
MODALITY_EXT = {"text": "txt", "log": "log", "image": "png",
                "audio": "wav", "video": "mp4"}
# 固定复用池:部分对象取自该池,模拟「同一附件被多个会话/租户重复引用」。
SHARED_POOL_SIZE = 64
SHARED_RATIO = 0.3
SEED = 42


def make_text(rng: random.Random, tenant: str, i: int) -> bytes:
    base = f"tenant={tenant} 样本 #{i} " + "模拟Agent对话内容 " * 8
    return (base + rng.choice(["天气好", "待办事项", "代码片段", "会议纪要"])).encode()


def make_log(rng: random.Random, tenant: str, i: int) -> bytes:
    level = rng.choice(["INFO", "WARN", "ERROR"])
    return f"{level} t={tenant} log#{i} msg='{rng.randint(0,999)}'".encode()


def make_png_bytes(rng: random.Random, px: int = 8) -> bytes:
    """无依赖生成合法 PNG(px×px RGBA 噪点;zlib IDAT + 真实 CRC)。"""
    import zlib

    w = h = px
    raw = rng.randbytes(w * h * 4)
    rows = b"".join(b"\x00" + raw[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8bit, RGBA 彩色
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(rows, level=1))
        + chunk(b"IEND", b"")
    )


def make_wav_bytes(rng: random.Random, seconds: float = 1.0) -> bytes:
    """合成噪声 WAV(8kHz 16bit 单声道),randbytes 直接作 PCM 体,快且可复现。"""
    rate = 8000
    frames = int(rate * seconds)
    body = rng.randbytes(frames * 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(body)
    return buf.getvalue()


def make_video_bytes(rng: random.Random, size_bytes: int = 256) -> bytes:
    """占位 MP4 字节(极小合成容器 + 可配置噪声载荷),体积确定性可复现。"""
    return b"ftypisom" + rng.randbytes(size_bytes)


def _make_modality(
    rng: random.Random,
    modality: str,
    ctx: str,
    i: int = 0,
    media: dict | None = None,
) -> bytes:
    """生成单个模态对象。

    ``ctx`` 作为“租户”名参与文本内容:独立对象传租户(唯一),共享池传
    ``"pool"``(跨租户相同 → 内容寻址去重可命中)。``media`` 控制媒体体积。
    """
    m = media or TIER_MEDIA["smoke"]
    if modality == "text":
        return make_text(rng, ctx, i)
    if modality == "log":
        return make_log(rng, ctx, i)
    if modality == "image":
        return make_png_bytes(rng, px=m["image_px"])
    if modality == "audio":
        return make_wav_bytes(rng, seconds=m["audio_seconds"])
    if modality == "video":
        return make_video_bytes(rng, size_bytes=m["video_bytes"])
    return b""


def derived_text_for(modality: str, i: int, rng: random.Random) -> str:
    """生成 OCR/ASR 派生文本描述,用于后续索引。"""
    return f"modality={modality} derived-{i} desc={rng.randint(0, 9999)}"


def generate(bucket: str, tier: str):
    """按档位生成数据,通过内容寻址去重后写入对象桶。"""
    import boto3

    if tier not in TIER_SIZES:
        raise SystemExit(f"未知档位: {tier}")
    sizes = TIER_SIZES[tier]
    media = TIER_MEDIA[tier]
    store = DedupStore()
    rng = random.Random(SEED)

    # 连接信息从环境变量(.env)读取,默认对齐 docker-compose 本地编排。
    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("X4_MINIO_ENDPOINT", "http://127.0.0.1:9000"),
        aws_access_key_id=os.getenv("X4_MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("X4_MINIO_SECRET_KEY", "minioadmin"),
    )

    def put(key: str, data: bytes, tenant: str, modality: str, src: str) -> bool:
        sha = content_hash(data)
        is_new = store.add(
            sha, tenant=tenant, modality=modality,
            size_bytes=len(data), source=src,
        )
        if is_new:
            s3.put_object(Bucket=bucket, Key=key, Body=data)
        return is_new

    # 预生成「共享池」:同一组内容跨租户复用,模拟同一附件被多次引用。
    shared_pool: dict[str, list[bytes]] = {}
    for mod in ("text", "log", "image"):
        shared_pool[mod] = [
            _make_modality(rng, mod, "shared_pool", i, media)
            for i in range(SHARED_POOL_SIZE)
        ]

    for modality, n in sizes.items():
        # 每租户的每个模态里,前 SHARED_RATIO 份从共享池取;其余独立生成。
        shared_use = int(n * SHARED_RATIO)
        for tenant in ("t-aa", "t-bb", "t-cc"):
            for i in range(n):
                if i < shared_use and modality in shared_pool:
                    data = shared_pool[modality][i % SHARED_POOL_SIZE]
                else:
                    data = _make_modality(rng, modality, tenant, i, media)
                src = f"obj/{tenant}/{modality}/{i}.{MODALITY_EXT[modality]}"
                put(src, data, tenant, modality, src)

    report = savings_report(store)
    total_raw = report["unique_bytes"] + report["dedup_saved_bytes"]
    print(f"[{tier}] 生成完成:")
    print(f"  tenant 组: t-aa/t-bb/t-cc  唯一对象数: {len(store.unique_entries)}")
    print(f"  原始总字节: {total_raw} (≈{total_raw / (1 << 20):.1f} MiB)")
    print(f"  唯一字节: {report['unique_bytes']}  "
          f"重复省下: {report['dedup_saved_bytes']}")
    print(f"  去重比: {report['dedup_ratio']}")
    return store


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=sorted(TIER_SIZES), default="smoke")
    parser.add_argument("--bucket",
                        default=os.getenv("X4_OBJECTS_BUCKET", "x4-objects"))
    args = parser.parse_args(argv)
    generate(args.bucket, args.tier)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())