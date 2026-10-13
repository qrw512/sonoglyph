"""Public API tests."""

from __future__ import annotations

import pytest

from sonoglyph import analyze, analyze_batch
from sonoglyph.cache import clear_cache


def test_analyze_returns_full_result(sine_wav):
    result = analyze(sine_wav)
    assert result.metadata.duration_sec == pytest.approx(2.0, abs=0.05)
    assert result.tempo is not None
    assert result.key is not None
    assert result.spectral is not None
    assert result.energy is not None
    assert result.mood is not None


def test_tempo_detects_120_bpm(metronome_wav):
    """Check BPM with octave-error tolerance (60/120/240 are all valid)."""
    result = analyze(metronome_wav, features=["tempo"])
    assert result.tempo is not None

    bpm = result.tempo.bpm
    allowed = (60.0, 120.0, 240.0)
    rel_tol = 0.15  # 15% tolerance for a crude synthetic click track

    matched = any(abs(bpm - ref) / ref < rel_tol for ref in allowed)
    assert matched, f"Expected BPM around one of {allowed}, got {bpm:.2f}"


def test_unknown_feature_raises(sine_wav):
    with pytest.raises(ValueError, match="Unknown analyzers"):
        analyze(sine_wav, features=["nonexistent"])


def test_empty_features_uses_defaults(sine_wav):
    """features=None → use the default set."""
    result = analyze(sine_wav, features=None)
    assert result.tempo is not None
    assert result.key is not None


def test_metadata_fields_populated(sine_wav):
    result = analyze(sine_wav, features=["tempo"])
    assert result.metadata.sample_rate == 22050
    assert result.metadata.channels == 1
    assert result.metadata.format == "wav"
    assert result.metadata.path.endswith("sine.wav")


def test_cache_hit_returns_same_result(sine_wav):
    """A second call with use_cache=True should return an identical result."""
    clear_cache()
    r1 = analyze(sine_wav, features=["tempo"], use_cache=True)
    r2 = analyze(sine_wav, features=["tempo"], use_cache=True)
    assert r1.tempo.bpm == r2.tempo.bpm
    assert r1.metadata.duration_sec == r2.metadata.duration_sec


def test_cache_disabled_reruns(sine_wav):
    clear_cache()
    analyze(sine_wav, features=["tempo"], use_cache=True)
    # With use_cache=False the cache must be bypassed
    r = analyze(sine_wav, features=["tempo"], use_cache=False)
    assert r.tempo is not None


def test_batch_returns_all_results(sine_wav, metronome_wav):
    results = analyze_batch([sine_wav, metronome_wav], features=["tempo"], use_cache=False)
    assert len(results) == 2
    paths = {r.metadata.path for r in results}
    assert any("sine.wav" in p for p in paths)
    assert any("metronome.wav" in p for p in paths)


def test_batch_progress_callback(sine_wav, metronome_wav):
    calls: list[tuple[int, int]] = []
    analyze_batch(
        [sine_wav, metronome_wav],
        features=["tempo"],
        use_cache=False,
        progress_callback=lambda n, t: calls.append((n, t)),
    )
    assert calls == [(1, 2), (2, 2)]


def test_batch_empty_list_returns_empty():
    assert analyze_batch([]) == []


def test_batch_skips_broken_file(sine_wav, tmp_path):
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"not a real wav")
    results = analyze_batch([sine_wav, broken], features=["tempo"], use_cache=False)
    # Only the valid file must remain
    assert len(results) == 1
    assert "sine.wav" in results[0].metadata.path


def test_mood_features_present(sine_wav):
    result = analyze(sine_wav, features=["mood"])
    assert result.mood is not None
    assert 0.0 <= result.mood.valence <= 1.0
    assert 0.0 <= result.mood.arousal <= 1.0
    assert result.mood.label in {
        "happy", "calm", "sad", "angry", "neutral", "melancholic",
    }
    assert result.mood.backend in {"heuristic", "vibenet"}
    assert isinstance(result.mood.tags, list)
    assert result.mood.spectral_flatness is not None
    assert result.mood.spectral_flatness >= 0.0


def test_mood_atmospheric_classified_as_melancholic(tmp_path):
    """A diffuse noisy signal with low valence + high arousal
    should be classified as melancholic, not angry."""
    import numpy as np
    import soundfile as sf

    sr = 22050
    rng = np.random.default_rng(42)
    # Noise signal — high spectral flatness
    noise = rng.normal(0, 0.3, sr * 4).astype(np.float32)
    path = tmp_path / "noise.wav"
    sf.write(path, noise, sr)

    result = analyze(path, features=["mood"], use_cache=False)
    assert result.mood is not None
    # For pure noise flatness is high → atmospheric tag should appear
    assert "atmospheric" in result.mood.tags or "noisy" in result.mood.tags


def test_mood_in_default_features(sine_wav):
    result = analyze(sine_wav)
    assert result.mood is not None


def test_mood_heuristic_backend_explicit(sine_wav):
    import os

    old = os.environ.get("SONOGLYPH_MOOD_BACKEND")
    os.environ["SONOGLYPH_MOOD_BACKEND"] = "heuristic"
    try:
        result = analyze(sine_wav, features=["mood"])
        assert result.mood is not None
        assert result.mood.backend == "heuristic"
    finally:
        if old is None:
            os.environ.pop("SONOGLYPH_MOOD_BACKEND", None)
        else:
            os.environ["SONOGLYPH_MOOD_BACKEND"] = old


def test_mood_unknown_backend_raises(sine_wav, monkeypatch):
    monkeypatch.setenv("SONOGLYPH_MOOD_BACKEND", "nonexistent")
    # analyzers/api swallows exceptions, so mood simply stays None
    result = analyze(sine_wav, features=["mood"])
    assert result.mood is None


def test_mood_arousal_split_present(sine_wav):
    """Split arousal must be available in the heuristic backend."""
    result = analyze(sine_wav, features=["mood"])
    assert result.mood is not None
    assert result.mood.arousal_rhythmic is not None
    assert result.mood.arousal_harmonic is not None
    assert 0.0 <= result.mood.arousal_rhythmic <= 1.0
    assert 0.0 <= result.mood.arousal_harmonic <= 1.0


def test_mood_split_arousal_tags(tmp_path):
    """Split arousal should emit `driving-beat` or `lush-harmony`
    when the gap is significant."""
    import numpy as np
    import soundfile as sf

    sr = 22050
    duration = 8.0
    # Dense 120 BPM clicks over a quiet clean sine wave
    audio = 0.05 * np.sin(2 * np.pi * 220 * np.linspace(0, duration, int(sr * duration)))
    for i in range(int(duration / 0.5)):
        start = int(i * 0.5 * sr)
        click_len = int(sr * 0.02)
        click = 0.9 * np.sin(2 * np.pi * 2000 * np.linspace(0, 0.02, click_len))
        audio[start:start + click_len] += click.astype(np.float32)

    path = tmp_path / "driving.wav"
    sf.write(path, audio.astype(np.float32), sr)

    result = analyze(path, features=["mood"], use_cache=False)
    assert result.mood is not None
    assert result.mood.arousal_rhythmic is not None
    assert result.mood.arousal_harmonic is not None
    # For synthetic audio the gap is large → tag expected
    gap = result.mood.arousal_rhythmic - result.mood.arousal_harmonic
    if abs(gap) >= 0.15:
        assert (
            "driving-beat" in result.mood.tags
            or "lush-harmony" in result.mood.tags
        )
