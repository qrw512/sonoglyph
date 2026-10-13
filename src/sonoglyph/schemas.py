"""Pydantic schemas for typed analysis results."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class TempoFeatures(BaseModel):
    """Rhythmic characteristics of a track."""

    bpm: float = Field(..., description="Tempo in beats per minute")
    beat_count: int = Field(..., description="Number of detected beats")
    beat_positions: list[float] = Field(
        default_factory=list, description="Beat positions in seconds"
    )
    confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Algorithm confidence"
    )


class KeyFeatures(BaseModel):
    """Tonal characteristics."""

    name: str = Field(..., description="Key name, e.g. 'A minor'")
    tonic: str = Field(..., description="Tonic, e.g. 'A'")
    mode: str = Field(..., description="Mode: 'major' or 'minor'")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class SpectralFeatures(BaseModel):
    """Spectral characteristics (timbre)."""

    centroid_mean: float = Field(..., description="Mean spectral centroid, Hz")
    centroid_std: float = Field(..., description="Centroid standard deviation")
    rolloff_mean: float = Field(..., description="Mean rolloff, Hz")
    zcr_mean: float = Field(..., description="Mean zero-crossing rate")
    mfcc_mean: list[float] = Field(
        default_factory=list, description="Mean MFCC values (13 coefficients)"
    )


class EnergyFeatures(BaseModel):
    """Energy characteristics."""

    rms_mean: float = Field(..., description="Mean RMS energy")
    rms_std: float = Field(..., description="RMS standard deviation")
    dynamic_range_db: float = Field(..., description="Dynamic range in dB")


class MoodFeatures(BaseModel):
    """Emotional and perceptual characteristics."""

    valence: float = Field(
        ..., ge=0.0, le=1.0, description="Valence: 0 = sad, 1 = happy"
    )
    arousal: float = Field(
        ..., ge=0.0, le=1.0,
        description="Overall arousal: 0.55·rhythmic + 0.45·harmonic",
    )
    arousal_rhythmic: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Arousal from rhythm section (tempo, transients, percussive RMS)",
    )
    arousal_harmonic: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Arousal from harmony (brightness, chroma motion, sustained RMS)",
    )
    label: str = Field(
        ...,
        description="Russell quadrant: happy/calm/sad/angry/neutral/"
        "melancholic (extended map)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Extra tags: atmospheric, noisy, dark, dreamy, "
        "aggressive, upbeat, anthemic, driving",
    )
    spectral_flatness: float | None = Field(
        None, ge=0.0, description="Effective spectral flatness"
    )
    acousticness: float | None = Field(None, ge=0.0, le=1.0)
    danceability: float | None = Field(None, ge=0.0, le=1.0)
    instrumentalness: float | None = Field(None, ge=0.0, le=1.0)
    liveness: float | None = Field(None, ge=0.0, le=1.0)
    speechiness: float | None = Field(None, ge=0.0, le=1.0)
    backend: str = Field("heuristic", description="Which engine computed this")


class AudioMetadata(BaseModel):
    """Source file metadata."""

    path: str
    duration_sec: float
    sample_rate: int
    channels: int
    format: str


class AnalysisResult(BaseModel):
    """Full analysis result for a track."""

    metadata: AudioMetadata
    tempo: TempoFeatures | None = None
    key: KeyFeatures | None = None
    spectral: SpectralFeatures | None = None
    energy: EnergyFeatures | None = None
    mood: MoodFeatures | None = None

    def summary(self) -> str:
        """Short human-readable summary (single-line log format)."""
        name = Path(self.metadata.path).name
        m, s = divmod(int(round(self.metadata.duration_sec)), 60)
        lines = [
            f"📁 {name}",
            f"⏱  {m}:{s:02d} @ {self.metadata.sample_rate} Hz",
        ]
        if self.tempo:
            lines.append(f"🥁 {self.tempo.bpm:.1f} BPM")
        if self.key:
            lines.append(f"🎼 {self.key.name} (conf {self.key.confidence:.2f})")
        if self.mood:
            lines.append(
                f"😊 {self.mood.label} — "
                f"valence={self.mood.valence:.2f}, arousal={self.mood.arousal:.2f}"
            )
        return "\n".join(lines)
