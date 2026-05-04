from __future__ import annotations

from karaoke_system.lyrics.reading import ReadingGenerator
from karaoke_system.models import LyricLine


class AlignmentMerger:
    def __init__(self, reading_generator: ReadingGenerator | None = None) -> None:
        self.reading_generator = reading_generator or ReadingGenerator()

    def enrich(self, lines: list[LyricLine], language: str) -> list[LyricLine]:
        for line in lines:
            for unit in line.units:
                unit.reading = self.reading_generator.get(unit.text, language)
        return lines
