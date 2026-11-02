"""Offline diagnostic: user CSV must share song timeline with reference JSON."""
import argparse
import csv
import json
from pathlib import Path
from karaoke_phase0.pitch_scoring import load_reference, load_user_csv, score_tracks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--user-csv', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--offset-ms', type=float, default=0)
    p.add_argument('--octave-invariant', action='store_true')
    p.add_argument('--hz-column', default='crepe_hz')
    a = p.parse_args()
    result = score_tracks(load_reference(a.reference), load_user_csv(a.user_csv, hz_column=a.hz_column,
                          confidence_column='crepe_periodicity' if a.hz_column == 'crepe_hz' else ''),
                          offset_seconds=a.offset_ms / 1000, octave_invariant=a.octave_invariant)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output/'score_summary.json').write_text(json.dumps(result['summary'], indent=2, ensure_ascii=False), encoding='utf-8')
    with (a.output/'score_frames.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['time', 'reference_time', 'reference_hz', 'user_hz', 'error_cents', 'score'])
        writer.writeheader(); writer.writerows(result['frames'])
    print(json.dumps(result['summary'], indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
