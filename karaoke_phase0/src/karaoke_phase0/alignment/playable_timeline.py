"""Build a reversible, opt-in CTC preview timeline without modifying its inputs."""
from __future__ import annotations

import copy
import math


def number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def build_preview(timeline, candidate, *, max_shift=4.0, tolerance=0.03):
    """Translate a whole line and its token intervals by one offset, or retain original.

    A uniform translation preserves token durations; it does NOT re-align phonemes.
    This is a preview, not an approved per-character alignment.
    """
    if not isinstance(timeline, dict) or not isinstance(candidate, dict):
        raise ValueError('Both inputs must be JSON objects')
    source = timeline.get('lines')
    proposed = candidate.get('lines')
    if not isinstance(source, list) or not isinstance(proposed, list):
        raise ValueError('Both inputs require lines arrays')
    if not number(max_shift) or max_shift <= 0 or not number(tolerance) or tolerance < 0:
        raise ValueError('Invalid thresholds')
    if len(source) != len(proposed):
        raise ValueError('Candidate and original line counts differ')
    ids = lambda lines: [x.get('line_id', i) for i, x in enumerate(lines)]
    if ids(source) != ids(proposed) or len(set(ids(source))) != len(source):
        raise ValueError('Line IDs/order mismatch or duplicates')
    out = copy.deepcopy(timeline)
    output_lines = out['lines']
    accepted = []
    rejected = []
    for i, (orig, prop) in enumerate(zip(source, proposed)):
        lid = orig.get('line_id', i)
        info = prop.get('ctc_adoption') or {}
        if info.get('decision') != 'propose_ctc':
            continue
        start, end, new_start = orig.get('start'), orig.get('end'), info.get('proposed_start')
        reason = None
        if not all(number(x) for x in (start, end, new_start)) or not 0 <= start < end:
            reason = 'invalid_line_interval'
        elif not number(info.get('original_start')) or abs(info['original_start'] - start) > 1e-6:
            reason = 'stale_candidate_original_start'
        elif new_start < 0 or abs(new_start-start) > max_shift:
            reason = 'shift_out_of_bounds'
        elif orig.get('text') != prop.get('text'):
            reason = 'stale_candidate_text'
        else:
            delta = new_start - start
            new_end = end + delta
            tokens = orig.get('tokens')
            if not isinstance(tokens, list) or not tokens:
                reason = 'missing_tokens'
            elif any(not isinstance(t, dict) or not all(number(t.get(k)) for k in ('start','end')) or
                     t['start'] < start-tolerance or t['end'] > end+tolerance or t['end'] <= t['start']
                     for t in tokens):
                reason = 'invalid_token_intervals'
            elif any(tokens[j]['start'] + tolerance < tokens[j-1]['end'] for j in range(1,len(tokens))):
                reason = 'overlapping_tokens'
            elif i and number(output_lines[i-1].get('end')) and new_start < output_lines[i-1]['end']-tolerance:
                reason = 'previous_line_overlap'
            elif i+1 < len(source) and number(source[i+1].get('start')) and new_end > source[i+1]['start']+tolerance:
                reason = 'next_line_overlap'
            else:
                output_lines[i]['start'] = round(new_start, 6)
                output_lines[i]['end'] = round(new_end, 6)
                for tok in output_lines[i]['tokens']:
                    tok['start'] = round(tok['start']+delta, 6)
                    tok['end'] = round(tok['end']+delta, 6)
                output_lines[i]['needs_review'] = True
                accepted.append({'line_id':lid, 'delta_seconds':round(delta,6), 'method':'uniform_translation'})
        if reason:
            rejected.append({'line_id':lid,'reason':reason})
    # No accepted line may newly conflict with any neighbor, including lines shifted later.
    # Revert only the affected accepted line, retaining all original source data.
    for item in list(accepted):
        i = ids(source).index(item['line_id'])
        line = output_lines[i]
        prev = output_lines[i-1] if i else None
        nxt = output_lines[i+1] if i+1 < len(source) else None
        if ((prev and number(prev.get('end')) and line['start'] < prev['end']-tolerance) or
            (nxt and number(nxt.get('start')) and line['end'] > nxt['start']+tolerance)):
            output_lines[i] = copy.deepcopy(source[i])
            accepted.remove(item)
            rejected.append({'line_id':item['line_id'],'reason':'post_shift_neighbor_overlap'})
    out['ctc_preview_metadata'] = {
        'status':'preview_only', 'method':'uniform_line_and_token_translation',
        'warning':'Not phoneme re-alignment. All shifted lines require review; never replace authoritative timeline automatically.',
        'applied_count':len(accepted), 'rejected_count':len(rejected),
        'applied':accepted, 'rejected':rejected,
    }
    # Preserve review-required status regardless of input readiness.
    out['status'] = 'review_required'
    return out
