"""Report singing coverage separately from experimental pitch accuracy."""
import argparse
import json
from pathlib import Path
from karaoke_phase0.vocal_activity import singing_coverage
from karaoke_phase0.pitch_scoring import load_user_csv, load_reference, score_tracks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--song-folder', type=Path, required=True)
    p.add_argument('--user-csv', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = a.song_folder / 'generated'
    mask = json.loads((root / 'vocal_activity.json').read_text(encoding='utf-8-sig'))
    user = load_user_csv(a.user_csv)
    pitch = score_tracks(load_reference(root / 'reference_pitch.json'), user)['summary']
    coverage = singing_coverage(mask, user)
    result = {'status': 'experimental_singing_coverage', 'pitch_score': pitch['score'],
              'previous_recording_coverage': pitch['counts']['coverage'],
              'singing_coverage': coverage['singing_coverage'], 'counts': coverage,
              'warning': 'Coverage uses estimated reference vocal activity, not verified singing. No overall score.'}
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / 'singing_coverage_summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
