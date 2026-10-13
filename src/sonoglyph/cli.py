"""Command-line interface for Sonoglyph."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sonoglyph.api import analyze, analyze_batch
from sonoglyph.schemas import (
    AnalysisResult,
    EnergyFeatures,
    KeyFeatures,
    MoodFeatures,
    SpectralFeatures,
    TempoFeatures,
)

app = typer.Typer(
    help="Sonoglyph — extract musical features from audio files.",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------- helpers

def _fmt_duration(sec: float) -> str:
    """Format seconds as M:SS."""
    total = int(round(sec))
    m, s = divmod(total, 60)
    return f"{m}:{s:02d}"


def _bar(value: float, width: int = 24, fill: str = "█", empty: str = "░") -> str:
    """Render a text progress bar of given width."""
    v = max(0.0, min(1.0, value))
    filled = int(round(v * width))
    return fill * filled + empty * (width - filled)


def _valence_color(v: float) -> str:
    if v >= 0.66:
        return "green"
    if v >= 0.40:
        return "yellow"
    return "red"


def _arousal_color(a: float) -> str:
    if a >= 0.66:
        return "red"
    if a >= 0.40:
        return "yellow"
    return "blue"


# ---------------------------------------------------------------- panels

def _render_tempo(t: TempoFeatures) -> Panel:
    body = Text()
    body.append(f"{t.bpm:6.1f}", style="bold cyan")
    body.append(" BPM\n", style="dim")
    body.append(f"{t.beat_count} beats", style="dim")
    body.append("  ·  ", style="dim")
    body.append(f"conf {t.confidence:.2f}", style="dim")
    return Panel(
        body,
        title="[bold]🥁 Tempo[/bold]",
        border_style="cyan",
        padding=(0, 1),
    )


def _render_key(k: KeyFeatures) -> Panel:
    body = Text()
    body.append(k.name, style="bold magenta")
    body.append("\n")
    icon = "♭" if k.mode == "minor" else "♯"
    body.append(f"{icon} {k.mode}", style="dim")
    body.append("  ·  ", style="dim")
    body.append(f"conf {k.confidence:.2f}", style="dim")
    return Panel(
        body,
        title="[bold]🎼 Key[/bold]",
        border_style="magenta",
        padding=(0, 1),
    )


def _render_mood(m: MoodFeatures) -> Panel:
    body = Text()
    body.append(m.label.upper(), style=f"bold {_valence_color(m.valence)}")
    body.append(f"   (backend: {m.backend})", style="dim")

    if m.tags:
        body.append("\n")
        for tag in m.tags:
            body.append(f"  #{tag}", style="italic dim")

    body.append("\n\n")

    body.append("Valence  ")
    body.append(_bar(m.valence), style=_valence_color(m.valence))
    body.append(f"  {m.valence:.2f}\n", style="bold")

    body.append("Arousal  ")
    body.append(_bar(m.arousal), style=_arousal_color(m.arousal))
    body.append(f"  {m.arousal:.2f}", style="bold")

    # Split arousal — show only if present
    if m.arousal_rhythmic is not None and m.arousal_harmonic is not None:
        body.append("\n\n")
        body.append("  rhythmic  ", style="dim")
        body.append(_bar(m.arousal_rhythmic, width=16), style="red")
        body.append(f"  {m.arousal_rhythmic:.2f}\n", style="dim")
        body.append("  harmonic  ", style="dim")
        body.append(_bar(m.arousal_harmonic, width=16), style="blue")
        body.append(f"  {m.arousal_harmonic:.2f}\n", style="dim")

    if m.spectral_flatness is not None:
        body.append("\nFlatness  ", style="dim")
        body.append(_bar(min(m.spectral_flatness * 6.0, 1.0), width=16), style="magenta")
        body.append(f"  {m.spectral_flatness:.4f}\n", style="dim")

    extras = [
        ("danceability", m.danceability),
        ("acousticness", m.acousticness),
        ("instrumentalness", m.instrumentalness),
        ("liveness", m.liveness),
        ("speechiness", m.speechiness),
    ]
    extras = [(k, v) for k, v in extras if v is not None]
    if extras:
        body.append("\n")
        for name, val in extras:
            body.append(f"{name:<17}", style="dim")
            body.append(_bar(val, width=16), style="cyan")
            body.append(f"  {val:.2f}\n")

    return Panel(
        body,
        title="[bold]😊 Mood[/bold]",
        border_style="yellow",
        padding=(0, 1),
    )


def _render_spectral(s: SpectralFeatures) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="left")
    table.add_column(style="bold", justify="right")
    table.add_row("Centroid", f"{s.centroid_mean:7.0f} Hz  ± {s.centroid_std:.0f}")
    table.add_row("Rolloff", f"{s.rolloff_mean:7.0f} Hz")
    table.add_row("ZCR", f"{s.zcr_mean:7.4f}")
    return Panel(
        table,
        title="[bold]🎨 Spectral[/bold]",
        border_style="blue",
        padding=(0, 1),
    )


def _render_energy(e: EnergyFeatures) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", justify="left")
    table.add_column(style="bold", justify="right")
    table.add_row("RMS", f"{e.rms_mean:7.4f}  ± {e.rms_std:.4f}")
    table.add_row("Dynamic range", f"{e.dynamic_range_db:7.1f} dB")
    return Panel(
        table,
        title="[bold]⚡ Energy[/bold]",
        border_style="green",
        padding=(0, 1),
    )


# ---------------------------------------------------------------- pretty print

def _print_pretty(result: AnalysisResult) -> None:
    """Render a rich, multi-panel report for a single track."""
    meta = result.metadata
    header = Panel(
        f"[bold]{Path(meta.path).name}[/bold]\n"
        f"[dim]{_fmt_duration(meta.duration_sec)}  ·  "
        f"{meta.sample_rate} Hz  ·  {meta.channels}ch  ·  {meta.format.upper()}[/dim]",
        title="[bold cyan]Sonoglyph[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(header)

    cards = []
    if result.tempo:
        cards.append(_render_tempo(result.tempo))
    if result.key:
        cards.append(_render_key(result.key))
    if cards:
        console.print(Columns(cards, expand=True, equal=True))

    if result.mood:
        console.print(_render_mood(result.mood))

    bottom = []
    if result.spectral:
        bottom.append(_render_spectral(result.spectral))
    if result.energy:
        bottom.append(_render_energy(result.energy))
    if bottom:
        console.print(Columns(bottom, expand=True, equal=True))


# ---------------------------------------------------------------- commands

@app.command("analyze")
def analyze_cmd(
    path: Path = typer.Argument(..., exists=True, help="Path to the audio file."),
    as_json: bool = typer.Option(False, "--json", help="Print result as JSON."),
    plain: bool = typer.Option(False, "--plain", help="Print a short plain-text summary."),
    csv_out: Path | None = typer.Option(
        None, "--csv", help="Save the result to a CSV file at the given path."
    ),
    html_out: Path | None = typer.Option(
        None, "--html", help="Generate an HTML report at the given path."
    ),
    no_spectrogram: bool = typer.Option(
        False,
        "--no-spectrogram",
        help="Do not embed mel-spectrograms in the HTML report.",
    ),
) -> None:
    """Analyze a single audio file and print/extract the results."""
    result = analyze(path)

    # --- Exports ---
    if csv_out:
        from sonoglyph.exporters import to_csv

        saved = to_csv([result], csv_out)
        console.print(f"[green]CSV saved:[/green] {saved}")
    if html_out:
        from sonoglyph.exporters import to_html

        saved = to_html(
            [result],
            html_out,
            include_spectrograms=not no_spectrogram,
        )
        console.print(f"[green]HTML saved:[/green] {saved}")

    # If the user only asked for exports — don't flood the console with the pretty report.
    if (csv_out or html_out) and not (as_json or plain):
        return

    if as_json:
        console.print_json(json.dumps(result.model_dump(mode="json"), default=str))
    elif plain:
        console.print(result.summary())
    else:
        _print_pretty(result)


@app.command("batch")
def batch_cmd(
    directory: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="Directory with audio files."
    ),
    pattern: str = typer.Option(
        "*.mp3", "--pattern", "-p", help="Glob pattern for files (default: *.mp3)."
    ),
    features: str = typer.Option(
        "tempo,key,energy,mood",
        "--features",
        "-f",
        help="Comma-separated list of analyzers to run.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Print results as a JSON array."),
    workers: int = typer.Option(
        None,
        "--workers",
        "-w",
        help="Number of worker processes (default: CPU count - 1).",
    ),
    csv_out: Path | None = typer.Option(
        None, "--csv", help="Save the results to a CSV file."
    ),
    html_out: Path | None = typer.Option(
        None, "--html", help="Generate an HTML report."
    ),
    no_spectrogram: bool = typer.Option(
        False,
        "--no-spectrogram",
        help="Do not embed mel-spectrograms in the HTML report.",
    ),
) -> None:
    """Analyze every audio file matching PATTERN in DIRECTORY."""
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
    )

    files = sorted(directory.glob(pattern))
    if not files:
        console.print(
            f"[yellow]No files matched pattern '{pattern}' in {directory}[/yellow]"
        )
        raise typer.Exit(code=1)

    feature_list = [f.strip() for f in features.split(",") if f.strip()]
    console.print(f"[bold]Analyzing {len(files)} files...[/bold]\n")

    results: list = []
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing", total=len(files))
        results = analyze_batch(
            files,
            features=feature_list,
            max_workers=workers,
            progress_callback=lambda n, t: progress.update(task, completed=n),
        )

    # --- JSON-only mode: print and exit before exporting ---
    if as_json:
        payload = [r.model_dump(mode="json") for r in results]
        console.print_json(json.dumps(payload, default=str))
        if not (csv_out or html_out):
            return

    # --- Exports ---
    if csv_out:
        from sonoglyph.exporters import to_csv

        saved = to_csv(results, csv_out)
        console.print(f"[green]CSV saved:[/green] {saved}")
    if html_out:
        from sonoglyph.exporters import to_html

        saved = to_html(
            results,
            html_out,
            include_spectrograms=not no_spectrogram,
        )
        console.print(f"[green]HTML saved:[/green] {saved}")

    if as_json:
        return  # already printed above

    # --- Summary table ---
    table = Table(
        title=f"[bold]Results ({len(results)} tracks)[/bold]",
        show_lines=False,
    )
    table.add_column("File", style="cyan", overflow="fold", max_width=30)
    table.add_column("BPM", justify="right")
    table.add_column("Key", justify="left")
    table.add_column("Mood", justify="left")
    table.add_column("V", justify="right")
    table.add_column("A", justify="right")
    table.add_column("Tags", justify="left")

    for r in sorted(results, key=lambda x: Path(x.metadata.path).name):
        name = Path(r.metadata.path).name
        bpm = f"{r.tempo.bpm:.0f}" if r.tempo else "—"
        key = r.key.name if r.key else "—"
        mood = r.mood.label if r.mood else "—"
        v = f"{r.mood.valence:.2f}" if r.mood else "—"
        a = f"{r.mood.arousal:.2f}" if r.mood else "—"
        tags = " ".join(f"#{t}" for t in (r.mood.tags if r.mood else []))
        table.add_row(name, bpm, key, mood, v, a, tags)

    console.print(table)


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port."),
    reload: bool = typer.Option(
        False, "--reload", help="Auto-reload on code changes (development)."
    ),
) -> None:
    """Start the local REST API server (FastAPI + uvicorn)."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]uvicorn is not installed.[/red]\n"
            "Install it with: [bold]pip install 'sonoglyph[server]'[/bold]"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold green]Sonoglyph API[/bold green] → http://{host}:{port}")
    console.print(f"[dim]Swagger UI: http://{host}:{port}/docs[/dim]\n")
    uvicorn.run(
        "sonoglyph.server.app:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command("version")
def version_cmd() -> None:
    """Print the Sonoglyph version."""
    from sonoglyph import __version__

    console.print(f"sonoglyph {__version__}")


if __name__ == "__main__":
    app()
