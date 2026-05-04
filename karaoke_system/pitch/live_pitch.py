from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from karaoke_system.audio.aec import EchoCanceller, PassThroughAEC
from karaoke_system.pitch.note_mapper import hz_to_midi

try:
    import aubio
except Exception:  # pragma: no cover - optional dependency path
    aubio = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency path
    sd = None


class LivePitchTracker:
    def __init__(
        self,
        sample_rate: int = 48000,
        block_size: int = 1024,
        aec: EchoCanceller | None = None,
        on_pitch: Callable[[float | None, float | None], None] | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.aec = aec or PassThroughAEC()
        self.on_pitch = on_pitch
        self._latest_hz: float | None = None
        self._latest_midi: float | None = None
        self._stream = None
        self._lock = threading.Lock()
        self._reference_frame: np.ndarray | None = None
        self._min_hz = 65.4
        self._max_hz = 1046.5
        if aubio is not None:
            self._pitch = aubio.pitch("yin", block_size * 2, block_size, sample_rate)
            self._pitch.set_unit("Hz")
            self._pitch.set_silence(-40)
        else:
            self._pitch = None

    @property
    def latest_midi(self) -> float | None:
        with self._lock:
            return self._latest_midi

    def set_reference_frame(self, frame: np.ndarray | None) -> None:
        self._reference_frame = frame

    def start(self) -> None:
        if sd is None:
            raise RuntimeError("sounddevice is not installed")
        self._stream = sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _estimate_pitch(self, frame: np.ndarray) -> float | None:
        if self._pitch is not None:
            estimate = float(self._pitch(frame.astype(np.float32))[0])
            return estimate if estimate > 0 else None
        return self._estimate_pitch_autocorrelation(frame)

    def _estimate_pitch_autocorrelation(self, frame: np.ndarray) -> float | None:
        if frame.size == 0:
            return None
        signal = np.asarray(frame, dtype=np.float32)
        rms = float(np.sqrt(np.mean(signal * signal)))
        if rms < 0.005:
            return None
        signal = signal - np.mean(signal)
        if not np.any(signal):
            return None
        window = np.hanning(signal.size).astype(np.float32)
        windowed = signal * window
        corr = np.correlate(windowed, windowed, mode="full")
        corr = corr[corr.size // 2 :]
        if corr.size < 4 or corr[0] <= 0:
            return None
        min_lag = max(1, int(self.sample_rate / self._max_hz))
        max_lag = min(corr.size - 1, int(self.sample_rate / self._min_hz))
        if max_lag <= min_lag:
            return None
        search = corr[min_lag : max_lag + 1]
        if search.size == 0:
            return None
        lag = int(np.argmax(search)) + min_lag
        peak = float(corr[lag])
        if peak <= 0.1 * float(corr[0]):
            return None
        return float(self.sample_rate / lag)

    def _callback(self, indata, frames, time_info, status) -> None:  # pragma: no cover - realtime callback
        mono = np.asarray(indata[:, 0], dtype=np.float32)
        processed = self.aec.process(mono, self._reference_frame)
        hz = self._estimate_pitch(processed)
        midi = hz_to_midi(hz)
        with self._lock:
            self._latest_hz = hz
            self._latest_midi = midi
        if self.on_pitch is not None:
            self.on_pitch(hz, midi)
