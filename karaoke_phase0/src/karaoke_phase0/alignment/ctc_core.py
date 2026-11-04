"""Shared pure CTC algorithms for offline karaoke experiments.

No model downloads, audio I/O, GUI, or timeline mutation occurs here.
This phase deliberately preserves the existing numerical implementations.
"""
from statistics import median
import numpy as np

def ctc_subsequence_viterbi(log_probs, token_ids, blank_id):
    """Best single occurrence of a token sequence in a CTC frame sequence.

    O(T*L) time, O(L) working memory. Returns start/end frame (end exclusive),
    mean log score per consumed frame, or None. Allows arbitrary prefix/suffix.
    Not a calibrated confidence score. Repeated symbols require a blank.
    """
    x = np.asarray(log_probs, dtype=np.float64)
    ids = list(token_ids)
    if x.ndim != 2 or not ids or not np.isfinite(x).all():
        raise ValueError('Expected finite [frames,vocabulary] log probabilities and nonempty tokens')
    if blank_id in ids or min(ids) < 0 or max(ids + [blank_id]) >= x.shape[1]:
        raise ValueError('Invalid CTC token or blank id')
    states = [blank_id]
    for t in ids:
        states.extend((t, blank_id))
    n = len(states)
    prev = np.full(n, -np.inf)
    prev_start = np.full(n, -1, dtype=int)
    best = None
    for frame, row in enumerate(x):
        cur = np.full(n, -np.inf)
        starts = np.full(n, -1, dtype=int)
        # Free start at any frame. No penalty for leading audio.
        for s in range(n):
            opts = []
            if s == 0:
                opts.append((0.0, frame))
            if s == 1:
                opts.append((0.0, frame))
            if np.isfinite(prev[s]):
                opts.append((prev[s], int(prev_start[s])))
            if s >= 1 and np.isfinite(prev[s-1]):
                opts.append((prev[s-1], int(prev_start[s-1])))
            if s >= 2 and states[s] != blank_id and states[s] != states[s-2] and np.isfinite(prev[s-2]):
                opts.append((prev[s-2], int(prev_start[s-2])))
            if opts:
                val, start = max(opts, key=lambda z:z[0])
                cur[s] = val + row[states[s]]
                starts[s] = start
        for s in (n-2, n-1):
            if np.isfinite(cur[s]):
                start = int(starts[s]); end = frame + 1
                # Total likelihood includes sequence duration, so report separately.
                val = float(cur[s]); normalized = val / (end - start)
                if best is None or val > best['total_log_probability']:
                    best = {'start_frame':start, 'end_frame':end,
                            'total_log_probability':val, 'mean_log_probability':normalized}
        prev, prev_start = cur, starts
    return best


def tokenize_exact(text, tokenizer):
    """Fail closed: no UNK and exact round-trip required for model-specific text."""
    clean = ''.join(c for c in text if not c.isspace())
    if not clean:
        raise ValueError('Empty lyric query')
    ids = tokenizer(clean, add_special_tokens=False).input_ids
    if not ids or (tokenizer.unk_token_id is not None and tokenizer.unk_token_id in ids):
        raise ValueError('Model tokenizer cannot represent the supplied Chinese text')
    decoded = tokenizer.decode(ids, skip_special_tokens=True).replace(' ', '')
    if decoded != clean:
        raise ValueError(f'Tokenizer round-trip mismatch: {decoded!r} != {clean!r}')
    return ids


def joint_viterbi(log_probs, token_ids, blank_id, split_index):
    """Best CTC subsequence with token-level traceback; O(T*L) time and memory.

    Token start/end times are approximated by the first/last frames assigned to
    the corresponding CTC token state; blank frames are not assigned to tokens.
    """
    x = np.asarray(log_probs, dtype=np.float64)
    ids = list(token_ids)
    if x.ndim != 2 or not np.isfinite(x).all() or not 0 < split_index < len(ids):
        raise ValueError('Invalid CTC logits or line boundary')
    if blank_id in ids or min(ids) < 0 or max(ids + [blank_id]) >= x.shape[1]:
        raise ValueError('Invalid token/blank ids')
    states = [blank_id]
    for token in ids:
        states.extend((token, blank_id))
    n = len(states)
    tcount = len(x)
    prev = np.full(n, -np.inf)
    back = np.full((tcount, n), -1, dtype=np.int32)
    best_score = -np.inf
    best_final = None
    for t, row in enumerate(x):
        cur = np.full(n, -np.inf)
        for s, token in enumerate(states):
            opts = []
            if s in (0, 1):
                opts.append((0.0, -1))  # free subsequence start
            if np.isfinite(prev[s]):
                opts.append((prev[s], s))
            if s >= 1 and np.isfinite(prev[s-1]):
                opts.append((prev[s-1], s-1))
            if s >= 2 and token != blank_id and token != states[s-2] and np.isfinite(prev[s-2]):
                opts.append((prev[s-2], s-2))
            if opts:
                value, origin = max(opts, key=lambda z: z[0])
                cur[s] = value + row[token]
                back[t, s] = origin
        for s in (n-2, n-1):
            if cur[s] > best_score:
                best_score = float(cur[s]); best_final = (t, s)
        prev = cur
    if best_final is None:
        return None
    token_frames = [[] for _ in ids]
    t, s = best_final
    last_frame = t
    while t >= 0 and s >= 0:
        if s % 2 == 1:
            token_frames[(s-1)//2].append(t)
        origin = int(back[t, s]); s = origin; t -= 1
    if any(not frames for frames in token_frames):
        return None
    spans = [{'start_frame':min(frames), 'end_frame':max(frames)+1} for frames in token_frames]
    return {'start_frame':min(sp['start_frame'] for sp in spans),
            'end_frame':last_frame+1,
            'total_log_probability':best_score,
            'token_spans':spans,
            'line1_last_token':spans[split_index-1],
            'line2_first_token':spans[split_index]}


def make_groups(lines, supported, size=3, max_gap=18.0):
    """Contiguous, nonoverlapping groups; split at unsupported lines or long gaps."""
    if not 2 <= size <= 4 or max_gap <= 0:
        raise ValueError('Invalid grouping parameters')
    groups, pending = [], []
    def flush():
        if pending:
            groups.append(pending.copy())
            pending.clear()
    for i, line in enumerate(lines):
        if i not in supported:
            flush()
            continue
        if pending and (float(line['start']) - float(lines[pending[-1]]['start']) > max_gap):
            flush()
        pending.append(i)
        if len(pending) == size:
            flush()
    flush()
    return groups


def make_sliding_groups(lines, supported, size=3, max_gap=18.0):
    """Stride-one windows plus edge pairs so each line in runs >=3 has >=2 contexts.

    A run of 1 or 2 cannot provide two independent distinct contexts without
    duplicating evidence; report this limitation rather than manufacturing it.
    """
    if not 2 <= size <= 4 or max_gap <= 0:
        raise ValueError('Invalid group settings')
    runs, run = [], []
    for i, line in enumerate(lines):
        if i not in supported or (run and float(line['start']) - float(lines[run[-1]]['start']) > max_gap):
            if run:
                runs.append(run)
            run = []
        if i in supported:
            run.append(i)
    if run:
        runs.append(run)
    groups = []
    for run in runs:
        n = len(run)
        if n <= 2:
            groups.append(run)
            continue
        width = min(size, n)
        windows = [run[i:i+width] for i in range(n-width+1)]
        # Add different-length boundary contexts, not duplicate windows.
        if width > 2:
            windows.extend([run[:2], run[-2:]])
        for window in windows:
            if window not in groups:
                groups.append(window)
    return groups


def summarize_consensus(groups, lines, tolerance=0.5):
    """Separate planned coverage, successful observations and failed groups."""
    from statistics import median
    planned = {i: 0 for i in range(len(lines))}
    observations = {i: [] for i in range(len(lines))}
    failures = {i: [] for i in range(len(lines))}
    for group in groups:
        for i in group.get('line_ids', []):
            planned[i] += 1
            if group.get('status') != 'candidate_needs_review':
                failures[i].append(group.get('status', 'unknown'))
        if group.get('status') == 'candidate_needs_review':
            for item in group.get('lines', []):
                observations[item['line_id']].append(float(item['start_seconds']))
    result = []
    for i, line in enumerate(lines):
        values = sorted(observations[i])
        spread = values[-1]-values[0] if len(values) >= 2 else None
        result.append({'line_id': i, 'original_start': line['start'],
                       'observations': [round(v, 3) for v in values],
                       'planned_observations': planned[i],
                       'observation_count': len(values),
                       'failed_group_statuses': failures[i],
                       'median_start': round(median(values), 3) if values else None,
                       'spread_seconds': round(spread, 3) if spread is not None else None,
                       'status': ('no_candidate' if not values else
                                  'single_observation_needs_review' if len(values) == 1 else
                                  'consistent_needs_review' if spread <= tolerance else
                                  'disagreement_needs_review')})
    return result


def boundaries(token_spans, lengths, frame_to_seconds):
    """Per-line start/end from the first/last nonblank token frames."""
    if not lengths or any(n <= 0 for n in lengths) or sum(lengths) != len(token_spans):
        raise ValueError('Invalid token partition')
    out, pos = [], 0
    for length in lengths:
        part = token_spans[pos:pos+length]
        out.append({'start_seconds': round(frame_to_seconds(part[0]['start_frame']), 3),
                    'end_seconds': round(frame_to_seconds(part[-1]['end_frame']), 3)})
        pos += length
    return out


