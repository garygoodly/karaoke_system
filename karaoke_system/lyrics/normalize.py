from __future__ import annotations

import re
import unicodedata

from karaoke_system.utils.text import normalize_spaces


PUNCT_REPLACEMENTS = {
    "，": ",",
    "。": ".",
    "！": "!",
    "？": "?",
    "：": ":",
    "；": ";",
    "（": "(",
    "）": ")",
    "［": "[",
    "］": "]",
    "【": "[",
    "】": "]",
    "「": '"',
    "」": '"',
    "『": '"',
    "』": '"',
}


def normalize_lyrics_text(text: str, lang: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    for src, dst in PUNCT_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(normalize_spaces(line) for line in normalized.splitlines())
    if lang == "en":
        normalized = re.sub(r"\s+([,.!?;:])", r"\1", normalized)
    return normalized.strip()
