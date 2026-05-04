from __future__ import annotations

from pathlib import Path

import srt

from karaoke_system.lyrics.normalize import normalize_lyrics_text
from karaoke_system.lyrics.tokenize import build_units
from karaoke_system.models import LyricLine


def parse_srt(path: str | Path, lang: str) -> list[LyricLine]:
    subtitles = list(srt.parse(Path(path).read_text(encoding="utf-8")))
    lines: list[LyricLine] = []
    for index, item in enumerate(subtitles):
        text = normalize_lyrics_text(item.content.replace("\n", " "), lang)
        if not text:
            continue
        line_id = f"line_{index:04d}"
        lines.append(
            LyricLine(
                id=line_id,
                text=text,
                lang=lang,
                start=item.start.total_seconds(),
                end=item.end.total_seconds(),
                units=build_units(line_id=line_id, text=text, lang=lang),
            )
        )
    return lines
