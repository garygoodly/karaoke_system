from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import requests

from karaoke_system.lyrics.providers.base import LyricsProvider
from karaoke_system.lyrics.providers.local_provider import LocalLyricsProvider


class OnlineLyricsProvider(LyricsProvider):
    """Download lyrics/subtitles from a direct URL and parse them by extension.

    This module intentionally does not hardcode one commercial lyric API.
    In production, swap this provider with your preferred online subtitle source.
    """

    def __init__(self, url: str, timeout: float = 20.0) -> None:
        self.url = url
        self.timeout = timeout

    def load(self, lang: str):
        parsed = urlparse(self.url)
        suffix = Path(parsed.path).suffix.lower() or ".txt"
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / f"lyrics{suffix}"
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            tmp_path.write_bytes(response.content)
            provider = LocalLyricsProvider(tmp_path)
            return provider.load(lang)
