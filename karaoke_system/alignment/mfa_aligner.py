from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from karaoke_system.alignment.base import Aligner
from karaoke_system.exceptions import ToolUnavailableError
from karaoke_system.models import LyricLine


class MFAAligner(Aligner):
    """Montreal Forced Aligner adapter.

    This wrapper expects that you already have the MFA binary, acoustic model,
    pronunciation dictionary, and corpus preparation flow configured.
    It intentionally stops early with a clear error if the tool is missing.
    """

    def __init__(self, binary: str = "mfa") -> None:
        self.binary = binary

    def align(
        self,
        audio_path: str | Path,
        lines: list[LyricLine],
        language: str,
        output_dir: str | Path,
    ) -> list[LyricLine]:
        if shutil.which(self.binary) is None:
            raise ToolUnavailableError(
                "Montreal Forced Aligner is not installed. Configure MFA and a language dictionary first."
            )
        raise NotImplementedError(
            "MFA integration depends on your corpus layout and dictionary files. Use heuristic or WhisperX first, "
            "then replace this adapter with your project-specific MFA command."
        )
