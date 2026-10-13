"""On-disk cache for analysis results."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_VERSION = "1"
DEFAULT_CACHE_DIR = Path(
    os.environ.get("SONOGLYPH_CACHE_DIR", Path.home() / ".cache" / "sonoglyph")
)


def file_hash(path: str | Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file, streaming.

    Args:
        path: path to the file.
        chunk_size: read chunk size in bytes (default 64 KB).

    Returns:
        Hex string of the hash.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def features_variant(features: list[str], sr: int) -> str:
    """Short hash of (features, sr) — part of the cache key.

    Ensures that a result computed for ["tempo"] is not returned to a
    request that asked for ["mood", "key"].
    """
    canonical = json.dumps(
        {"features": sorted(features), "sr": sr, "v": CACHE_VERSION},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _cache_path(
    hash_hex: str,
    variant: str = "",
    cache_dir: Path | None = None,
) -> Path:
    base = cache_dir or DEFAULT_CACHE_DIR
    name = f"{hash_hex}-{variant}.json" if variant else f"{hash_hex}.json"
    # Split into subdirectories to avoid thousands of files in one folder
    return base / hash_hex[:2] / name


def get_cached(
    hash_hex: str,
    variant: str = "",
    cache_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Read a cached result if it exists and the version matches."""
    path = _cache_path(hash_hex, variant, cache_dir)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Corrupted cache %s: %s", path, exc)
        return None

    if payload.get("version") != CACHE_VERSION:
        return None
    # Sanity check: variant in payload must match the requested variant
    if payload.get("variant", "") != variant:
        return None
    return payload.get("result")


def set_cached(
    hash_hex: str,
    result: dict[str, Any],
    variant: str = "",
    cache_dir: Path | None = None,
) -> None:
    """Write a result to the cache. Atomic write via .tmp → rename."""
    path = _cache_path(hash_hex, variant, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"version": CACHE_VERSION, "variant": variant, "result": result}
    tmp = path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        tmp.replace(path)  # atomic on POSIX and Windows
    except OSError as exc:
        logger.warning("Failed to write cache %s: %s", path, exc)


def clear_cache(cache_dir: Path | None = None) -> int:
    """Remove all cache files. Return the number deleted."""
    base = cache_dir or DEFAULT_CACHE_DIR
    if not base.exists():
        return 0
    count = 0
    for json_file in base.rglob("*.json"):
        try:
            json_file.unlink()
            count += 1
        except OSError:
            pass
    return count
