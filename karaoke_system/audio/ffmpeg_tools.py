from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess

from karaoke_system.exceptions import ToolUnavailableError
from karaoke_system.utils.files import ensure_dir


def _check_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise ToolUnavailableError(f"Required binary not found in PATH: {binary}")


def run_ffmpeg(command: list[str]) -> None:
    _check_binary(command[0])
    subprocess.run(command, check=True)


def probe_duration(media_path: str | Path, ffprobe: str = "ffprobe") -> float:
    _check_binary(ffprobe)
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(media_path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    return float(payload["format"]["duration"])


def extract_video_only(input_path: str | Path, output_path: str | Path, ffmpeg: str = "ffmpeg") -> Path:
    ensure_dir(Path(output_path).parent)
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(input_path),
            "-an",
            "-c:v",
            "copy",
            str(output_path),
        ]
    )
    return Path(output_path)


def extract_audio(input_path: str | Path, output_path: str | Path, ffmpeg: str = "ffmpeg") -> Path:
    ensure_dir(Path(output_path).parent)
    suffix = Path(output_path).suffix.lower()
    codec_args = ["-c:a", "aac", "-b:a", "256k"] if suffix in {".m4a", ".aac"} else ["-acodec", "pcm_s16le"]
    run_ffmpeg([
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        *codec_args,
        str(output_path),
    ])
    return Path(output_path)


def mux_video_audio(video_path: str | Path, audio_path: str | Path, output_path: str | Path, ffmpeg: str = "ffmpeg") -> Path:
    ensure_dir(Path(output_path).parent)
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )
    return Path(output_path)


def render_pitch_shifted_audio(
    input_audio: str | Path,
    output_audio: str | Path,
    semitones: int,
    ffmpeg: str = "ffmpeg",
) -> Path:
    ensure_dir(Path(output_audio).parent)
    pitch_ratio = 2 ** (semitones / 12)
    filter_expr = f"rubberband=pitch={pitch_ratio}"
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(input_audio),
            "-vn",
            "-af",
            filter_expr,
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            str(output_audio),
        ]
    )
    return Path(output_audio)
