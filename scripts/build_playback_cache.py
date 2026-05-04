from __future__ import annotations

import argparse
from pathlib import Path

from karaoke_system.audio.keyshift import AudioVariantCache
from karaoke_system.models import SongManifest


MODES = ["original", "karaoke"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cached playback MP4 files for a song package")
    parser.add_argument("--song-dir", type=Path, required=True)
    parser.add_argument("--keys", type=int, nargs="*", default=[0], help="Semitone shifts to pre-render")
    parser.add_argument("--modes", nargs="*", default=MODES, choices=MODES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    song_dir = args.song_dir.resolve()
    manifest = SongManifest.load(song_dir / "manifest.json")
    cache = AudioVariantCache(song_dir=song_dir, manifest=manifest)
    for mode in args.modes:
        for key in args.keys:
            path = cache.ensure_playback_media(kind=mode, key_shift=key)
            print(f"Built: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
