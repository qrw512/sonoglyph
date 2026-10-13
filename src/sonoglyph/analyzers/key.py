"""Key detection using Krumhansl-Kessler profiles."""

from __future__ import annotations

import warnings
from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer

# Krumhansl-Kessler profiles
_MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
_MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)
_PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class KeyAnalyzer(BaseAnalyzer):
    """Detect musical key by correlating chroma with tonal profiles."""

    name = "key"

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        # Suppress librosa's internal n_fft warning on short signals.
        # It doesn't affect chroma correctness.
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="n_fft=.*is too large", category=UserWarning
            )
            chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
        chroma_mean = chroma.mean(axis=1)

        best_score = -np.inf
        best_key: tuple[str, str] | None = None

        for i in range(12):
            major_rot = np.roll(_MAJOR_PROFILE, i)
            minor_rot = np.roll(_MINOR_PROFILE, i)
            for profile, mode in ((major_rot, "major"), (minor_rot, "minor")):
                score = float(np.corrcoef(chroma_mean, profile)[0, 1])
                if score > best_score:
                    best_score = score
                    best_key = (_PITCHES[i], mode)

        assert best_key is not None
        tonic, mode = best_key
        return {
            "name": f"{tonic} {mode}",
            "tonic": tonic,
            "mode": mode,
            "confidence": max(0.0, min(1.0, best_score)),
        }
