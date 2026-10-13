"""Example 6: write your own analyzer.

Shows how to plug in a custom feature extractor without touching
the core library. We implement a simple 'loudness' analyzer that
returns an approximate LUFS-like value.

To actually use it inside `analyze()`, you would register it in
`sonoglyph/analyzers/__init__.py`. This example shows the class
in isolation and how to call it manually.
"""

from __future__ import annotations

from typing import Any

import librosa
import numpy as np

from sonoglyph.analyzers.base import BaseAnalyzer
from sonoglyph.io import load_audio


class LoudnessAnalyzer(BaseAnalyzer):
    """Approximate integrated loudness in dBFS.

    This is NOT real LUFS (EBU R128) — it's a simplified RMS-based
    proxy that's good enough for comparing tracks in the same library.
    """

    name = "loudness"

    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        rms = librosa.feature.rms(y=audio)[0]
        # dBFS relative to full scale (1.0)
        rms_dbfs = 20 * np.log10(np.maximum(rms, 1e-10))

        return {
            "integrated_dbfs": float(rms_dbfs.mean()),
            "peak_dbfs": float(rms_dbfs.max()),
            "loudness_range_db": float(rms_dbfs.max() - rms_dbfs.min()),
        }


def main() -> None:
    from pathlib import Path

    track = Path(__file__).parent / "ginseng_strip.mp3"
    if not track.exists():
        print(f"Place a track at {track} to run this example.")
        return

    audio, sr = load_audio(track)
    analyzer = LoudnessAnalyzer()
    result = analyzer.analyze(audio, sr)

    print("Loudness analysis:")
    for k, v in result.items():
        print(f"  {k:20s}  {v:+.2f} dB")


if __name__ == "__main__":
    main()
