<div align="center">

# 🎵 Sonoglyph

**Extract musical features from audio — tempo, key, mood, spectral data and more.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-18%20passed-brightgreen.svg)]()

[English](README.md) · [Русский](README.ru.md)

</div>

---

## What is it?

**Sonoglyph** is a Python library and CLI tool that analyzes audio files and extracts musical features: **tempo**, **key**, **mood**, **spectral characteristics**, **energy**, and more. Works out of the box with no ML dependencies, optionally plugs in neural network backends for higher accuracy.

Use cases:

- 🎧 Build smart playlists by tempo, key or mood
- 📊 Analyze your music library in batch (CSV/HTML reports)
- 🤖 Add music understanding to your app via REST API
- 🔬 Research Music Information Retrieval (MIR)

---

## Features

| Feature | Description |
|---|---|
| 🥁 **Tempo / BPM** | Beat tracking with confidence estimation |
| 🎼 **Key detection** | Krumhansl-Kessler profiles, tonic + mode |
| 🎨 **Spectral features** | Centroid, rolloff, ZCR, 13 MFCC coefficients |
| ⚡ **Energy** | RMS mean/std, dynamic range in dB |
| 😊 **Mood** | Valence/Arousal + labels + tags |
| 🎭 **Extended mood map** | Distinguishes `melancholic` from `angry` via spectral flatness |
| 💾 **Disk cache** | SHA-256 keyed, avoids recomputation |
| ⚡ **Parallel batch** | `ProcessPoolExecutor`, uses all CPU cores |
| 📤 **CSV export** | Flat table, Excel-friendly (utf-8-sig) |
| 🌐 **HTML report** | Dark theme, sortable, filterable, modal with spectrogram |
| 🚀 **REST API** | FastAPI server for language-agnostic integration |

---

## Installation

Basic:

```bash
pip install sonoglyph
```

With HTML reports:

```bash
pip install "sonoglyph[html]"
```

With REST API server:

```bash
pip install "sonoglyph[server]"
```

Everything:

```bash
pip install "sonoglyph[html,server,ml]"
```

From source:

```bash
git clone https://github.com/sonoglyph/sonoglyph.git
cd sonoglyph
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,html,server]"
```

On Windows, activate the venv with `.venv\Scripts\activate` instead.

---

## Quick start

### CLI — analyze one file

```bash
sonoglyph analyze track.mp3
```

Output:

```
╭────────────────────────────── Sonoglyph ─────────────────────────────╮
│  track.mp3                                                           │
│  2:34  ·  22050 Hz  ·  1ch  ·  MP3                                   │
╰──────────────────────────────────────────────────────────────────────╯
╭─────── 🥁 Tempo ────────╮           ╭──────── 🎼 Key ─────────╮
│  117.5 BPM              │           │ D# minor                 │
│ 292 beats  ·  conf 0.97 │           │ ♭ minor  ·  conf 0.55    │
╰─────────────────────────╯           ╰──────────────────────────╯
╭────────────────────────── 😊 Mood ───────────────────────────╮
│ MELANCHOLIC   (backend: heuristic)                           │
│   #atmospheric  #dark                                        │
│                                                              │
│ Valence  ██████████░░░░░░░░░░░░░░  0.40                      │
│ Arousal  ███████████████░░░░░░░░░  0.63                      │
│                                                              │
│ Flatness ████░░░░░░░░░░░░  0.0425                            │
╰──────────────────────────────────────────────────────────────╯
╭────── 🎨 Spectral ──────╮      ╭───────── ⚡ Energy ──────────╮
│ Centroid     2260 Hz    │      │ RMS       0.1900 ± 0.1015     │
│ Rolloff      4650 Hz    │      │ Dynamic         69.6 dB       │
│ ZCR           0.0963    │      ╰───────────────────────────────╯
╰─────────────────────────╯
```

### CLI — batch directory

```bash
sonoglyph batch ./music/ --pattern "*.mp3" --html report.html --csv library.csv
```

Generates: progress bar, terminal summary table, `report.html` (dark-theme modal report) and `library.csv`.

### Python API

```python
from sonoglyph import analyze, analyze_batch
from sonoglyph.exporters import to_csv, to_html


def main() -> None:
    # Single track
    result = analyze("1.mp3")
    print(f"BPM:   {result.tempo.bpm:.1f}")
    print(f"Key:   {result.key.name}")
    print(f"Mood:  {result.mood.label}")
    print(f"Tags:  {result.mood.tags}")
    print(f"Valence: {result.mood.valence:.2f}")
    print()

    # Batch — must be inside main() on Windows
    results = analyze_batch(
        ["1.mp3", "2.mp3", "3.mp3"],
        features=["tempo", "mood"],
    )

    to_csv(results, "library.csv")
    to_html(results, "report.html", include_spectrograms=True)
    print(f"Done: {len(results)} tracks analyzed.")


if __name__ == "__main__":
    main()
```

### REST API

```bash
sonoglyph serve --host 127.0.0.1 --port 8000
```

Then:

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/api/analyze-by-path -H "Content-Type: application/json" -d '{"path": "track.mp3", "features": ["tempo", "mood"]}'

curl -X POST http://127.0.0.1:8000/api/analyze -F "file=@track.mp3" -F "features=tempo,mood"
```

Interactive docs: <http://127.0.0.1:8000/docs>

---

## Real examples

### Example 1 — Cloud rap, melancholic

```json
{
  "tempo": { "bpm": 117.45, "confidence": 0.97, "beat_count": 292 },
  "key":   { "name": "D# minor", "confidence": 0.55 },
  "mood":  {
    "label": "melancholic",
    "valence": 0.40,
    "arousal": 0.63,
    "tags": ["atmospheric", "dark"],
    "spectral_flatness": 0.0425
  }
}
```

**Why "melancholic" and not "angry":** the track has energetic 808 bass and sharp hi-hats, but also a diffuse, reverberant atmosphere. Sonoglyph uses **spectral flatness** (p90 percentile) to distinguish the "atmospheric + energetic" quadrant from "aggressive" — a classic mistake for naive valence/arousal classifiers.

### Example 2 — Trap, energetic

```json
{
  "tempo": { "bpm": 143.55, "confidence": 0.96, "beat_count": 501 },
  "key":   { "name": "E minor", "confidence": 0.59 },
  "mood":  {
    "label": "happy",
    "valence": 0.57,
    "arousal": 0.82,
    "arousal_rhythmic": 0.66,
    "arousal_harmonic": 0.71,
    "tags": ["upbeat"],
    "spectral_flatness": 0.0204
  }
}
```

**Beat stability analysis** (from HTML modal):

| Metric | Value |
|---|---|
| Mean interval | 418.0 ms |
| Median interval | 417.9 ms |
| Std deviation | 33.2 ms |
| CV (stability) | 0.0793 |
| BPM from intervals | 143.52 (matches `bpm` 143.55 ✅) |

### Example 3 — HTML report

```bash
sonoglyph batch ./music/ --html report.html
```

Open `report.html` in a browser. Features:

- Filter by track name, key, tag
- Sort by BPM, mood, valence, arousal
- Click a track → modal with waveform + beat markers, mel spectrogram, beat interval histogram, beat positions timeline, and all stats

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SONOGLYPH_CACHE_DIR` | `~/.cache/sonoglyph` | Cache directory |
| `SONOGLYPH_MOOD_BACKEND` | `auto` | `auto` / `heuristic` / `vibenet` |

```bash
export SONOGLYPH_CACHE_DIR=/tmp/sonoglyph-cache
export SONOGLYPH_MOOD_BACKEND=heuristic
```

---

## Project structure

```
sonoglyph/
├── src/sonoglyph/
│   ├── analyzers/          # Tempo, key, spectral, energy, mood
│   ├── exporters/          # CSV, HTML
│   ├── server/             # FastAPI app
│   ├── api.py              # Public API
│   ├── cache.py            # Disk cache
│   ├── cli.py              # Typer CLI
│   ├── io.py               # Audio loading
│   └── schemas.py          # Pydantic models
├── tests/                  # 18 tests
├── examples/
├── benchmarks/
└── pyproject.toml
```


---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgments

Built on: [librosa](https://librosa.org/) · [soundfile](https://python-soundfile.readthedocs.io/) · [pydantic](https://docs.pydantic.dev/) · [Typer](https://typer.tiangolo.com/) · [Rich](https://rich.readthedocs.io/) · [FastAPI](https://fastapi.tiangolo.com/) · [uvicorn](https://www.uvicorn.org/) · [matplotlib](https://matplotlib.org/)

Krumhansl-Kessler tonal profiles from *Cognitive Foundations of Musical Pitch* (1990).
