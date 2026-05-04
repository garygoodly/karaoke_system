from __future__ import annotations

from karaoke_system.pitch.note_mapper import cents_distance


def score_from_midi(live_midi: float | None, target_midi: float | None, tolerance_cents: float = 50.0) -> float:
    distance = cents_distance(live_midi, target_midi)
    if distance is None:
        return 0.0
    error = abs(distance)
    if error <= tolerance_cents:
        return 100.0
    if error >= 300.0:
        return 0.0
    return max(0.0, 100.0 * (1.0 - (error - tolerance_cents) / (300.0 - tolerance_cents)))
