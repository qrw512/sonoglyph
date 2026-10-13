"""Shared test fixtures."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear the on-disk cache before every test to avoid cross-test cache hits."""
    from sonoglyph.cache import clear_cache

    clear_cache()
    yield


@pytest.fixture()
def sine_wav(tmp_path):
    """A 2-second WAV file containing a 440 Hz sine wave."""
    sr = 22050
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    audio = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    path = tmp_path / "sine.wav"
    sf.write(path, audio, sr)
    return path


@pytest.fixture()
def metronome_wav(tmp_path):
    """A 4-second WAV file with clicks every 0.5 s (i.e. 120 BPM)."""
    sr = 22050
    duration = 4.0
    audio = np.zeros(int(sr * duration), dtype=np.float32)

    click_len = int(sr * 0.03)  # 30 ms
    t_click = np.linspace(0, 0.03, click_len, endpoint=False)
    # Sharp attack + exponential decay: makes the onset detector fire reliably
    envelope = np.exp(-t_click * 80)
    click = (0.9 * np.sin(2 * np.pi * 1000 * t_click) * envelope).astype(np.float32)

    for i in range(int(duration / 0.5)):
        start = int(i * 0.5 * sr)
        end = min(start + click_len, len(audio))
        audio[start:end] += click[: end - start]

    path = tmp_path / "metronome.wav"
    sf.write(path, audio, sr)
    return path
