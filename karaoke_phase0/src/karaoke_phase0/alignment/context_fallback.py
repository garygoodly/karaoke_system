"""Provenance-aware diagnostic aggregation of current-run CTC groups.

Overlapping windows share audio and are correlated. Agreement is diagnostic,
not an independently calibrated confidence or permission to auto-adopt.
"""
from __future__ import annotations

import math
from statistics import median


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def diagnose_unanchored(shadow, timeline, *, max_spread=0.1, min_observations=2):
    if not isinstance(shadow, dict) or not isinstance(shadow.get('groups'), list):
        raise ValueError('Shadow requires groups')
    lines = timeline.get('lines')
    if not isinstance(lines, list):
        raise ValueError('Timeline requires lines')
    original = {row.get('line_id', i): row for i, row in enumerate(lines)}
    if len(original) != len(lines):
        raise ValueError('Duplicate timeline IDs')
    proxy = {int(i) for i in shadow.get('phonetic_proxy_lines', {})}
    excluded = {int(i): reason for i, reason in shadow.get('excluded_lines', {}).items()}
    entries = {lid: [] for lid in original}
    for group_index, group in enumerate(shadow['groups']):
        if group.get('status') != 'candidate_needs_review':
            continue
        ids = group.get('line_ids', [])
        rows = group.get('lines', [])
        seen = set()
        row_by_id = {}
        for row in rows:
            lid = row.get('line_id')
            if lid in seen:
                raise ValueError(f'Duplicate line {lid} in group {group_index}')
            seen.add(lid)
            row_by_id[lid] = row
        for lid, row in row_by_id.items():
            if lid not in original or lid not in ids:
                continue
            start = row.get('start_seconds')
            if not _finite(start) or not _finite(row.get('original_start')):
                continue
            expected = original[lid].get('start')
            if not _finite(expected) or abs(expected - row['original_start']) > 0.001:
                raise ValueError(f'Stale shadow group for line {lid}')
            prev = row_by_id.get(lid - 1)
            anchored = bool(prev and lid - 1 in ids and _finite(prev.get('end_seconds'))
                            and prev['end_seconds'] <= start)
            entries[lid].append({
                'group_index': group_index, 'group_line_ids': list(ids),
                'start_seconds': round(float(start), 3),
                'predecessor_anchored': anchored,
                'predecessor_end_seconds': round(float(prev['end_seconds']), 3)
                if prev and _finite(prev.get('end_seconds')) else None,
            })
    results = []
    for lid, row in original.items():
        evidence = entries[lid]
        values = sorted(item['start_seconds'] for item in evidence)
        spread = round(values[-1] - values[0], 3) if len(values) > 1 else None
        candidate = round(median(values), 3) if len(values) >= min_observations and spread <= max_spread else None
        prev = original.get(lid - 1)
        prev_end = prev.get('end') if prev else None
        overlap = round(prev_end - candidate, 3) if candidate is not None and _finite(prev_end) else None
        proxy_context = lid in proxy or lid - 1 in proxy
        if lid in excluded and not evidence:
            status = 'excluded_tokenization'
        elif not evidence:
            status = 'no_candidate'
        elif len(evidence) < min_observations:
            status = 'single_group_observation'
        elif candidate is None:
            status = 'group_disagreement'
        elif proxy_context:
            status = 'phonetic_proxy_diagnostic_only'
        elif all(item['predecessor_anchored'] for item in evidence):
            status = 'anchored_consensus_diagnostic_only'
        else:
            status = 'missing_predecessor_anchor_diagnostic_only'
        results.append({
            'line_id': lid, 'observations': values,
            'observation_count': len(evidence), 'group_indices': [e['group_index'] for e in evidence],
            'group_evidence': evidence, 'spread_seconds': spread,
            'candidate_start': candidate, 'previous_original_end': prev_end,
            'overlap_previous_original_seconds': overlap,
            'excluded_reason': excluded.get(lid), 'phonetic_proxy_context': proxy_context,
            'status': status, 'auto_adopt': False,
        })
    return {
        'status': 'diagnostic_only', 'method': 'provenance_aware_ctc_group_aggregation',
        'warning': 'Overlapping groups are correlated, not independent acoustic measurements. No auto-adoption.',
        'lines': results,
    }
