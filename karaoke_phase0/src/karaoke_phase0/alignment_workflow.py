"""Separate, testable alignment orchestration (heavy models loaded only in worker)."""
import json
from pathlib import Path
from .core import parse_lyrics
from .known_lyrics_alignment import align_known_lyrics


def lyrics_path(folder):
    folder = Path(folder)
    matches = [p for p in (folder/'lyrics.txt', folder/'lyrics.lrc') if p.is_file()]
    if len(matches) != 1:
        raise ValueError('Expected exactly one lyrics.txt or lyrics.lrc in song folder')
    return matches[0]


def align_song(folder, device='cuda', language='zh', model_name=None):
    folder = Path(folder)
    vocals = folder/'generated'/'vocals.wav'
    if not vocals.is_file():
        raise FileNotFoundError('Run Demucs separation first: generated/vocals.wav missing')
    lines = parse_lyrics(lyrics_path(folder))
    if not lines:
        raise ValueError('Lyrics file contains no singing lines')
    output = folder/'generated'/'lyrics_timeline.json'
    return align_known_lyrics(vocals, lines, output, language=language, device=device, model_name=model_name)


def read_timeline(folder):
    path = Path(folder)/'generated'/'lyrics_timeline.json'
    return json.loads(path.read_text(encoding='utf-8'))
