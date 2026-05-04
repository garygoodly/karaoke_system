from __future__ import annotations

from pathlib import Path
import statistics

import numpy as np

from karaoke_system.models import LyricLine, PitchPoint
from karaoke_system.pitch.note_mapper import hz_to_midi

try:
    import librosa
except Exception:  # pragma: no cover - optional dependency path
    librosa = None


class ReferencePitchExtractor:
    def __init__(self, sample_rate: int = 22050, hop_length: int = 256) -> None:
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def attach(self, lines: list[LyricLine], audio_path: str | Path) -> list[LyricLine]:
        if librosa is None:
            return lines
        y, sr = librosa.load(str(audio_path), sr=self.sample_rate, mono=True)
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sr,
            hop_length=self.hop_length,
        )
        times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)
        midi_values = [hz_to_midi(float(value)) if value is not None and not np.isnan(value) else None for value in f0]

        for line in lines:
            for unit in line.units:
                if unit.start is None or unit.end is None:
                    continue
                curve: list[PitchPoint] = []
                midi_bucket: list[float] = []
                for time_value, midi_value in zip(times, midi_values, strict=False):
                    if unit.start <= float(time_value) <= unit.end:
                        curve.append(PitchPoint(time=float(time_value), midi=midi_value))
                        if midi_value is not None:
                            midi_bucket.append(float(midi_value))
                unit.pitch_curve = curve
                unit.pitch_midi = statistics.median(midi_bucket) if midi_bucket else None
        return lines
