"""Conservative, read-only CTC adoption proposals; never alters token timings."""
from __future__ import annotations
import copy
import math


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        return None
    return float(value)


def propose(timeline, quality, *, max_spread=0.10, min_shift=1.0, max_shift=4.0):
    """Make reviewable proposals, not a playable replacement timeline.

    Rules are deliberately uncalibrated and conservative. Source quality rows
    should be computed from v4/v6 reports by quality_evaluation.evaluate().
    """
    if not isinstance(timeline, dict) or not isinstance(timeline.get('lines'), list):
        raise ValueError('Timeline requires a lines array')
    if not isinstance(quality, dict) or not isinstance(quality.get('lines'), list):
        raise ValueError('Quality report requires a lines array')
    if max_spread < 0 or min_shift < 0 or max_shift < min_shift:
        raise ValueError('Invalid selection thresholds')
    rows = quality['lines']
    ids = [r.get('line_id') for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate quality line_id')
    by_id = {r['line_id']: r for r in rows}
    original_lines = timeline['lines']
    line_ids = [line.get('line_id', i) for i, line in enumerate(original_lines)]
    if len(line_ids) != len(set(line_ids)):
        raise ValueError('Duplicate timeline line_id')
    result = []
    for i, line in enumerate(original_lines):
        lid = line_ids[i]
        original = _number(line.get('start'))
        end = _number(line.get('end'))
        q = by_id.get(lid)
        proposal = None
        reason = 'no_quality_record'
        if q is not None:
            peak = _number(q.get('ctc_token_peak'))
            spread = _number(q.get('spread_seconds'))
            count = q.get('anchored_count')
            if peak is None:
                reason = 'missing_ctc_candidate'
            elif original is None or end is None:
                reason = 'invalid_original_timing'
            elif q.get('candidate_source') != 'v6':
                reason = 'not_boundary_anchored'
            elif count is None or isinstance(count, bool) or count < 2:
                reason = 'insufficient_observations'
            elif spread is None or spread > max_spread:
                reason = 'unstable_candidate'
            elif not min_shift <= abs(peak-original) <= max_shift:
                reason = 'shift_outside_review_range'
            elif peak < 0 or peak >= end:
                reason = 'invalid_candidate_interval'
            elif i > 0 and _number(original_lines[i-1].get('start')) is not None and peak <= _number(original_lines[i-1]['start']):
                reason = 'previous_line_order_conflict'
            elif i+1 < len(original_lines) and _number(original_lines[i+1].get('start')) is not None and peak >= _number(original_lines[i+1]['start']):
                reason = 'next_line_order_conflict'
            else:
                proposal = peak
                reason = 'ctc_candidate_for_review'
        # Preserve the source line, including all original token timing and review flags.
        item = copy.deepcopy(line)
        item['ctc_adoption'] = {
            'decision': 'propose_ctc' if proposal is not None else 'keep_original',
            'reason': reason,
            'original_start': original,
            'proposed_start': proposal,
            'candidate_source': q.get('candidate_source') if q else None,
            'candidate_spread_seconds': q.get('spread_seconds') if q else None,
        }
        result.append(item)
    output = copy.deepcopy(timeline)
    output['lines'] = result
    output['ctc_candidate_metadata'] = {
        'status': 'review_only',
        'method': 'controlled_ctc_adoption_v1',
        'warning': 'Original start/end/tokens are unchanged. proposed_start is NOT an approved or playable lyric boundary.',
        'proposed_count': sum(x['ctc_adoption']['decision']=='propose_ctc' for x in result),
        'kept_count': sum(x['ctc_adoption']['decision']=='keep_original' for x in result),
        'thresholds': {'max_spread': max_spread, 'min_shift': min_shift, 'max_shift': max_shift},
    }
    return output
