# Examples

Runnable examples that show how to use Sonoglyph — from a one-line
analysis to building mood-based playlists and talking to the REST API.

[English](README.md) · [Русский](README.ru.md)

---

## Index

| # | File | What it shows |
|---|---|---|
| 01 | [`01_basic_library.py`](01_basic_library.py) | Analyze one track with the Python API |
| 02 | [`02_choose_features.py`](02_choose_features.py) | Run only selected analyzers (faster) |
| 03 | [`03_batch_and_export.py`](03_batch_and_export.py) | Batch a folder, export CSV + HTML |
| 04 | [`04_mood_deep_dive.py`](04_mood_deep_dive.py) | Read valence / arousal / tags in detail |
| 05 | [`05_playlist_builder.py`](05_playlist_builder.py) | Build mood-based `.m3u` playlists |
| 06 | [`06_custom_analyzer.py`](06_custom_analyzer.py) | Write your own analyzer |
| 07 | [`07_server_client.py`](07_server_client.py) | Talk to the REST API from Python |
| — | [`basic_usage.py`](basic_usage.py) | Minimal HTTP API client |

---

## Requirements

Install Sonoglyph with the optional extras used by these examples:

```bash
pip install "sonoglyph[html,server]"
```

- `[html]` — pulls in `matplotlib` for the spectrogram in the HTML report
- `[server]` — pulls in `fastapi` + `uvicorn` for the REST examples

---

## Running

Most examples expect an `.mp3` file in this folder. Grab any track
you own, drop it in `examples/`, and run:

```bash
python examples/01_basic_library.py my_track.mp3
```

Examples `03` and `05` scan the folder for `*.mp3` files and process
everything they find:

```bash
python examples/03_batch_and_export.py
python examples/05_playlist_builder.py
```

For `07_server_client.py` and `basic_usage.py`, start the server
first in another terminal:

```bash
sonoglyph serve
```

Then, in a second terminal:

```bash
python examples/07_server_client.py
```

---

## What each example covers

### `01_basic_library.py` — first contact

The simplest possible usage: `analyze(path)` returns a typed
`AnalysisResult` with `.tempo`, `.key`, `.spectral`, `.energy`,
and `.mood` fields. Shows how to read each one.

### `02_choose_features.py` — selective analysis

Full analysis runs every analyzer. For speed, request only what
you need:

```python
analyze(path, features=["tempo"])                 # ~2 sec
analyze(path, features=["mood"])                  # ~5 sec
analyze(path, features=["tempo", "key", "mood"])  # middle ground
```

### `03_batch_and_export.py` — whole library

Parallel analysis of every track in a folder, then export to:

- `library.csv` — flat table, opens in Excel / pandas
- `report.html` — interactive dark-theme report with modal per track

### `04_mood_deep_dive.py` — emotional landscape

Explains the mood model: valence (sad ↔ happy), arousal (calm ↔ energetic),
split arousal (rhythmic vs harmonic), and tags (`atmospheric`, `dark`, etc.).

### `05_playlist_builder.py` — practical use case

Classifies every track by mood and writes one `.m3u` playlist per mood
bucket: `01_happy.m3u`, `03_melancholic.m3u`, etc. Open them in any
player (VLC, foobar2000, MusicBee).

### `06_custom_analyzer.py` — extensibility

Shows how to subclass `BaseAnalyzer` and implement your own feature
extractor. In this example we build a `LoudnessAnalyzer` that returns
an approximate dBFS loudness value.

To plug a custom analyzer into `analyze()`, register it in
`src/sonoglyph/analyzers/__init__.py`.

### `07_server_client.py` — REST integration

Demonstrates all three main endpoints:

- `GET  /api/health`           — version check
- `POST /api/analyze-by-path`  — analyze a server-side file
- `POST /api/analyze`          — upload + analyze in one request
- `GET  /api/features`         — list available analyzers

---

## Troubleshooting

**`File not found: ...`** — check the path. Most examples default to
`ginseng_strip.mp3`; replace it with a track you actually have.

**`httpx.ReadTimeout`** — analysis of a full track takes 5–10 seconds
on CPU. The examples already set a 60-second timeout, but if your
machine is slow, bump it further.

**`Cannot connect to http://127.0.0.1:8000`** — the server isn't
running. Open another terminal and run `sonoglyph serve`.

**`ModuleNotFoundError: matplotlib`** — install the extras:
`pip install "sonoglyph[html]"`.

---

## Contributing an example

If you build something interesting with Sonoglyph, we'd love to
include it. Open a PR that adds `examples/NN_your_idea.py` and a
one-line entry to the index table above. Keep it self-contained —
no hardcoded paths, no external services.
