from __future__ import annotations

from pathlib import Path

from karaoke_system.audio.ffmpeg_tools import mux_video_audio, render_pitch_shifted_audio
from karaoke_system.models import AudioKind, SongManifest
from karaoke_system.utils.files import ensure_dir


class AudioVariantCache:
    def __init__(self, song_dir: str | Path, manifest: SongManifest, ffmpeg: str = "ffmpeg") -> None:
        self.song_dir = Path(song_dir)
        self.manifest = manifest
        self.ffmpeg = ffmpeg
        self.cache_dir = ensure_dir(self.song_dir / "cache")

    def ensure_playback_media(self, kind: AudioKind, key_shift: int) -> Path:
        audio_variant = self.manifest.find_audio_variant(kind=kind, key_shift=0)
        if audio_variant is None:
            raise FileNotFoundError(f"Audio variant not found for mode={kind}")
        base_audio_path = self.song_dir / audio_variant.audio_path
        if key_shift == 0:
            shifted_audio = base_audio_path
        else:
            shifted_audio = self.cache_dir / f"audio_{kind}_{key_shift:+d}.m4a"
            if not shifted_audio.exists():
                render_pitch_shifted_audio(base_audio_path, shifted_audio, semitones=key_shift, ffmpeg=self.ffmpeg)
        video_path = self.song_dir / self.manifest.video_only_path
        playback_path = self.cache_dir / f"playback_{kind}_{key_shift:+d}.mp4"
        if not playback_path.exists():
            mux_video_audio(video_path, shifted_audio, playback_path, ffmpeg=self.ffmpeg)
        return playback_path
