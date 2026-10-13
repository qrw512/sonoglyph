"""Example 4: focus on mood features.

Shows how to read valence, arousal, split arousal, and tags.
Useful for building mood-based playlists.
"""

from pathlib import Path

from sonoglyph import analyze

TRACK = Path(__file__).parent / "ginseng_strip.mp3"


def describe(mood) -> str:
    """Human-friendly mood description combining label + metrics."""
    if mood is None:
        return "no mood data"
    parts = [mood.label.upper()]
    if mood.tags:
        parts.append(" ".join(f"#{t}" for t in mood.tags))
    return "  ".join(parts)


def main() -> None:
    result = analyze(TRACK, features=["tempo", "key", "mood"])
    m = result.mood
    if m is None:
        print("Mood backend failed. Try SONOGLYPH_MOOD_BACKEND=heuristic")
        return

    print(f"Track:  {Path(result.metadata.path).name}")
    print(f"Mood:   {describe(m)}")
    print(f"Backend: {m.backend}")
    print()

    # --- Russell's circumplex ---
    print("Russell's circumplex:")
    print(f"  Valence  {m.valence:.2f}   (0 = sad,   1 = happy)")
    print(f"  Arousal  {m.arousal:.2f}   (0 = calm,  1 = energetic)")
    print()

    # --- Split arousal (diagnostic) ---
    if m.arousal_rhythmic is not None and m.arousal_harmonic is not None:
        gap = m.arousal_rhythmic - m.arousal_harmonic
        direction = (
            "rhythm-driven" if gap > 0.15
            else "harmony-driven" if gap < -0.15
            else "balanced"
        )
        print("Split arousal:")
        print(f"  Rhythmic  {m.arousal_rhythmic:.2f}")
        print(f"  Harmonic  {m.arousal_harmonic:.2f}")
        print(f"  Gap       {gap:+.2f}  →  {direction}")
        print()

    # --- Texture ---
    if m.spectral_flatness is not None:
        texture = "atmospheric" if m.spectral_flatness >= 0.035 else "clean"
        print(f"Texture:  {texture}  (flatness {m.spectral_flatness:.4f})")


if __name__ == "__main__":
    main()
