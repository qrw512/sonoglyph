"""Tempo and beat tracking based on librosa."""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer


class TempoAnalyzer(BaseAnalyzer):
    """Detect BPM, beat count and beat positions."""

    name = "tempo"

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        tempo, beats = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr, units="time"
        )
        # librosa returns ndarray — coerce to plain float
        bpm = float(np.atleast_1d(tempo)[0])
        beat_positions = [float(b) for b in np.atleast_1d(beats)]

        # Simple confidence: how regular the beats are.
        if len(beat_positions) > 2:
            intervals = np.diff(beat_positions)
            cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9))
            confidence = max(0.0, min(1.0, 1.0 - cv))
        else:
            confidence = 0.0

        return {
            "bpm": bpm,
            "beat_count": len(beat_positions),
            "beat_positions": beat_positions,
            "confidence": confidence,
        }
