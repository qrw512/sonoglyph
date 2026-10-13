"""Audio loading and validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from sonoglyph.exceptions import AudioLoadError

SUPPORTED_EXTENSIONS = {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3", ".m4a"}


def load_audio(
    path: str | Path, sr: int | None = 22050, mono: bool = True
) -> tuple[np.ndarray, int]:
    """Load an audio file and return (signal, sample_rate).

    Args:
        path: path to the audio file.
        sr: target sample rate; None keeps the original.
        mono: downmix to mono if True.

    Returns:
        Tuple of (audio, sample_rate).
    """
    path = Path(path)
    if not path.exists():
        raise AudioLoadError(f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AudioLoadError(f"Unsupported extension: {path.suffix}")

    try:
        audio, native_sr = sf.read(str(path), always_2d=False, dtype="float32")
    except Exception as exc:  # noqa: BLE001
        # Old soundfile cannot read mp3 — fall back to librosa
        try:
            import librosa

            audio, native_sr = librosa.load(str(path), sr=sr, mono=mono)
            return audio, native_sr
        except Exception as inner:  # noqa: BLE001
            raise AudioLoadError(f"Failed to read {path}: {inner}") from exc

    if mono and audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    if sr is not None and sr != native_sr:
        import librosa

        audio = librosa.resample(audio, orig_sr=native_sr, target_sr=sr)
        native_sr = sr

    return audio.astype(np.float32), int(native_sr)
