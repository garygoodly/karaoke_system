from __future__ import annotations

import math


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def hz_to_midi(hz: float | None) -> float | None:
    if hz is None or hz <= 0:
        return None
    return 69 + 12 * math.log2(hz / 440.0)


def midi_to_hz(midi: float | None) -> float | None:
    if midi is None:
        return None
    return 440.0 * (2 ** ((midi - 69) / 12))


def cents_distance(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return (a - b) * 100.0


def midi_to_note_name(midi: float | None) -> str:
    if midi is None:
        return "--"
    rounded = int(round(midi))
    octave = rounded // 12 - 1
    return f"{NOTE_NAMES[rounded % 12]}{octave}"
