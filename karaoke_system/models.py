from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal
import json


UnitType = Literal["word", "syllable", "mora", "char"]
AudioKind = Literal["original", "karaoke"]


@dataclass(slots=True)
class PitchPoint:
    time: float
    midi: float | None


@dataclass(slots=True)
class LyricUnit:
    id: str
    text: str
    lang: str
    unit_type: UnitType
    start: float | None = None
    end: float | None = None
    reading: str | None = None
    confidence: float | None = None
    pitch_midi: float | None = None
    pitch_curve: list[PitchPoint] = field(default_factory=list)


@dataclass(slots=True)
class LyricLine:
    id: str
    text: str
    lang: str
    start: float | None = None
    end: float | None = None
    units: list[LyricUnit] = field(default_factory=list)


@dataclass(slots=True)
class AudioVariant:
    kind: AudioKind
    key_shift: int
    audio_path: str


@dataclass(slots=True)
class SongManifest:
    song_id: str
    title: str
    language: str
    video_only_path: str
    lyrics_path: str
    audio_variants: list[AudioVariant]
    default_mode: AudioKind = "original"
    version: str = "1.0"

    @classmethod
    def load(cls, path: str | Path) -> "SongManifest":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        audio_variants = [AudioVariant(**item) for item in payload["audio_variants"]]
        payload["audio_variants"] = audio_variants
        return cls(**payload)

    def save(self, path: str | Path) -> None:
        payload = asdict(self)
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def find_audio_variant(self, kind: AudioKind, key_shift: int = 0) -> AudioVariant | None:
        for variant in self.audio_variants:
            if variant.kind == kind and variant.key_shift == key_shift:
                return variant
        return None


@dataclass(slots=True)
class JudgeSnapshot:
    playback_time: float
    live_midi: float | None
    target_midi: float | None
    instant_score: float
    average_score: float
    active_line_id: str | None
    active_unit_id: str | None


def _serialize_pitch_point(point: PitchPoint) -> dict[str, Any]:
    return {"time": point.time, "midi": point.midi}


def _serialize_unit(unit: LyricUnit) -> dict[str, Any]:
    payload = asdict(unit)
    payload["pitch_curve"] = [_serialize_pitch_point(point) for point in unit.pitch_curve]
    return payload


def _serialize_line(line: LyricLine) -> dict[str, Any]:
    return {
        "id": line.id,
        "text": line.text,
        "lang": line.lang,
        "start": line.start,
        "end": line.end,
        "units": [_serialize_unit(unit) for unit in line.units],
    }


def save_lines(lines: list[LyricLine], path: str | Path) -> None:
    payload = [_serialize_line(line) for line in lines]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_lines(path: str | Path) -> list[LyricLine]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    lines: list[LyricLine] = []
    for line_data in payload:
        units: list[LyricUnit] = []
        for unit_data in line_data.get("units", []):
            curve = [PitchPoint(**point) for point in unit_data.get("pitch_curve", [])]
            unit_copy = dict(unit_data)
            unit_copy["pitch_curve"] = curve
            units.append(LyricUnit(**unit_copy))
        line_copy = dict(line_data)
        line_copy["units"] = units
        lines.append(LyricLine(**line_copy))
    return lines
