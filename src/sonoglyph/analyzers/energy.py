"""Energy-related features."""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer


class EnergyAnalyzer(BaseAnalyzer):
    """Extract RMS energy and dynamic range."""

    name = "energy"

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        rms = librosa.feature.rms(y=audio)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        dynamic_range = float(np.max(rms_db) - np.min(rms_db))

        return {
            "rms_mean": float(rms.mean()),
            "rms_std": float(rms.std()),
            "dynamic_range_db": dynamic_range,
        }
