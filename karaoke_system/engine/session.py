from __future__ import annotations

from karaoke_system.engine.timeline import Timeline
from karaoke_system.models import JudgeSnapshot, LyricLine
from karaoke_system.scoring.judge import PitchJudge


class KaraokeSession:
    def __init__(self, lines: list[LyricLine], tolerance_cents: float = 50.0) -> None:
        self.lines = lines
        self.timeline = Timeline(lines)
        self.judge = PitchJudge(self.timeline, tolerance_cents=tolerance_cents)

    def update(self, playback_time: float, live_midi: float | None) -> JudgeSnapshot:
        return self.judge.evaluate(playback_time, live_midi)
