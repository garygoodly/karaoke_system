from __future__ import annotations

from pathlib import Path

from karaoke_system.lyrics.normalize import normalize_lyrics_text
from karaoke_system.lyrics.parsers.lrc import parse_lrc
from karaoke_system.lyrics.parsers.srt_parser import parse_srt
from karaoke_system.lyrics.providers.base import LyricsProvider
from karaoke_system.lyrics.tokenize import build_units
from karaoke_system.models import LyricLine


class LocalLyricsProvider(LyricsProvider):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, lang: str) -> list[LyricLine]:
        suffix = self.path.suffix.lower()
        if suffix == ".lrc":
            return parse_lrc(self.path, lang)
        if suffix == ".srt":
            return parse_srt(self.path, lang)
        if suffix == ".txt":
            return self._parse_txt(lang)
        if suffix == ".json":
            raise ValueError("JSON lyric sources are not supported here; use lyrics.json as a final aligned asset.")
        raise ValueError(f"Unsupported lyric file type: {self.path.suffix}")

    def _parse_txt(self, lang: str) -> list[LyricLine]:
        lines: list[LyricLine] = []
        for index, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines()):
            text = normalize_lyrics_text(raw, lang)
            if not text:
                continue
            line_id = f"line_{index:04d}"
            lines.append(
                LyricLine(
                    id=line_id,
                    text=text,
                    lang=lang,
                    start=None,
                    end=None,
                    units=build_units(line_id=line_id, text=text, lang=lang),
                )
            )
        return lines
