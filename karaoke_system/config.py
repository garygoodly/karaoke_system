from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass(slots=True)
class BinarySettings:
    ffmpeg: str = os.getenv("KARAOKE_FFMPEG", "ffmpeg")
    ffprobe: str = os.getenv("KARAOKE_FFPROBE", "ffprobe")
    demucs: str = os.getenv("KARAOKE_DEMUCS", "demucs")
    whisperx: str = os.getenv("KARAOKE_WHISPERX", "whisperx")
    mfa: str = os.getenv("KARAOKE_MFA", "mfa")


@dataclass(slots=True)
class RuntimeSettings:
    sample_rate: int = 48000
    input_channels: int = 1
    block_size: int = 1024
    pitch_min_hz: float = 65.4
    pitch_max_hz: float = 1046.5
    judge_tolerance_cents: float = 50.0


@dataclass(slots=True)
class PipelineSettings:
    default_language: str = "ja"
    whisperx_model: str = "small"
    compute_type: str = "int8"
    cache_dir_name: str = "cache"


@dataclass(slots=True)
class AppSettings:
    binaries: BinarySettings = field(default_factory=BinarySettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)


DEFAULT_SETTINGS = AppSettings()
