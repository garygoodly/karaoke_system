"""Diagnose experimental Karaoke pitch scoring without changing its scoring engine."""
import argparse
import bisect
import csv
import json
import math
from collections import Counter
from pathlib import Path


def number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def evaluate(reference, user, threshold=0.35, use_capture_time=True):
    refs = sorted(reference, key=lambda x: float(x['time']))
    times = [float(r['time']) for r in refs]
    counts = Counter()
    scored = []
    records = []
    for row in user:
        time = number(row.get('time_s' if use_capture_time else 'playback_time_s'))
        hz = number(row.get('crepe_hz'))
        conf = number(row.get('crepe_periodicity'))
        trusted = str(row.get('offset_trusted', '0')).strip() == '1'
        offset = number(row.get('offset_ms'))
        label = ''
        err = None
        score = None
        ref_hz = None
        if time is None:
            label = 'invalid_time'
        elif hz is None or hz <= 0:
            label = 'user_missing_f0'
        elif conf is not None and conf < threshold:
            label = 'user_low_confidence'
        else:
            k = bisect.bisect_left(times, time)
            near = [j for j in (k - 1, k) if 0 <= j < len(times) and abs(times[j] - time) <= 0.04]
            if not near:
                label = 'no_reference_near_time'
            else:
                ref = refs[min(near, key=lambda j: abs(times[j] - time))]
                ref_hz = number(ref.get('hz'))
                rc = number(ref.get('periodicity'))
                if ref_hz is None or ref_hz <= 0 or (rc is not None and rc < 0.35):
                    label = 'reference_unvoiced'
                else:
                    err = 1200 * math.log2(hz / ref_hz)
                    magnitude = abs(err)
                    score = 100 if magnitude <= 50 else max(0, 100 * (300 - magnitude) / 250)
                    label = ('error_0_50' if magnitude <= 50 else 'error_50_100' if magnitude <= 100
                             else 'error_100_200' if magnitude <= 200 else 'error_200_300' if magnitude <= 300
                             else 'error_300_600' if magnitude <= 600 else 'error_over_600')
                    scored.append(score)
        counts[label] += 1
        records.append({'time_s': row.get('time_s',''), 'playback_time_s': row.get('playback_time_s',''),
                        'offset_ms': offset if offset is not None else '', 'offset_trusted': int(trusted),
                        'user_hz': hz if hz is not None else '', 'user_periodicity': conf if conf is not None else '',
                        'reference_hz': ref_hz if ref_hz is not None else '',
                        'error_cents': round(err,2) if err is not None else '',
                        'score': round(score,2) if score is not None else '', 'classification': label})
    return {'frames': len(user), 'matched': len(scored), 'score': round(sum(scored)/len(scored),2) if scored else None,
            'counts': dict(sorted(counts.items())), 'rows': records}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--user-csv', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    refs = json.loads(a.reference.read_text(encoding='utf-8-sig'))['frames']
    with a.user_csv.open(newline='', encoding='utf-8-sig') as f:
        users = list(csv.DictReader(f))
    thresholds = [0.2, 0.35, 0.5, 0.65]
    scenarios = {f'confidence_{t:g}': evaluate(refs, users, t) for t in thresholds}
    raw = evaluate(refs, users, 0.35, False)
    result = {'status':'diagnostic_only', 'frames':len(users),
              'baseline': {k:v for k,v in scenarios['confidence_0.35'].items() if k != 'rows'},
              'confidence_sensitivity': {k:{'matched':v['matched'],'score':v['score']} for k,v in scenarios.items()},
              'playback_time_without_auto_offset': {'matched':raw['matched'],'score':raw['score']},
              'trusted_offset_frames':sum(str(r.get('offset_trusted','0')).strip()=='1' for r in users),
              'warning':'No ground truth. Comparing offsets or thresholds does not establish accuracy. Score is pitch-only, excludes unmatched frames.'}
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'diagnostics_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    rows = scenarios['confidence_0.35']['rows']
    with (a.output/'diagnostics_frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['classification']);w.writeheader();w.writerows(rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
