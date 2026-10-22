"""Demucs process configuration and verified stem publication."""
import json
import os
import sys
from pathlib import Path


def demucs_command(song_folder, python=None):
    folder = Path(song_folder).resolve()
    source = folder / 'song.mp3'
    if not source.is_file():
        raise FileNotFoundError(f'Missing song: {source}')
    output = folder / 'generated' / 'demucs_work'
    return [python or sys.executable, '-u', '-m', 'demucs', '-n', 'htdemucs',
            '--two-stems=vocals', '-d', 'cuda', '-o', str(output), str(source)]


def expected_stems(song_folder):
    folder = Path(song_folder).resolve()
    base = folder / 'generated' / 'demucs_work' / 'htdemucs' / 'song'
    return base / 'vocals.wav', base / 'no_vocals.wav'


def publish_stems(song_folder):
    """Validate both files before exposing a completed analysis."""
    folder = Path(song_folder).resolve()
    vocals, instrumental = expected_stems(folder)
    for path in (vocals, instrumental):
        if not path.is_file() or path.stat().st_size <= 44:
            raise RuntimeError(f'Demucs did not produce a valid stem: {path}')
    generated = folder / 'generated'
    generated.mkdir(exist_ok=True)
    # Keep Demucs originals until both published files are in place.
    import shutil
    for source, name in ((vocals, 'vocals.wav'), (instrumental, 'instrumental.wav')):
        target = generated / name
        temp = generated / (name + '.tmp')
        try:
            shutil.copyfile(source, temp)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    metadata_path = generated / 'separation.json'
    temp = generated / 'separation.json.tmp'
    temp.write_text(json.dumps({'model': 'htdemucs', 'device': 'cuda',
                                'vocals': 'vocals.wav', 'instrumental': 'instrumental.wav'}, indent=2), encoding='utf-8')
    os.replace(temp, metadata_path)
    return generated / 'vocals.wav', generated / 'instrumental.wav'
