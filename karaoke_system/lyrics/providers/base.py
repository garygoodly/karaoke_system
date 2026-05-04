from __future__ import annotations

from abc import ABC, abstractmethod

from karaoke_system.models import LyricLine


class LyricsProvider(ABC):
    @abstractmethod
    def load(self, lang: str) -> list[LyricLine]:
        raise NotImplementedError
