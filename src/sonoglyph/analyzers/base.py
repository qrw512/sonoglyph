"""Base analyzer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class BaseAnalyzer(ABC):
    """Abstract analyzer. Subclasses implement `_analyze`."""

    name: str = "base"

    @abstractmethod
    def _analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        """Return a dict with extracted features."""

    def analyze(self, audio: np.ndarray, sr: int) -> dict[str, Any]:
        """Public entry point with basic validation."""
        if audio.size == 0:
            raise ValueError(f"[{self.name}] Empty audio signal")
        return self._analyze(audio, sr)
