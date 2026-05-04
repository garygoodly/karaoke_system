from __future__ import annotations

import argparse
import ctypes.util
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MODULES = [
    ("PySide6", True),
    ("numpy", True),
    ("librosa", True),
    ("sounddevice", True),
    ("requests", True),
    ("srt", True),
    ("pykakasi", True),
    ("pypinyin", True),
    ("aubio", False),
    ("whisperx", False),
    ("demucs", False),
]

BINARIES = [
    ("ffmpeg", True),
    ("ffprobe", True),
    ("demucs", False),
    ("whisperx", False),
    ("mfa", False),
]


def check_module(name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None)
        return {"ok": True, "version": version}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_binary(name: str) -> dict[str, Any]:
    resolved = shutil.which(name)
    if resolved is None:
        return {"ok": False, "error": "not found in PATH"}
    version = None
    try:
        result = subprocess.run([resolved, "-version"], capture_output=True, text=True, timeout=10)
        line = (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else ""
        version = line.strip()
    except Exception:
        version = None
    return {"ok": True, "path": resolved, "version": version}


def check_rubberband() -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return {"ok": False, "error": "ffmpeg not found"}
    try:
        result = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20)
        text = f"{result.stdout}\n{result.stderr}"
        found = " rubberband " in text or text.strip().endswith("rubberband") or "rubberband" in text
        return {"ok": found, "detail": "rubberband filter found" if found else "rubberband filter missing"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_speex() -> dict[str, Any]:
    lib_name = ctypes.util.find_library("speexdsp") or ctypes.util.find_library("speex")
    if lib_name:
        return {"ok": True, "library": lib_name}
    return {"ok": False, "error": "SpeexDSP library not found"}


def check_song_dir(song_dir: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"exists": song_dir.exists()}
    if not song_dir.exists():
        return report
    manifest = song_dir / "manifest.json"
    lyrics = song_dir / "lyrics.json"
    cache_dir = song_dir / "cache"
    report["manifest"] = manifest.exists()
    report["lyrics"] = lyrics.exists()
    report["cache_dir"] = cache_dir.exists()
    report["playback_cache_files"] = sorted([item.name for item in cache_dir.glob("playback_*.mp4")]) if cache_dir.exists() else []
    return report


def build_report(song_dir: Path | None) -> dict[str, Any]:
    modules = {name: check_module(name) for name, _ in MODULES}
    binaries = {name: check_binary(name) for name, _ in BINARIES}
    report: dict[str, Any] = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "cwd": os.getcwd(),
        },
        "modules": modules,
        "binaries": binaries,
        "features": {
            "rubberband_filter": check_rubberband(),
            "speexdsp": check_speex(),
        },
    }
    if song_dir is not None:
        report["song_dir"] = check_song_dir(song_dir)
    return report


def print_human(report: dict[str, Any]) -> None:
    print("=== Karaoke System Doctor ===")
    print(f"Platform: {report['platform']['system']} {report['platform']['release']}")
    print(f"Python:   {report['platform']['python']} ({report['platform']['python_executable']})")
    print()
    print("Modules:")
    for name, status in report["modules"].items():
        state = "OK" if status["ok"] else "MISSING"
        detail = status.get("version") or status.get("error") or ""
        print(f"  - {name:<12} {state:<8} {detail}")
    print()
    print("Binaries:")
    for name, status in report["binaries"].items():
        state = "OK" if status["ok"] else "MISSING"
        detail = status.get("path") or status.get("error") or ""
        print(f"  - {name:<12} {state:<8} {detail}")
    print()
    print("Features:")
    for name, status in report["features"].items():
        state = "OK" if status["ok"] else "LIMITED"
        detail = status.get("detail") or status.get("library") or status.get("error") or ""
        print(f"  - {name:<18} {state:<8} {detail}")
    if "song_dir" in report:
        print()
        print("Song directory:")
        for key, value in report["song_dir"].items():
            print(f"  - {key}: {value}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Karaoke System runtime dependencies")
    parser.add_argument("--song-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.song_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
