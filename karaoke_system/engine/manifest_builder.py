from __future__ import annotations

from pathlib import Path

from karaoke_system.models import AudioVariant, SongManifest


class ManifestBuilder:
    def __init__(self, song_id: str, title: str, language: str) -> None:
        self.song_id = song_id
        self.title = title
        self.language = language

    def build(
        self,
        video_only_path: str,
        lyrics_path: str,
        original_audio_path: str,
        karaoke_audio_path: str,
    ) -> SongManifest:
        return SongManifest(
            song_id=self.song_id,
            title=self.title,
            language=self.language,
            video_only_path=video_only_path,
            lyrics_path=lyrics_path,
            audio_variants=[
                AudioVariant(kind="original", key_shift=0, audio_path=original_audio_path),
                AudioVariant(kind="karaoke", key_shift=0, audio_path=karaoke_audio_path),
            ],
            default_mode="original",
        )
