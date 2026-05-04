from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from karaoke_system.alignment.heuristic_aligner import HeuristicAligner
from karaoke_system.alignment.merger import AlignmentMerger
from karaoke_system.alignment.mfa_aligner import MFAAligner
from karaoke_system.alignment.whisperx_aligner import WhisperXAligner
from karaoke_system.audio.ffmpeg_tools import extract_audio, extract_video_only
from karaoke_system.audio.separator import DemucsSeparator
from karaoke_system.config import DEFAULT_SETTINGS
from karaoke_system.engine.manifest_builder import ManifestBuilder
from karaoke_system.lyrics.providers.local_provider import LocalLyricsProvider
from karaoke_system.lyrics.providers.online_provider import OnlineLyricsProvider
from karaoke_system.models import save_lines
from karaoke_system.pitch.reference_pitch import ReferencePitchExtractor
from karaoke_system.utils.files import copy_file, ensure_dir, relpath


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess a song into a karaoke package")
    parser.add_argument("--input", type=Path, required=True, help="Input MP4 or media file")
    parser.add_argument("--song-id", type=str, required=True)
    parser.add_argument("--title", type=str, required=True)
    parser.add_argument("--language", type=str, choices=["en", "ja", "zh"], default="ja")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lyrics-file", type=Path, default=None)
    parser.add_argument("--lyrics-url", type=str, default=None)
    parser.add_argument("--karaoke-audio", type=Path, default=None, help="Existing instrumental audio")
    parser.add_argument("--use-demucs", action="store_true")
    parser.add_argument("--aligner", choices=["heuristic", "whisperx", "mfa"], default="heuristic")
    parser.add_argument("--whisperx-model", type=str, default=DEFAULT_SETTINGS.pipeline.whisperx_model)
    return parser.parse_args()


def build_provider(args: argparse.Namespace):
    if args.lyrics_file is not None:
        return LocalLyricsProvider(args.lyrics_file)
    if args.lyrics_url is not None:
        return OnlineLyricsProvider(args.lyrics_url)
    raise ValueError("Either --lyrics-file or --lyrics-url is required for subtitle-first alignment")


def build_aligner(args: argparse.Namespace):
    if args.aligner == "whisperx":
        return WhisperXAligner(model_name=args.whisperx_model)
    if args.aligner == "mfa":
        return MFAAligner(binary=DEFAULT_SETTINGS.binaries.mfa)
    return HeuristicAligner()


def main() -> int:
    args = parse_args()
    settings = DEFAULT_SETTINGS

    song_dir = ensure_dir(args.output_dir / args.song_id)
    video_dir = ensure_dir(song_dir / "video")
    audio_dir = ensure_dir(song_dir / "audio")
    work_dir = ensure_dir(song_dir / "work")
    align_dir = ensure_dir(work_dir / "alignment")

    video_only_path = video_dir / "video_only.mp4"
    original_wav_path = work_dir / "original.wav"
    original_audio_path = audio_dir / "original_+0.m4a"

    extract_video_only(args.input, video_only_path, ffmpeg=settings.binaries.ffmpeg)
    extract_audio(args.input, original_wav_path, ffmpeg=settings.binaries.ffmpeg)
    extract_audio(args.input, original_audio_path, ffmpeg=settings.binaries.ffmpeg)

    vocals_path = original_wav_path
    if args.karaoke_audio is not None:
        karaoke_audio_path = copy_file(args.karaoke_audio, audio_dir / "karaoke_+0.m4a")
    elif args.use_demucs:
        separator = DemucsSeparator(binary=settings.binaries.demucs)
        stem_vocals, stem_no_vocals = separator.separate(original_wav_path, work_dir / "demucs")
        vocals_path = copy_file(stem_vocals, work_dir / "vocals.wav")
        karaoke_wav = copy_file(stem_no_vocals, work_dir / "no_vocals.wav")
        extract_audio(karaoke_wav, audio_dir / "karaoke_+0.m4a", ffmpeg=settings.binaries.ffmpeg)
        karaoke_audio_path = audio_dir / "karaoke_+0.m4a"
    else:
        karaoke_audio_path = copy_file(original_audio_path, audio_dir / "karaoke_+0.m4a")

    provider = build_provider(args)
    raw_lines = provider.load(args.language)

    aligner = build_aligner(args)
    aligned_lines = aligner.align(vocals_path, raw_lines, args.language, align_dir)
    aligned_lines = AlignmentMerger().enrich(aligned_lines, args.language)
    aligned_lines = ReferencePitchExtractor().attach(aligned_lines, vocals_path)

    lyrics_path = song_dir / "lyrics.json"
    save_lines(aligned_lines, lyrics_path)

    manifest = ManifestBuilder(args.song_id, args.title, args.language).build(
        video_only_path=relpath(video_only_path, song_dir),
        lyrics_path=relpath(lyrics_path, song_dir),
        original_audio_path=relpath(original_audio_path, song_dir),
        karaoke_audio_path=relpath(karaoke_audio_path, song_dir),
    )
    manifest.save(song_dir / "manifest.json")
    print(f"Created karaoke package: {song_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
