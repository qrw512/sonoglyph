"""Analyzer registry."""

from sonoglyph.analyzers.base import BaseAnalyzer
from sonoglyph.analyzers.energy import EnergyAnalyzer
from sonoglyph.analyzers.key import KeyAnalyzer
from sonoglyph.analyzers.mood import MoodAnalyzer
from sonoglyph.analyzers.spectral import SpectralAnalyzer
from sonoglyph.analyzers.tempo import TempoAnalyzer

REGISTRY: dict[str, type[BaseAnalyzer]] = {
    TempoAnalyzer.name: TempoAnalyzer,
    KeyAnalyzer.name: KeyAnalyzer,
    SpectralAnalyzer.name: SpectralAnalyzer,
    EnergyAnalyzer.name: EnergyAnalyzer,
    MoodAnalyzer.name: MoodAnalyzer,
}

__all__ = [
    "BaseAnalyzer",
    "EnergyAnalyzer",
    "KeyAnalyzer",
    "MoodAnalyzer",
    "SpectralAnalyzer",
    "TempoAnalyzer",
    "REGISTRY",
]
