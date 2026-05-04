class KaraokeError(Exception):
    """Base exception for the karaoke system."""


class ToolUnavailableError(KaraokeError):
    """Raised when an optional external tool is unavailable."""


class AlignmentError(KaraokeError):
    """Raised when lyric alignment fails."""


class ManifestError(KaraokeError):
    """Raised when a song package is invalid."""
