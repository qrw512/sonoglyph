"""Sonoglyph exceptions."""


class SonoglyphError(Exception):
    """Base library exception."""


class AudioLoadError(SonoglyphError):
    """Failed to load an audio file."""


class UnsupportedFormatError(SonoglyphError):
    """Audio format is not supported."""


class AnalyzerError(SonoglyphError):
    """Error inside an analyzer."""
