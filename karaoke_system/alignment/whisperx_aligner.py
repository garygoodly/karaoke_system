from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import json

from karaoke_system.alignment.base import Aligner
from karaoke_system.alignment.heuristic_aligner import HeuristicAligner
from karaoke_system.exceptions import AlignmentError, ToolUnavailableError
from karaoke_system.models import LyricLine


class WhisperXAligner(Aligner):
    """Optional WhisperX-backed aligner.

    This adapter keeps a working heuristic fallback. If WhisperX is importable,
    it performs a transcription-assisted alignment pass and then projects the
    timing back to the known lyric lines.
    """

    def __init__(self, model_name: str = "small", device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._fallback = HeuristicAligner()

    def align(
        self,
        audio_path: str | Path,
        lines: list[LyricLine],
        language: str,
        output_dir: str | Path,
    ) -> list[LyricLine]:
        rough = self._fallback.align(audio_path=audio_path, lines=lines, language=language, output_dir=output_dir)
        try:
            result = self._run_whisperx(audio_path=audio_path, language=language)
        except ToolUnavailableError:
            return rough
        except Exception as exc:
            raise AlignmentError(f"WhisperX alignment failed: {exc}") from exc
        return self._project_segments_to_known_lyrics(rough, result)

    def _run_whisperx(self, audio_path: str | Path, language: str) -> dict[str, Any]:
        try:
            import whisperx  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise ToolUnavailableError("whisperx is not installed") from exc

        audio = whisperx.load_audio(str(audio_path))
        model = whisperx.load_model(self.model_name, self.device, language=language, compute_type=self.compute_type)
        transcript = model.transcribe(audio)
        align_model, metadata = whisperx.load_align_model(language_code=language, device=self.device)
        aligned = whisperx.align(
            transcript["segments"],
            align_model,
            metadata,
            audio,
            self.device,
            return_char_alignments=False,
        )
        return aligned

    def _project_segments_to_known_lyrics(
        self,
        rough_lines: list[LyricLine],
        whisperx_result: dict[str, Any],
    ) -> list[LyricLine]:
        words: list[dict[str, Any]] = []
        for segment in whisperx_result.get("segments", []):
            words.extend(segment.get("words", []))

        if not words:
            return rough_lines

        projected = deepcopy(rough_lines)
        flat_units = [unit for line in projected for unit in line.units]
        usable_words = [item for item in words if item.get("start") is not None and item.get("end") is not None]
        if not usable_words:
            return projected

        count = min(len(flat_units), len(usable_words))
        for index in range(count):
            unit = flat_units[index]
            word = usable_words[index]
            unit.start = float(word["start"])
            unit.end = float(word["end"])
            unit.confidence = float(word.get("score", 0.8)) if word.get("score") is not None else 0.8

        for line in projected:
            timed_units = [unit for unit in line.units if unit.start is not None and unit.end is not None]
            if timed_units:
                line.start = timed_units[0].start
                line.end = timed_units[-1].end
        return projected
