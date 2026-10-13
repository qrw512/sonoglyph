"""Example 3: analyze a whole folder and export to CSV + HTML.

Demonstrates parallel processing and both exporters.
"""

from pathlib import Path

from sonoglyph import analyze_batch
from sonoglyph.exporters import to_csv, to_html

# Change this to your music folder
MUSIC_DIR = Path(__file__).parent
PATTERN = "*.mp3"


def main() -> None:
    tracks = sorted(MUSIC_DIR.glob(PATTERN))
    if not tracks:
        print(f"No files matched {PATTERN} in {MUSIC_DIR}")
        return

    print(f"Found {len(tracks)} tracks. Analyzing...\n")

    def on_progress(done: int, total: int) -> None:
        pct = 100 * done / total
        print(f"  [{done}/{total}]  {pct:5.1f}%")

    results = analyze_batch(
        tracks,
        features=["tempo", "key", "energy", "mood"],
        progress_callback=on_progress,
    )

    print(f"\nAnalyzed {len(results)} tracks.")

    # --- Export to CSV (flat table, opens in Excel) ---
    csv_path = to_csv(results, "library.csv")
    print(f"CSV saved:  {csv_path}")

    # --- Export to interactive HTML report ---
    html_path = to_html(results, "report.html", include_spectrograms=True)
    print(f"HTML saved: {html_path}")
    print("\nOpen report.html in a browser to explore the results.")


if __name__ == "__main__":
    main()
