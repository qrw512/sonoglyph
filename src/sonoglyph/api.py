"""Public Sonoglyph API."""

from __future__ import annotations

import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from sonoglyph.analyzers import REGISTRY
from sonoglyph.cache import features_variant, file_hash, get_cached, set_cached
from sonoglyph.io import load_audio
from sonoglyph.schemas import (
    AnalysisResult,
    AudioMetadata,
    EnergyFeatures,
    KeyFeatures,
    MoodFeatures,
    SpectralFeatures,
    TempoFeatures,
)

logger = logging.getLogger(__name__)

DEFAULT_FEATURES = ["tempo", "key", "spectral", "energy", "mood"]


def analyze(
    path: str | Path,
    features: list[str] | None = None,
    sr: int = 22050,
    use_cache: bool = True,
) -> AnalysisResult:
    """Analyze an audio file and return all requested features.

    Args:
        path: path to the audio file.
        features: list of analyzer names; None means all defaults.
        sr: target sample rate.
        use_cache: use the on-disk cache.

    Returns:
        AnalysisResult with all requested fields filled in.
    """
    features = features or DEFAULT_FEATURES
    unknown = set(features) - set(REGISTRY)
    if unknown:
        raise ValueError(f"Unknown analyzers: {unknown}")

    path = Path(path)

    # --- Cache lookup ---
    variant = features_variant(features, sr)
    hash_hex: str | None = None
    if use_cache:
        try:
            hash_hex = file_hash(path)
            cached = get_cached(hash_hex, variant=variant)
            if cached is not None:
                logger.debug("Cache hit: %s [%s]", path.name, variant)
                return AnalysisResult.model_validate(cached)
        except OSError as exc:
            logger.warning("Failed to hash %s: %s", path, exc)

    # --- Analysis ---
    audio, sample_rate = load_audio(path, sr=sr)

    metadata = AudioMetadata(
        path=str(path.resolve()),
        duration_sec=float(len(audio) / sample_rate),
        sample_rate=sample_rate,
        channels=1,  # load_audio always returns mono
        format=path.suffix.lstrip(".").lower(),
    )

    result = AnalysisResult(metadata=metadata)
    raw: dict[str, dict] = {}

    for name in features:
        analyzer_cls = REGISTRY[name]
        try:
            raw[name] = analyzer_cls().analyze(audio, sample_rate)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analyzer %s failed: %s", name, exc)
            continue

    if "tempo" in raw:
        result.tempo = TempoFeatures(**raw["tempo"])
    if "key" in raw:
        result.key = KeyFeatures(**raw["key"])
    if "spectral" in raw:
        result.spectral = SpectralFeatures(**raw["spectral"])
    if "energy" in raw:
        result.energy = EnergyFeatures(**raw["energy"])
    if "mood" in raw:
        result.mood = MoodFeatures(**raw["mood"])

    # --- Cache write ---
    if use_cache and hash_hex is not None:
        set_cached(hash_hex, result.model_dump(mode="json"), variant=variant)

    return result


def _worker(args: tuple[str, list[str] | None, int, bool]) -> tuple[str, dict | None, str | None]:
    """Worker for ProcessPoolExecutor. Module-level so it can be pickled.

    Returns:
        (path, result_dict | None, error_str | None)
    """
    path_str, features, sr, use_cache = args
    try:
        result = analyze(path_str, features=features, sr=sr, use_cache=use_cache)
        return path_str, result.model_dump(mode="json"), None
    except Exception as exc:  # noqa: BLE001
        return path_str, None, str(exc)


def analyze_batch(
    paths: list[str | Path],
    features: list[str] | None = None,
    sr: int = 22050,
    use_cache: bool = True,
    max_workers: int | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[AnalysisResult]:
    """Analyze a set of files in parallel using ProcessPoolExecutor.

    Args:
        paths: list of file paths.
        features: list of analyzers (None = defaults).
        sr: sample rate.
        use_cache: use the on-disk cache.
        max_workers: number of processes; None = os.cpu_count() - 1.
        progress_callback: callable (n_done, n_total) for progress bars.

    Returns:
        List of AnalysisResult. Order differs from input — use
        metadata.path to map back to the original file.
    """
    if not paths:
        return []

    if max_workers is None:
        max_workers = max(1, (os.cpu_count() or 2) - 1)

    path_strs = [str(p) for p in paths]
    args_list = [(p, features, sr, use_cache) for p in path_strs]

    results: list[AnalysisResult] = []
    total = len(args_list)
    done = 0

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_worker, args): args[0] for args in args_list}
        for future in as_completed(futures):
            path_str, result_dict, error = future.result()
            done += 1

            if progress_callback:
                progress_callback(done, total)

            if error is not None:
                logger.warning("Failed to analyze %s: %s", path_str, error)
                continue

            assert result_dict is not None
            results.append(AnalysisResult.model_validate(result_dict))

    return results
