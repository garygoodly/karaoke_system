"""Read-only, conservative quality checks for experimental CTC word previews.

These are structural heuristics, not estimates of word-timing accuracy.
"""
from __future__ import annotations

import math


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def evaluate_word_preview(original, preview, *, min_duration=0.035,
                          max_duration=3.0, max_overlap=0.10):
    """Evaluate all lines, never mutate source/preview, never auto-approve audio timing.

    Rejected word-preview lines are explicitly fallback, not new CTC successes.
    An acoustic offset cue marked needs_review cannot establish accuracy.
    """
    old = original.get('lines')
    new = preview.get('lines')
    if not isinstance(old, list) or not isinstance(new, list) or len(old) != len(new):
        raise ValueError('Original/preview lines mismatch')
    if min_duration <= 0 or max_duration <= min_duration or max_overlap < 0:
        raise ValueError('Invalid quality thresholds')
    meta = preview.get('ctc_word_preview_metadata') or {}
    applied = {x['line_id']: x for x in meta.get('applied', [])}
    rejected = {x['line_id']: x for x in meta.get('rejected', [])}
    if set(applied) & set(rejected):
        raise ValueError('Line cannot be both applied and rejected')
    rows = []
    for i, (source, candidate) in enumerate(zip(old, new)):
        lid = source.get('line_id', i)
        if candidate.get('line_id', i) != lid or candidate.get('text') != source.get('text'):
            raise ValueError(f'Line identity mismatch at {i}')
        issues = []
        tokens = candidate.get('tokens')
        start, end = candidate.get('start'), candidate.get('end')
        if not _number(start) or not _number(end) or end <= start:
            issues.append('invalid_line_interval')
        if not isinstance(tokens, list) or not tokens:
            issues.append('missing_tokens')
        else:
            last_end = None
            for j, token in enumerate(tokens):
                a, b = token.get('start'), token.get('end')
                if not _number(a) or not _number(b) or b <= a:
                    issues.append('invalid_token_interval')
                    continue
                duration = b-a
                if duration < min_duration - 1e-6:
                    issues.append('short_token')
                if duration > max_duration + 1e-6:
                    issues.append('long_token')
                if last_end is not None and a < last_end - 1e-6:
                    issues.append('nonmonotonic_tokens')
                last_end = b
                if _number(start) and _number(end) and (a < start - 1e-6 or b > end + 1e-6):
                    issues.append('token_outside_line')
            original_tokens = source.get('tokens')
            if (lid in applied and isinstance(original_tokens, list) and
                    len(original_tokens) != len(tokens)):
                issues.append('token_count_changed')
            if lid in applied and isinstance(original_tokens, list):
                if any(a.get('text') != b.get('text') for a,b in zip(original_tokens,tokens)):
                    issues.append('token_text_changed')
        if i + 1 < len(new) and _number(end) and _number(new[i+1].get('start')):
            if end - new[i+1]['start'] > max_overlap + 1e-6:
                issues.append('next_line_overlap')
        if lid in applied:
            cue = applied[lid].get('final_offset_cue')
            if cue and cue.get('status') == 'possible_vocal_offset_needs_review':
                issues.append('unverified_vocal_offset')
            status = 'review_required' if issues else 'structurally_valid_unverified'
            source_type = 'ctc_word_preview'
        elif lid in rejected:
            status = 'fallback_original'
            source_type = 'original'
            if candidate != source:
                issues.append('rejected_line_not_restored')
                status = 'review_required'
        else:
            status = 'unchanged_original'
            source_type = 'original'
        rows.append({'line_id': lid, 'source': source_type, 'status': status,
                     'issues': sorted(set(issues))})
    return {
        'status': 'diagnostic_only',
        'method': 'ctc_word_quality_v1',
        'warning': 'Structural checks do not establish acoustic word-boundary accuracy. No timeline changed.',
        'thresholds': {'min_duration': min_duration, 'max_duration': max_duration,
                       'max_overlap': max_overlap},
        'summary': {
            'lines': len(rows), 'applied_lines': len(applied), 'fallback_lines': len(rejected),
            'structurally_valid_unverified': sum(x['status']=='structurally_valid_unverified' for x in rows),
            'review_required': sum(x['status']=='review_required' for x in rows),
            'unchanged_original': sum(x['status']=='unchanged_original' for x in rows),
        },
        'lines': rows,
    }
