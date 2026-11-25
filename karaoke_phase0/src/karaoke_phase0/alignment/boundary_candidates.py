"""Select preceding-line-anchored CTC token candidates from current shadow groups.

Pure computation; never treats CTC token peaks as validated acoustic onsets.
"""
from __future__ import annotations
from statistics import median
import math


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def from_shadow(shadow, timeline, *, tolerance=0.5, min_gap=0.0):
    """Return v6-compatible rows for every timeline line, using ONLY this shadow run.

    A candidate is anchored only when its immediate predecessor appears in the
    same successful joint CTC group and ends no later than the candidate start.
    """
    if not isinstance(shadow, dict) or not isinstance(shadow.get('groups'), list) or not isinstance(shadow.get('consensus'), list):
        raise ValueError('Shadow must contain groups and consensus arrays')
    lines = timeline.get('lines')
    if not isinstance(lines, list):
        raise ValueError('Timeline requires lines')
    original = {line.get('line_id', i): line.get('start') for i, line in enumerate(lines)}
    if len(original) != len(lines):
        raise ValueError('Duplicate timeline IDs')
    proxy_lines = {int(i) for i in shadow.get('phonetic_proxy_lines', {})}
    observations = {i: [] for i in original}
    for group in shadow['groups']:
        if group.get('status') != 'candidate_needs_review':
            continue
        ids = group.get('line_ids', [])
        rows = {row['line_id']: row for row in group.get('lines', [])}
        if len(rows) != len(group.get('lines', [])):
            raise ValueError('Duplicate group line IDs')
        for i in ids:
            row, prev = rows.get(i), rows.get(i-1)
            if row is None or i not in original or i in proxy_lines or i-1 in proxy_lines:
                continue
            if not _finite(row.get('start_seconds')) or not _finite(row.get('original_start')):
                continue
            if not _finite(original[i]) or abs(row['original_start']-original[i]) > 1e-3:
                raise ValueError(f'Stale shadow group for line {i}')
            if prev is None or i-1 not in ids or not _finite(prev.get('end_seconds')):
                continue
            if not _finite(prev.get('original_start')) or not _finite(original.get(i-1)) or abs(prev['original_start']-original[i-1]) > 1e-3:
                raise ValueError(f'Stale shadow predecessor for line {i-1}')
            if row['start_seconds']-prev['end_seconds'] >= min_gap:
                observations[i].append(round(float(row['start_seconds']), 3))
    result = []
    for i, start in original.items():
        values = sorted(observations[i])
        spread = round(values[-1]-values[0], 3) if len(values) >= 2 else None
        result.append({'line_id': i, 'original_start': start,
                       'token_peak_median': round(median(values), 3) if values else None,
                       'token_peak_spread_seconds': spread,
                       'anchored_count': len(values),
                       'phonetic_proxy_context': i in proxy_lines or i-1 in proxy_lines,
                       'status': 'consistent_boundary_candidate_needs_review' if len(values)>=2 and spread <= tolerance else 'boundary_candidate_needs_review' if values else 'no_boundary_anchored_candidate'})
    return {'status':'diagnostic_only', 'method':'boundary_aware_from_current_shadow', 'lines':result}
