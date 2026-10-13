"""Benchmark: sequential vs parallel vs cached analysis."""

from __future__ import annotations

import time
from pathlib import Path

from sonoglyph import analyze, analyze_batch
from sonoglyph.cache import clear_cache

FIXTURES = Path("tests/fixtures")
TRACKS = sorted(FIXTURES.glob("*.mp3"))


def bench_sequential(paths):
    start = time.perf_counter()
    for p in paths:
        analyze(p, use_cache=False)
    return time.perf_counter() - start


def bench_parallel(paths, workers=None):
    start = time.perf_counter()
    analyze_batch(paths, use_cache=False, max_workers=workers)
    return time.perf_counter() - start


def bench_cached(paths):
    # Warm the cache
    analyze_batch(paths, use_cache=True)
    # Measure
    start = time.perf_counter()
    analyze_batch(paths, use_cache=True)
    return time.perf_counter() - start


if __name__ == "__main__":
    print(f"Tracks: {len(TRACKS)}")
    for p in TRACKS:
        print(f"  - {p.name}")

    clear_cache()

    t_seq = bench_sequential(TRACKS)
    print(f"\nSequential: {t_seq:.2f} s")

    clear_cache()
    t_par = bench_parallel(TRACKS)
    print(f"Parallel:   {t_par:.2f} s  (speedup ×{t_seq / t_par:.2f})")

    t_cache = bench_cached(TRACKS)
    print(f"Cached:     {t_cache:.2f} s  (speedup ×{t_seq / t_cache:.2f})")
