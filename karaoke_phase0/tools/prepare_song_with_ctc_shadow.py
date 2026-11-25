"""Run read-only CTC shadow analysis on existing song artifacts.

Use --prepare only when the full song preparation pipeline is explicitly desired.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from karaoke_phase0.alignment.shadow_mode import run_shadow, shadow_paths, DEFAULT_MODEL


def available_shadow_inputs(song):
    audio, timeline, _ = shadow_paths(song)
    if not audio.is_file() or audio.stat().st_size == 0:
        return False, f'Missing or empty audio: {audio}'
    if not timeline.is_file() or timeline.stat().st_size == 0:
        return False, f'Missing or empty timeline: {timeline}'
    try:
        data = json.loads(timeline.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or not isinstance(data.get('lines'), list) or not data['lines']:
            return False, f'Invalid or empty timeline lines: {timeline}'
    except (OSError, ValueError, UnicodeError) as exc:
        return False, f'Cannot read timeline: {exc}'
    return True, None


def execute(song, *, device='cuda', model=DEFAULT_MODEL, shadow_python=None, prepare=False):
    ready, reason = available_shadow_inputs(song)
    preparation = 'reused_existing'
    if not ready and prepare:
        from karaoke_phase0.preparation_pipeline import prepare_song
        report = prepare_song(song, device=device)
        preparation = report.get('status', 'unknown')
        ready, reason = available_shadow_inputs(song)
    if not ready:
        return {'preparation': 'skipped', 'shadow': {'status': 'skipped_missing_inputs', 'reason': reason}}
    return {'preparation': preparation, 'shadow': run_shadow(song, python=shadow_python or sys.executable, model=model, device=device)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--song', required=True)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--model', default=DEFAULT_MODEL)
    parser.add_argument('--shadow-python', help='Interpreter containing CTC dependencies')
    parser.add_argument('--prepare', action='store_true', help='Explicitly run full preparation if inputs are missing')
    args = parser.parse_args()
    result = execute(args.song, device=args.device, model=args.model, shadow_python=args.shadow_python, prepare=args.prepare)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['shadow']['status'] == 'skipped_missing_inputs':
        raise SystemExit(2)
    if result['shadow']['status'] == 'failed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
