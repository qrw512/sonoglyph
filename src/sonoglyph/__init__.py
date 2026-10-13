"""Sonoglyph — extract musical features from audio."""

from sonoglyph.api import analyze, analyze_batch
from sonoglyph.exceptions import (
    AnalyzerError,
    AudioLoadError,
    SonoglyphError,
    UnsupportedFormatError,
)
from sonoglyph.schemas import AnalysisResult

__version__ = "0.1.0"

__all__ = [
    "AnalysisResult",
    "AnalyzerError",
    "AudioLoadError",
    "SonoglyphError",
    "UnsupportedFormatError",
    "analyze",
    "analyze_batch",
]
