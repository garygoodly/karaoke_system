from __future__ import annotations

import re
from typing import Iterable

from karaoke_system.models import LyricUnit


EN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
CJK_CHAR_RE = re.compile(r"[\u3400-\u9fff]")
JP_CHAR_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fffー]")
PUNCT_RE = re.compile(r"^[^\w\u3400-\u9fff\u3040-\u30ff]+$")


def infer_unit_type(lang: str) -> str:
    if lang == "en":
        return "word"
    if lang == "ja":
        return "mora"
    return "char"


def _tokenize_en(text: str) -> list[str]:
    return EN_WORD_RE.findall(text)


def _tokenize_ja(text: str) -> list[str]:
    tokens: list[str] = []
    for char in text:
        if char.isspace():
            continue
        if PUNCT_RE.match(char):
            continue
        tokens.append(char)
    return tokens


def _tokenize_zh(text: str) -> list[str]:
    tokens: list[str] = []
    buffer: list[str] = []
    for char in text:
        if char.isspace():
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            continue
        if CJK_CHAR_RE.match(char):
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            tokens.append(char)
            continue
        if PUNCT_RE.match(char):
            if buffer:
                tokens.append("".join(buffer))
                buffer = []
            continue
        buffer.append(char)
    if buffer:
        tokens.append("".join(buffer))
    return tokens


def tokenize_text(text: str, lang: str) -> list[str]:
    if lang == "en":
        return _tokenize_en(text)
    if lang == "ja":
        return _tokenize_ja(text)
    return _tokenize_zh(text)


def build_units(line_id: str, text: str, lang: str) -> list[LyricUnit]:
    unit_type = infer_unit_type(lang)
    tokens = tokenize_text(text, lang)
    units: list[LyricUnit] = []
    for index, token in enumerate(tokens):
        units.append(
            LyricUnit(
                id=f"{line_id}_u{index:03d}",
                text=token,
                lang=lang,
                unit_type=unit_type,
            )
        )
    return units
