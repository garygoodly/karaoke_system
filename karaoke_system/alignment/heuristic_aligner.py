from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from karaoke_system.alignment.base import Aligner
from karaoke_system.audio.ffmpeg_tools import probe_duration
from karaoke_system.models import LyricLine


class HeuristicAligner(Aligner):
    """Fallback aligner.

    It does not require WhisperX or MFA. If line timestamps exist, it splits the
    line interval across lyric units. If timestamps do not exist, it distributes
    lines across the full audio duration.
    """

    def align(
        self,
        audio_path: str | Path,
        lines: list[LyricLine],
        language: str,
        output_dir: str | Path,
    ) -> list[LyricLine]:
        aligned = deepcopy(lines)
        duration = probe_duration(audio_path)
        if not aligned:
            return aligned

        missing_timing = any(line.start is None or line.end is None for line in aligned)
        if missing_timing:
            self._fill_line_timing(aligned, duration)

        for line in aligned:
            self._split_line_units(line)
        return aligned

    def _fill_line_timing(self, lines: list[LyricLine], duration: float) -> None:
        valid = [line for line in lines if line.start is not None and line.end is not None]
        if valid:
            # back-fill missing lines by neighboring anchors
            for index, line in enumerate(lines):
                if line.start is not None and line.end is not None:
                    continue
                prev_end = lines[index - 1].end if index > 0 else 0.0
                next_start = None
                for future in lines[index + 1 :]:
                    if future.start is not None:
                        next_start = future.start
                        break
                if next_start is None:
                    next_start = duration
                span = max(0.5, (next_start - prev_end))
                line.start = prev_end
                line.end = prev_end + span
            return

        segment = duration / max(1, len(lines))
        for index, line in enumerate(lines):
            line.start = index * segment
            line.end = min(duration, (index + 1) * segment)

    def _split_line_units(self, line: LyricLine) -> None:
        if line.start is None or line.end is None or not line.units:
            return
        weights = [max(1, len(unit.text.strip())) for unit in line.units]
        total_weight = sum(weights)
        cursor = line.start
        duration = max(0.001, line.end - line.start)
        for index, unit in enumerate(line.units):
            share = duration * (weights[index] / total_weight)
            unit.start = cursor
            unit.end = cursor + share
            unit.confidence = 0.35
            cursor += share
        if line.units:
            line.units[-1].end = line.end
