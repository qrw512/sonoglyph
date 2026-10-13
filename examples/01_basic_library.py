"""Example 1: analyze a single track via the Python library.

Run:
    python examples/01_basic_library.py path/to/track.mp3
"""

import sys
from pathlib import Path

from sonoglyph import analyze


def main(path: str) -> None:
    track = Path(path)
    if not track.exists():
        print(f"File not found: {track}")
        sys.exit(1)

    print(f"Analyzing {track.name}...\n")
    result = analyze(track)

    # --- Pretty console output ---
    print(result.summary())

    # --- Access individual fields programmatically ---
    print("\nDetailed breakdown:")
    if result.tempo:
        print(f"  BPM:         {result.tempo.bpm:.2f}")
        print(f"  Confidence:  {result.tempo.confidence:.2%}")
        print(f"  Beats found: {result.tempo.beat_count}")

    if result.key:
        print(f"  Key:         {result.key.name}")
        print(f"  Mode:        {result.key.mode}")
        print(f"  Confidence:  {result.key.confidence:.2%}")

    if result.energy:
        print(f"  RMS:         {result.energy.rms_mean:.4f}")
        print(f"  Dynamic:     {result.energy.dynamic_range_db:.1f} dB")

    if result.mood:
        print(f"  Mood:        {result.mood.label}")
        print(f"  Valence:     {result.mood.valence:.2f}")
        print(f"  Arousal:     {result.mood.arousal:.2f}")
        if result.mood.tags:
            print(f"  Tags:        {', '.join(result.mood.tags)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/01_basic_library.py <audio-file>")
        sys.exit(1)
    main(sys.argv[1])
