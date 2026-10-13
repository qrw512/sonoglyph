"""Example 2: run only the analyzers you need.

Selective analysis is faster: asking for just 'tempo' skips HPSS,
chroma, MFCC, and mood computation.
"""

from pathlib import Path

from sonoglyph import analyze

TRACK = Path(__file__).parent / "ginseng_strip.mp3"


def main() -> None:
    # Full analysis (all default analyzers)
    print("=== Full analysis ===")
    full = analyze(TRACK)
    print(f"Mood:  {full.mood.label if full.mood else '—'}")
    print(f"Key:   {full.key.name if full.key else '—'}")
    print(f"Spectral available: {full.spectral is not None}")

    # Only tempo — the fastest path (~2 sec for a 3-min track)
    print("\n=== Tempo only ===")
    fast = analyze(TRACK, features=["tempo"])
    print(f"BPM:   {fast.tempo.bpm:.1f}")
    print(f"Key:   {fast.key}")  # None — we didn't ask for it

    # Only mood — the slowest, uses HPSS internally
    print("\n=== Mood only ===")
    mood_result = analyze(TRACK, features=["mood"])
    print(f"Label: {mood_result.mood.label}")
    print(f"Tags:  {mood_result.mood.tags}")


if __name__ == "__main__":
    main()
