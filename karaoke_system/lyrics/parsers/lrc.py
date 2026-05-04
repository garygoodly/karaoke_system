from __future__ import annotations

from pathlib import Path
import re

from karaoke_system.lyrics.normalize import normalize_lyrics_text
from karaoke_system.lyrics.tokenize import build_units
from karaoke_system.models import LyricLine


LRC_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


def parse_lrc(path: str | Path, lang: str) -> list[LyricLine]:
    lines: list[LyricLine] = []
    raw_lines = Path(path).read_text(encoding="utf-8").splitlines()
    for index, raw in enumerate(raw_lines):
        match = LRC_RE.match(raw.strip())
        if not match:
            continue
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        start = minutes * 60 + seconds
        text = normalize_lyrics_text(match.group(3), lang)
        if not text:
            continue
        line_id = f"line_{index:04d}"
        lines.append(
            LyricLine(
                id=line_id,
                text=text,
                lang=lang,
                start=start,
                end=None,
                units=build_units(line_id=line_id, text=text, lang=lang),
            )
        )
    for idx, line in enumerate(lines[:-1]):
        line.end = lines[idx + 1].start
    if lines and lines[-1].end is None:
        lines[-1].end = (lines[-1].start or 0.0) + 4.0
    return lines
