from __future__ import annotations

from dataclasses import dataclass

from karaoke_system.models import LyricLine, LyricUnit


@dataclass(slots=True)
class LineProgress:
    line: LyricLine | None
    active_unit_index: int | None
    progress: float


class Timeline:
    def __init__(self, lines: list[LyricLine]) -> None:
        self.lines = sorted(lines, key=lambda item: item.start or 0.0)
        self.units = [unit for line in self.lines for unit in line.units if unit.start is not None and unit.end is not None]

    def active_line_at(self, playback_time: float) -> LyricLine | None:
        for line in self.lines:
            if line.start is None or line.end is None:
                continue
            if line.start <= playback_time <= line.end:
                return line
        return None

    def active_unit_at(self, playback_time: float) -> LyricUnit | None:
        for unit in self.units:
            if unit.start is None or unit.end is None:
                continue
            if unit.start <= playback_time <= unit.end:
                return unit
        return None

    def line_progress_at(self, playback_time: float) -> LineProgress:
        line = self.active_line_at(playback_time)
        if line is None:
            return LineProgress(line=None, active_unit_index=None, progress=0.0)
        active_index = None
        progress = 0.0
        for index, unit in enumerate(line.units):
            if unit.start is None or unit.end is None:
                continue
            if unit.start <= playback_time <= unit.end:
                active_index = index
                duration = max(0.001, unit.end - unit.start)
                progress = (playback_time - unit.start) / duration
                break
        return LineProgress(line=line, active_unit_index=active_index, progress=max(0.0, min(1.0, progress)))
