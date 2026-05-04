from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
import threading
from typing import Protocol

import numpy as np


class EchoCanceller(Protocol):
    def process(self, mic_frame: np.ndarray, speaker_frame: np.ndarray | None = None) -> np.ndarray:
        ...


@dataclass(slots=True)
class PassThroughAEC:
    def process(self, mic_frame: np.ndarray, speaker_frame: np.ndarray | None = None) -> np.ndarray:
        return mic_frame.astype(np.float32, copy=False)


class SpeexDAEC:
    """Minimal SpeexDSP echo canceller wrapper.

    This is intentionally small and focused. For production use, calibrate frame
    size, delay, and playback capture routing on the target device.
    """

    def __init__(self, frame_size: int = 1024, sample_rate: int = 48000, filter_length_ms: int = 250) -> None:
        lib_name = ctypes.util.find_library("speexdsp") or ctypes.util.find_library("speex")
        if not lib_name:
            raise OSError("SpeexDSP shared library was not found")
        self.lib = ctypes.cdll.LoadLibrary(lib_name)
        self.frame_size = frame_size
        self.sample_rate = sample_rate
        self.filter_length = max(frame_size, int(sample_rate * filter_length_ms / 1000))
        self.state = self.lib.speex_echo_state_init(frame_size, self.filter_length)
        self.lib.speex_echo_ctl(self.state, 24, ctypes.byref(ctypes.c_int(sample_rate)))
        self._lock = threading.Lock()

    def process(self, mic_frame: np.ndarray, speaker_frame: np.ndarray | None = None) -> np.ndarray:
        mic = np.clip(mic_frame, -1.0, 1.0)
        ref = np.zeros_like(mic) if speaker_frame is None else np.clip(speaker_frame, -1.0, 1.0)
        mic_i16 = (mic * 32767.0).astype(np.int16, copy=False)
        ref_i16 = (ref * 32767.0).astype(np.int16, copy=False)
        out_i16 = np.zeros_like(mic_i16)
        with self._lock:
            self.lib.speex_echo_cancellation(
                self.state,
                mic_i16.ctypes.data_as(ctypes.POINTER(ctypes.c_short)),
                ref_i16.ctypes.data_as(ctypes.POINTER(ctypes.c_short)),
                out_i16.ctypes.data_as(ctypes.POINTER(ctypes.c_short)),
            )
        return out_i16.astype(np.float32) / 32768.0

    def __del__(self) -> None:  # pragma: no cover - destructor path
        try:
            if getattr(self, "state", None):
                self.lib.speex_echo_state_destroy(self.state)
        except Exception:
            pass
