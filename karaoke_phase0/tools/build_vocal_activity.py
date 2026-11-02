"""Build reference vocal activity from existing separated vocals and lyrics timeline."""
import argparse
from pathlib import Path
from karaoke_phase0.vocal_activity import write_mask


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--song-folder', type=Path, required=True)
    a = p.parse_args()
    root = a.song_folder / 'generated'
    vocals = root / 'vocals.wav'
    if not vocals.exists():
        vocals = a.song_folder / 'vocals.wav'
    if not vocals.exists():
        raise FileNotFoundError('vocals.wav not found in generated/ or song folder')
    timeline = root / 'lyrics_timeline.json'
    reference = root / 'reference_pitch.json'
    for path in (timeline, reference):
        if not path.is_file():
            raise FileNotFoundError(path)
    out = root / 'vocal_activity.json'
    result = write_mask(vocals, timeline, reference, out)
    print(f'Wrote {out}; active fraction={result["active_fraction"]:.3f}')


if __name__ == '__main__':
    main()
