from __future__ import annotations

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency path
    sd = None


def list_audio_devices() -> list[dict]:
    if sd is None:
        return []
    return list(sd.query_devices())
