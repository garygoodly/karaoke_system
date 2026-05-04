from __future__ import annotations

from functools import lru_cache


try:
    from pykakasi import kakasi
except Exception:  # pragma: no cover - optional dependency path
    kakasi = None

try:
    from pypinyin import Style, lazy_pinyin
except Exception:  # pragma: no cover - optional dependency path
    Style = None
    lazy_pinyin = None


class ReadingGenerator:
    def __init__(self) -> None:
        self._ja_converter = None
        if kakasi is not None:
            converter = kakasi()
            converter.setMode("J", "H")
            converter.setMode("K", "H")
            self._ja_converter = converter.getConverter()

    @lru_cache(maxsize=4096)
    def get(self, text: str, lang: str) -> str | None:
        if not text:
            return None
        if lang == "ja" and self._ja_converter is not None:
            return self._ja_converter.do(text)
        if lang == "zh" and lazy_pinyin is not None and Style is not None:
            return " ".join(lazy_pinyin(text, style=Style.TONE3))
        if lang == "en":
            return text.lower()
        return None
