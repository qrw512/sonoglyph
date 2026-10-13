"""Spectral features (timbre)."""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer


class SpectralAnalyzer(BaseAnalyzer):
    """Extract spectral centroid, rolloff, ZCR, MFCC."""

    name = "spectral"

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        # Adaptive n_fft: never larger than the signal length,
        # always a power of two.
        n_fft = min(2048, max(256, 2 ** int(np.log2(max(len(audio), 256)))))

        centroid = librosa.feature.spectral_centroid(y=audio, sr=sr, n_fft=n_fft)[0]
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr, n_fft=n_fft)[0]
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_fft=n_fft, n_mfcc=13)
        mfcc_mean = mfcc.mean(axis=1)

        return {
            "centroid_mean": float(centroid.mean()),
            "centroid_std": float(centroid.std()),
            "rolloff_mean": float(rolloff.mean()),
            "zcr_mean": float(zcr.mean()),
            "mfcc_mean": [float(x) for x in mfcc_mean],
        }
