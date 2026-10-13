"""Mood analysis: valence/arousal + perceptual attributes.

Two backends are supported:
- `heuristic` — no ML dependencies, works out of the box.
- `vibenet`   — optional ML model (pip install vibenet).
Select via env var SONOGLYPH_MOOD_BACKEND = auto | heuristic | vibenet.

Split arousal (rhythmic / harmonic) is diagnostic only. It does NOT
participate in classification: HPSS separation is imperfect for 808 bass,
which is tonal by nature but acts as a percussive element.
"""

from __future__ import annotations

import logging
import os
import warnings
from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer

logger = logging.getLogger(__name__)

_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)

FLATNESS_ATMOSPHERIC = 0.035
FLATNESS_NOISY = 0.08

_P75_DISCOUNT = 0.9
_P90_DISCOUNT = 0.6

# Threshold for split-arousal tags. If rhythm outruns harmonic by 0.15+,
# the track is "driving beat"; if harmonic outruns rhythm — "lush harmony".
SPLIT_TAG_GAP = 0.15


def _effective_flatness(flatness_frames: np.ndarray) -> tuple[float, float, float]:
    """Return (mean, p90, effective).

    effective = max(mean, p75·0.9, p90·0.6) — captures both the overall
    level and the noisy background present in the upper frame percentiles.
    """
    mean = float(flatness_frames.mean())
    p75 = float(np.percentile(flatness_frames, 75))
    p90 = float(np.percentile(flatness_frames, 90))
    eff = max(mean, p75 * _P75_DISCOUNT, p90 * _P90_DISCOUNT)
    return mean, p90, eff


def _split_arousal(
    audio: np.ndarray, sr: int, bpm: float
) -> tuple[float, float]:
    """Compute arousal_rhythmic and arousal_harmonic via HPSS.

    CAVEAT: HPSS often classifies 808 bass as harmonic (low frequencies, but
    a tonal waveform), so the values are diagnostic, not evaluative.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="n_fft=.*is too large", category=UserWarning
        )
        try:
            y_harm, y_perc = librosa.effects.hpss(audio)
        except Exception:  # noqa: BLE001
            y_harm = y_perc = audio

        rms_perc = float(librosa.feature.rms(y=y_perc).mean())
        onsets = librosa.onset.onset_detect(y=audio, sr=sr, units="time")
        centroid_h = float(librosa.feature.spectral_centroid(y=y_harm, sr=sr).mean())
        rms_harm = float(librosa.feature.rms(y=y_harm).mean())
        chroma_h = librosa.feature.chroma_cqt(y=y_harm, sr=sr)

    tempo_norm = float(np.clip((bpm - 60) / 120, 0.0, 1.0))
    rms_perc_norm = float(np.clip(rms_perc / 0.15, 0.0, 1.0))

    duration = max(len(audio) / sr, 1e-3)
    onset_rate = len(onsets) / duration
    onset_norm = float(np.clip(onset_rate / 6.0, 0.0, 1.0))

    arousal_rhythm = float(
        np.clip(
            0.45 * tempo_norm + 0.35 * rms_perc_norm + 0.20 * onset_norm,
            0.0,
            1.0,
        )
    )

    centroid_norm = float(np.clip(centroid_h / 5000, 0.0, 1.0))
    rms_harm_norm = float(np.clip(rms_harm / 0.15, 0.0, 1.0))
    chroma_motion = float(np.mean(np.std(chroma_h, axis=1)))
    motion_norm = float(np.clip(chroma_motion / 0.25, 0.0, 1.0))

    arousal_harm = float(
        np.clip(
            0.40 * centroid_norm + 0.30 * rms_harm_norm + 0.30 * motion_norm,
            0.0,
            1.0,
        )
    )

    return arousal_rhythm, arousal_harm


def _classify_mood(
    valence: float, arousal: float, flatness_eff: float
) -> tuple[str, list[str]]:
    """Extended mood map that accounts for texture.

    Split arousal is NOT used here — diagnostic only.
    """
    tags: list[str] = []

    is_atmospheric = flatness_eff >= FLATNESS_ATMOSPHERIC
    is_noisy = flatness_eff >= FLATNESS_NOISY
    if is_atmospheric:
        tags.append("atmospheric")
    if is_noisy:
        tags.append("noisy")

    # Dead zone
    if 0.42 <= valence <= 0.58 and 0.42 <= arousal <= 0.58:
        return "neutral", tags

    # Q1: negative + energetic
    if valence < 0.5 and arousal >= 0.5:
        if is_atmospheric:
            tags.append("dark")
            return "melancholic", tags
        tags.append("aggressive")
        return "angry", tags

    # Q2: negative + calm
    if valence < 0.5 and arousal < 0.5:
        if is_atmospheric:
            tags.append("dark")
        return "sad", tags

    # Q3: positive + calm
    if valence >= 0.5 and arousal < 0.5:
        if is_atmospheric:
            tags.append("dreamy")
        return "calm", tags

    # Q4: positive + energetic
    if is_atmospheric:
        tags.append("dreamy")
    else:
        tags.append("upbeat")
    return "happy", tags


def _split_tags(arousal_rhythm: float, arousal_harm: float) -> list[str]:
    """Extra tags derived from split arousal — diagnostics only."""
    gap = arousal_rhythm - arousal_harm
    if gap >= SPLIT_TAG_GAP:
        return ["driving-beat"]
    if -gap >= SPLIT_TAG_GAP:
        return ["lush-harmony"]
    return []


class MoodAnalyzer(BaseAnalyzer):
    """Track mood. Backend selected via SONOGLYPH_MOOD_BACKEND."""

    name = "mood"

    def __init__(self, backend: str | None = None) -> None:
        self.backend = (
            backend or os.environ.get("SONOGLYPH_MOOD_BACKEND", "auto")
        ).lower()

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        if self.backend == "heuristic":
            return self._heuristic(audio, sr)
        if self.backend == "vibenet":
            return self._vibenet(audio, sr)
        if self.backend == "auto":
            try:
                return self._vibenet(audio, sr)
            except Exception as exc:  # noqa: BLE001
                logger.info("VibeNet unavailable (%s), falling back to heuristic", exc)
                return self._heuristic(audio, sr)
        raise ValueError(f"Unknown mood backend: {self.backend}")

    # ---------- Heuristic ----------

    def _heuristic(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
            rms = float(librosa.feature.rms(y=audio).mean())
            centroid = float(librosa.feature.spectral_centroid(y=audio, sr=sr).mean())
            flatness_frames = librosa.feature.spectral_flatness(y=audio)[0]
            chroma = librosa.feature.chroma_cqt(y=audio, sr=sr).mean(axis=1)

        _flatness_mean, _flatness_p90, flatness_eff = _effective_flatness(flatness_frames)
        bpm = float(np.atleast_1d(tempo)[0])
        is_minor = _is_minor(chroma)

        # --- Arousal: original formula, validated on real tracks ---
        rms_norm = float(np.clip(rms / 0.25, 0.0, 1.0))
        tempo_norm = float(np.clip((bpm - 60) / 120, 0.0, 1.0))
        centroid_norm = float(np.clip(centroid / 5000, 0.0, 1.0))
        arousal = float(
            np.clip(
                0.55 * rms_norm + 0.30 * tempo_norm + 0.15 * centroid_norm,
                0.0,
                1.0,
            )
        )

        # --- Valence ---
        mode_component = -0.26 if is_minor else 0.26
        brightness = float(np.clip((centroid - 1500) / 3000, -0.5, 0.5))
        tempo_val = float(np.clip((bpm - 100) / 100, -0.3, 0.3))
        texture_bias = -0.05 if flatness_eff >= FLATNESS_ATMOSPHERIC else 0.0
        valence = float(
            np.clip(
                0.5 + mode_component + 0.15 * brightness + tempo_val + texture_bias,
                0.0,
                1.0,
            )
        )

        # Main classification
        label, tags = _classify_mood(valence, arousal, flatness_eff)

        # Split arousal — diagnostics
        arousal_rhythm, arousal_harm = _split_arousal(audio, sr, bpm)
        tags.extend(_split_tags(arousal_rhythm, arousal_harm))

        return {
            "valence": valence,
            "arousal": arousal,
            "arousal_rhythmic": arousal_rhythm,
            "arousal_harmonic": arousal_harm,
            "label": label,
            "tags": tags,
            "spectral_flatness": flatness_eff,
            "acousticness": None,
            "danceability": None,
            "instrumentalness": None,
            "liveness": None,
            "speechiness": None,
            "backend": "heuristic",
        }

    # ---------- VibeNet ----------

    def _vibenet(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        try:
            from vibenet import VibeNet  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "VibeNet is not installed. Install it with: pip install vibenet"
            ) from exc

        flatness_frames = librosa.feature.spectral_flatness(y=audio)[0]
        _flatness_mean, _flatness_p90, flatness_eff = _effective_flatness(flatness_frames)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
        bpm = float(np.atleast_1d(tempo)[0])
        arousal_rhythm, arousal_harm = _split_arousal(audio, sr, bpm)

        model = _get_vibenet_model()
        preds = model.predict(audio, sr=sr)

        valence = float(np.clip(preds.get("valence", 0.5), 0.0, 1.0))
        arousal = float(np.clip(preds.get("energy", 0.5), 0.0, 1.0))

        label, tags = _classify_mood(valence, arousal, flatness_eff)
        tags.extend(_split_tags(arousal_rhythm, arousal_harm))

        return {
            "valence": valence,
            "arousal": arousal,
            "arousal_rhythmic": arousal_rhythm,
            "arousal_harmonic": arousal_harm,
            "label": label,
            "tags": tags,
            "spectral_flatness": flatness_eff,
            "acousticness": _clip01(preds.get("acousticness")),
            "danceability": _clip01(preds.get("danceability")),
            "instrumentalness": _clip01(preds.get("instrumentalness")),
            "liveness": _clip01(preds.get("liveness")),
            "speechiness": _clip01(preds.get("speechiness")),
            "backend": "vibenet",
        }


def _is_minor(chroma: np.ndarray) -> bool:
    """Rough mode estimate by correlating with Krumhansl profiles."""
    best_major = max(
        float(np.corrcoef(chroma, np.roll(_MAJOR_PROFILE, i))[0, 1]) for i in range(12)
    )
    best_minor = max(
        float(np.corrcoef(chroma, np.roll(_MINOR_PROFILE, i))[0, 1]) for i in range(12)
    )
    return best_minor > best_major


def _clip01(value: Any) -> float | None:
    if value is None:
        return None
    return float(np.clip(float(value), 0.0, 1.0))


_VIBENET_CACHE: Any = None


def _get_vibenet_model() -> Any:
    """Lazy VibeNet initialization — model is heavy, load once."""
    global _VIBENET_CACHE
    if _VIBENET_CACHE is None:
        from vibenet import VibeNet

        _VIBENET_CACHE = VibeNet()
    return _VIBENET_CACHE
