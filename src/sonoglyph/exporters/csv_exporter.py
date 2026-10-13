"""CSV exporter."""

from __future__ import annotations

import csv
from pathlib import Path

from sonoglyph.schemas import AnalysisResult

# Columns in a fixed order — important for stable downstream datasets.
FIELDNAMES = [
    "path",
    "filename",
    "duration_sec",
    "format",
    "sample_rate",
    "bpm",
    "bpm_confidence",
    "beat_count",
    "key_name",
    "key_tonic",
    "key_mode",
    "key_confidence",
    "rms_mean",
    "rms_std",
    "dynamic_range_db",
    "spectral_centroid_mean",
    "spectral_centroid_std",
    "spectral_rolloff_mean",
    "spectral_zcr_mean",
    "mood_valence",
    "mood_arousal",
    "mood_arousal_rhythmic",
    "mood_arousal_harmonic",
    "mood_label",
    "mood_tags",
    "mood_flatness",
    "mood_backend",
]


def _row_from_result(r: AnalysisResult) -> dict[str, object]:
    """Flatten an AnalysisResult into a flat row."""
    row: dict[str, object] = {
        "path": r.metadata.path,
        "filename": Path(r.metadata.path).name,
        "duration_sec": round(r.metadata.duration_sec, 3),
        "format": r.metadata.format,
        "sample_rate": r.metadata.sample_rate,
    }

    if r.tempo:
        row.update(
            bpm=round(r.tempo.bpm, 2),
            bpm_confidence=round(r.tempo.confidence, 3),
            beat_count=r.tempo.beat_count,
        )
    if r.key:
        row.update(
            key_name=r.key.name,
            key_tonic=r.key.tonic,
            key_mode=r.key.mode,
            key_confidence=round(r.key.confidence, 3),
        )
    if r.energy:
        row.update(
            rms_mean=round(r.energy.rms_mean, 5),
            rms_std=round(r.energy.rms_std, 5),
            dynamic_range_db=round(r.energy.dynamic_range_db, 2),
        )
    if r.spectral:
        row.update(
            spectral_centroid_mean=round(r.spectral.centroid_mean, 2),
            spectral_centroid_std=round(r.spectral.centroid_std, 2),
            spectral_rolloff_mean=round(r.spectral.rolloff_mean, 2),
            spectral_zcr_mean=round(r.spectral.zcr_mean, 5),
        )
    if r.mood:
        row.update(
            mood_valence=round(r.mood.valence, 3),
            mood_arousal=round(r.mood.arousal, 3),
            mood_arousal_rhythmic=(
                round(r.mood.arousal_rhythmic, 3)
                if r.mood.arousal_rhythmic is not None
                else ""
            ),
            mood_arousal_harmonic=(
                round(r.mood.arousal_harmonic, 3)
                if r.mood.arousal_harmonic is not None
                else ""
            ),
            mood_label=r.mood.label,
            mood_tags="|".join(r.mood.tags),
            mood_flatness=(
                round(r.mood.spectral_flatness, 5)
                if r.mood.spectral_flatness is not None
                else ""
            ),
            mood_backend=r.mood.backend,
        )

    return row


def to_csv(results: list[AnalysisResult], out: str | Path) -> Path:
    """Save a list of results to a CSV file. Return the file path."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        # utf-8-sig so Excel opens non-ASCII filenames correctly
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in results:
            row = _row_from_result(r)
            # Missing keys → empty strings
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    return out.resolve()
