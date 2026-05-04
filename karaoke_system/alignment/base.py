from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from karaoke_system.models import LyricLine


class Aligner(ABC):
    @abstractmethod
    def align(
        self,
        audio_path: str | Path,
        lines: list[LyricLine],
        language: str,
        output_dir: str | Path,
    ) -> list[LyricLine]:
        raise NotImplementedError
