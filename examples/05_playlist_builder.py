"""Example 5: build mood-based playlists from a folder.

Classifies every track and sorts it into a mood bucket, then
writes one .m3u file per mood.
"""

from collections import defaultdict
from pathlib import Path

from sonoglyph import analyze_batch

MUSIC_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent / "playlists"

# Which moods map to which playlist names
MOOD_PLAYLISTS = {
    "happy": "01_happy",
    "calm": "02_calm",
    "melancholic": "03_melancholic",
    "sad": "04_sad",
    "angry": "05_angry",
    "neutral": "06_neutral",
}


def main() -> None:
    tracks = sorted(MUSIC_DIR.glob("*.mp3"))
    if not tracks:
        print("No tracks found.")
        return

    print(f"Analyzing {len(tracks)} tracks...")
    results = analyze_batch(tracks, features=["mood", "tempo"])

    buckets: dict[str, list] = defaultdict(list)
    for r in results:
        if r.mood is None:
            continue
        buckets[r.mood.label].append(r)

    OUTPUT_DIR.mkdir(exist_ok=True)

    for mood, tracks_in_bucket in buckets.items():
        playlist_name = MOOD_PLAYLISTS.get(mood, f"99_{mood}")
        out = OUTPUT_DIR / f"{playlist_name}.m3u"

        lines = ["#EXTM3U"]
        for r in sorted(tracks_in_bucket, key=lambda x: x.tempo.bpm if x.tempo else 0):
            bpm = f"{r.tempo.bpm:.0f}" if r.tempo else "?"
            lines.append(f"#EXTINF:-1,{Path(r.metadata.path).stem} [{bpm} BPM]")
            lines.append(r.metadata.path)

        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"  {playlist_name}.m3u  ({len(tracks_in_bucket)} tracks)")

    print(f"\nPlaylists written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
