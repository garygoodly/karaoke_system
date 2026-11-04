"""Read-only boundary-aware CTC candidate selection from v4 and v5 reports.

This does not estimate acoustic onset. A CTC nonblank token span is NOT a
phonetic onset interval. The output is a review proposal, not a timeline edit.
"""
import argparse
import json
from pathlib import Path
from statistics import median


def select_boundary_candidates(consensus, groups, tolerance=0.5, min_gap=0.0):
    if tolerance < 0 or min_gap < 0:
        raise ValueError('tolerance and min_gap must be nonnegative')
    group_by_line = {}
    for group in groups:
        if group.get('status') != 'candidate_needs_review':
            continue
        ids = group.get('line_ids', [])
        rows = {row['line_id']: row for row in group.get('lines', [])}
        for line_id in ids:
            if line_id not in rows:
                continue
            row = rows[line_id]
            start = float(row['start_seconds'])
            prev_id = line_id - 1
            prev = rows.get(prev_id) if prev_id in ids else None
            prev_end = float(prev['end_seconds']) if prev else None
            gap = start - prev_end if prev_end is not None else None
            group_by_line.setdefault(line_id, []).append({
                'group': list(ids), 'token_peak_start': round(start, 3),
                'previous_last_token_end': round(prev_end, 3) if prev_end is not None else None,
                'gap_seconds': round(gap, 3) if gap is not None else None,
                'has_previous_context': prev is not None,
                'passes_order': gap is not None and gap >= min_gap,
            })
    result = []
    for item in consensus:
        line_id = item['line_id']
        observations = group_by_line.get(line_id, [])
        constrained = [x for x in observations if x['passes_order']]
        rejected = [x for x in observations if x['has_previous_context'] and not x['passes_order']]
        unanchored = [x for x in observations if not x['has_previous_context']]
        values = sorted(x['token_peak_start'] for x in constrained)
        spread = round(values[-1] - values[0], 3) if len(values) >= 2 else None
        if len(values) >= 2 and spread <= tolerance:
            status = 'consistent_boundary_candidate_needs_review'
        elif len(values) >= 2:
            status = 'boundary_disagreement_needs_review'
        elif len(values) == 1:
            status = 'single_boundary_candidate_needs_review'
        else:
            status = 'no_boundary_anchored_candidate'
        result.append({
            'line_id': line_id, 'original_start': item.get('original_start'),
            'token_peak_median': round(median(values), 3) if values else None,
            'token_peak_spread_seconds': spread,
            'estimated_acoustic_onset': None,
            'anchored_count': len(values), 'unanchored_count': len(unanchored),
            'order_rejected_count': len(rejected), 'status': status,
            'observations': observations,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v4', required=True, help='ctc_sliding_v4.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--line-ids', type=int, nargs='*', default=[2, 5, 24])
    parser.add_argument('--tolerance', type=float, default=0.5)
    parser.add_argument('--min-gap', type=float, default=0.0)
    args = parser.parse_args()
    if args.tolerance < 0 or args.min_gap < 0:
        parser.error('tolerance and min-gap must be nonnegative')
    report = json.loads(Path(args.v4).read_text(encoding='utf-8'))
    if not isinstance(report.get('groups'), list) or not isinstance(report.get('consensus'), list):
        parser.error('Expected v4 report containing groups and consensus arrays')
    decisions = select_boundary_candidates(report['consensus'], report['groups'], args.tolerance, args.min_gap)
    selected = set(args.line_ids)
    output = {
        'status': 'diagnostic_only', 'method': 'boundary_aware_ctc_v6',
        'warning': 'Uses v4 CTC token boundaries, not true acoustic onsets. All proposed times need listening. Does not modify source timeline.',
        'source_report': str(args.v4),
        'lines': [row for row in decisions if row['line_id'] in selected],
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    for row in output['lines']:
        print('Line {}: peak={}, anchored={}, spread={}, status={}'.format(row['line_id'], row['token_peak_median'], row['anchored_count'], row['token_peak_spread_seconds'], row['status']))
    print('Report:', path)


if __name__ == '__main__':
    main()
