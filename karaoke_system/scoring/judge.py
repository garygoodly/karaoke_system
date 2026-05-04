from __future__ import annotations

from dataclasses import dataclass

from karaoke_system.engine.timeline import Timeline
from karaoke_system.models import JudgeSnapshot, LyricUnit
from karaoke_system.scoring.metrics import score_from_midi
from karaoke_system.scoring.smoothing import RollingAverage


@dataclass(slots=True)
class JudgeState:
    total_score: float = 0.0
    sample_count: int = 0


class PitchJudge:
    def __init__(self, timeline: Timeline, tolerance_cents: float = 50.0) -> None:
        self.timeline = timeline
        self.tolerance_cents = tolerance_cents
        self.state = JudgeState()
        self.smoother = RollingAverage(size=12)

    def evaluate(self, playback_time: float, live_midi: float | None) -> JudgeSnapshot:
        active_line = self.timeline.active_line_at(playback_time)
        active_unit = self.timeline.active_unit_at(playback_time)
        target_midi = self._target_pitch(active_unit, playback_time)
        instant = score_from_midi(live_midi, target_midi, tolerance_cents=self.tolerance_cents)
        smooth = self.smoother.add(instant)
        if active_unit is not None and target_midi is not None and live_midi is not None:
            self.state.total_score += instant
            self.state.sample_count += 1
        average = self.state.total_score / self.state.sample_count if self.state.sample_count else 0.0
        return JudgeSnapshot(
            playback_time=playback_time,
            live_midi=live_midi,
            target_midi=target_midi,
            instant_score=smooth,
            average_score=average,
            active_line_id=active_line.id if active_line else None,
            active_unit_id=active_unit.id if active_unit else None,
        )

    def _target_pitch(self, unit: LyricUnit | None, playback_time: float) -> float | None:
        if unit is None:
            return None
        if unit.pitch_curve:
            return min(
                unit.pitch_curve,
                key=lambda point: abs(point.time - playback_time),
            ).midi
        return unit.pitch_midi
