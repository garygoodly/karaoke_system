from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from karaoke_system.exceptions import ToolUnavailableError
from karaoke_system.utils.files import ensure_dir


class DemucsSeparator:
    def __init__(self, binary: str = "demucs") -> None:
        self.binary = binary

    def separate(self, input_audio: str | Path, output_dir: str | Path) -> tuple[Path, Path]:
        if shutil.which(self.binary) is None:
            raise ToolUnavailableError("demucs is not installed")
        output_dir = ensure_dir(output_dir)
        subprocess.run(
            [
                self.binary,
                "--two-stems",
                "vocals",
                "-o",
                str(output_dir),
                str(input_audio),
            ],
            check=True,
        )
        song_name = Path(input_audio).stem
        base = output_dir / "htdemucs" / song_name
        vocals = base / "vocals.wav"
        no_vocals = base / "no_vocals.wav"
        if not vocals.exists() or not no_vocals.exists():
            raise FileNotFoundError("Demucs did not create the expected stem files")
        return vocals, no_vocals
