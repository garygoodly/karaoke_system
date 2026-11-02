"""Offline pitch scoring MVP. Scores only comparable voiced frames; no rhythm score."""
import bisect
import csv
import json
import math
from pathlib import Path


def valid_hz(value):
    try:
        v = float(value)
        return v if math.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def cents_error(reference_hz, user_hz, octave_invariant=False):
    ref, user = valid_hz(reference_hz), valid_hz(user_hz)
    if ref is None or user is None:
        return None
    cents = 1200 * math.log2(user / ref)
    return (cents + 600) % 1200 - 600 if octave_invariant else cents


def score_cents(cents, tolerance=50.0, max_error=300.0):
    """100 within tolerance; linear to 0 at max_error (heuristic, not calibrated)."""
    if tolerance < 0 or max_error <= tolerance:
        raise ValueError('Invalid score thresholds')
    a = abs(cents)
    return 100.0 if a <= tolerance else max(0.0, 100 * (max_error - a) / (max_error - tolerance))


def score_tracks(reference_frames, user_frames, *, offset_seconds=0.0,
                 reference_min_confidence=0.35, user_min_confidence=0.35,
                 tolerance_seconds=0.04, octave_invariant=False):
    """User time is playback time; reference queried at user_time + offset_seconds.

    Input: lists of {'time': seconds, 'hz': Hz, 'periodicity': optional confidence}.
    Missing and low-confidence frames are excluded and reported, never scored zero.
    """
    if not math.isfinite(offset_seconds) or tolerance_seconds < 0:
        raise ValueError('Invalid offset/tolerance')
    refs = sorted(reference_frames, key=lambda x: float(x['time']))
    times = [float(x['time']) for x in refs]
    counts = {'user_frames': len(user_frames), 'matched': 0, 'user_unvoiced': 0,
              'reference_unvoiced': 0, 'no_reference_near_time': 0}
    rows = []
    for user in user_frames:
        t = float(user['time'])
        hz = valid_hz(user.get('hz'))
        conf = user.get('periodicity')
        if hz is None or (conf is not None and float(conf) < user_min_confidence):
            counts['user_unvoiced'] += 1
            continue
        target = t + offset_seconds
        k = bisect.bisect_left(times, target)
        nearby = [refs[j] for j in (k - 1, k) if 0 <= j < len(refs) and abs(times[j] - target) <= tolerance_seconds]
        if not nearby:
            counts['no_reference_near_time'] += 1
            continue
        reference = min(nearby, key=lambda x: abs(float(x['time']) - target))
        ref_hz = valid_hz(reference.get('hz'))
        ref_conf = reference.get('periodicity')
        if ref_hz is None or (ref_conf is not None and float(ref_conf) < reference_min_confidence):
            counts['reference_unvoiced'] += 1
            continue
        err = cents_error(ref_hz, hz, octave_invariant)
        rows.append({'time': t, 'reference_time': float(reference['time']),
                     'reference_hz': ref_hz, 'user_hz': hz,
                     'error_cents': round(err, 3), 'score': round(score_cents(err), 2)})
    counts['matched'] = len(rows)
    counts['coverage'] = len(rows) / len(user_frames) if user_frames else 0.0
    summary = {'status': 'experimental_pitch_only', 'counts': counts,
               'score': round(sum(r['score'] for r in rows) / len(rows), 2) if rows else None,
               'mean_abs_error_cents': round(sum(abs(r['error_cents']) for r in rows) / len(rows), 2) if rows else None,
               'offset_seconds': offset_seconds, 'octave_invariant': octave_invariant,
               'warning': 'Matched voiced frames only. Coverage is separate; do not treat this as a complete singing score.'}
    return {'summary': summary, 'frames': rows}


def load_reference(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    return data['frames']


def load_user_csv(path, *, hz_column='crepe_hz', confidence_column='crepe_periodicity'):
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        return [{'time': float(row['time_s']), 'hz': valid_hz(row.get(hz_column)),
                 'periodicity': valid_hz(row.get(confidence_column)) if row.get(confidence_column) else None}
                for row in csv.DictReader(f)]
