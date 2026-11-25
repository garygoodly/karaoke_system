"""Conservative word/character timing preview from Joint CTC token anchors.

The anchors are CTC nonblank token times, not acoustic onset ground truth.
No original files are changed. Unreliable lines retain their original tokens.
"""
from __future__ import annotations
import copy
import math
from statistics import median


def _valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _anchors(shadow, line_id):
    observations = []
    for group in shadow.get('groups', []):
        if group.get('status') != 'candidate_needs_review':
            continue
        for line in group.get('lines', []):
            if line.get('line_id') == line_id and isinstance(line.get('character_anchors'), list):
                observations.append(line['character_anchors'])
    return observations


def inspect_character_anchors(line, observations, *, max_duration=3.0):
    """Explain suspicious token gaps without inventing phonetic boundaries.

    Each row identifies the displayed character that midpoint reconstruction
    would stretch, and the adjacent CTC anchor gaps responsible for it.
    """
    tokens = line.get('tokens') or []
    n = len(tokens)
    if n == 0 or not observations or any(len(obs) != n or any(not _valid(x) for x in obs) for obs in observations):
        return {'status': 'unavailable', 'reason': 'missing_or_mismatched_anchors'}
    centers = [median(obs[i] for obs in observations) for i in range(n)]
    start, end = line.get('start'), line.get('end')
    if not _valid(start) or not _valid(end) or end <= start:
        return {'status': 'unavailable', 'reason': 'invalid_line_interval'}
    boundaries = [float(start)] + [(centers[i] + centers[i+1]) / 2 for i in range(n-1)] + [float(end)]
    anomalies = []
    for i, token in enumerate(tokens):
        duration = boundaries[i+1] - boundaries[i]
        if duration <= max_duration:
            continue
        anomalies.append({
            'token_index': i,
            'character': token.get('text'),
            'estimated_start': round(boundaries[i], 3),
            'estimated_end': round(boundaries[i+1], 3),
            'estimated_duration_seconds': round(duration, 3),
            'previous_anchor_gap_seconds': round(centers[i] - centers[i-1], 3) if i else None,
            'next_anchor_gap_seconds': round(centers[i+1] - centers[i], 3) if i+1 < n else None,
            'interpretation': 'ctc_anchor_gap_not_verified_singing_duration',
        })
    return {
        'status': 'long_intervals_found' if anomalies else 'no_long_intervals',
        'observation_count': len(observations),
        'anomalies': anomalies,
    }



def estimate_final_vocal_offset(audio_path, anchor_seconds, line_end_seconds, *,
                                frame_seconds=0.02, min_silence_seconds=0.30):
    """Find a sustained low-energy tail after the last CTC anchor.

    Diagnostic only: a Demucs vocal stem may contain residual instruments or
    lose quiet singing. Silence is evidence for a possible offset, not proof.
    Return None if there is no unambiguous sustained quiet tail.
    """
    from pathlib import Path
    import numpy as np
    import soundfile as sf

    if not _valid(anchor_seconds) or not _valid(line_end_seconds) or line_end_seconds <= anchor_seconds:
        return None
    with sf.SoundFile(str(Path(audio_path))) as audio:
        rate = audio.samplerate
        left = max(0, int((anchor_seconds - 0.15) * rate))
        right = min(len(audio), int((line_end_seconds + 0.02) * rate))
        if right <= left:
            return None
        audio.seek(left)
        data = audio.read(right - left, dtype='float32', always_2d=True)
    mono = np.mean(data, axis=1)
    hop = max(1, int(frame_seconds * rate))
    count = len(mono) // hop
    if count < 10:
        return None
    frames = mono[:count * hop].reshape(count, hop)
    rms = np.sqrt(np.mean(frames.astype('float64') ** 2, axis=1))
    frame_times = left / rate + (np.arange(count) + 0.5) * hop / rate
    active = rms[(frame_times >= anchor_seconds - 0.15) & (frame_times <= min(line_end_seconds, anchor_seconds + 1.0))]
    if not len(active) or float(np.max(active)) < 0.0005:
        return None
    threshold = max(0.0005, float(np.percentile(active, 85)) * 0.12)
    # Require the *end* of the interval to be quiet, not an internal pause.
    tail = np.flatnonzero((frame_times >= anchor_seconds) & (frame_times <= line_end_seconds))
    if len(tail) == 0:
        return None
    last = int(tail[-1])
    if rms[last] > threshold:
        return None
    first = last
    while first > 0 and rms[first - 1] <= threshold:
        first -= 1
    duration = (last - first + 1) * hop / rate
    if duration < min_silence_seconds:
        return None
    onset = float(frame_times[first] - hop / (2 * rate))
    if onset <= anchor_seconds or onset >= line_end_seconds - 0.1:
        return None
    return {'offset_seconds': round(onset, 3), 'quiet_tail_seconds': round(duration, 3),
            'threshold_rms': round(threshold, 6), 'status': 'possible_vocal_offset_needs_review'}


def reconstruct(line, observations, *, max_spread=0.20, min_duration=0.035, final_offset=None):
    """Return rebuilt token intervals or (None, reason).

    Requires >=2 contexts with exactly one CTC token per displayed character.
    Blank frames are allocated at midpoints between token centers, so this is
    only a timing *estimate*, not a verified phonetic boundary.
    """
    tokens = line.get('tokens')
    if not isinstance(tokens, list) or not tokens:
        return None, 'missing_tokens'
    if len(observations) < 2:
        return None, 'insufficient_contexts'
    n = len(tokens)
    if any(len(obs) != n or any(not _valid(x) for x in obs) for obs in observations):
        return None, 'token_character_mismatch'
    if any(any(obs[i] >= obs[i+1] for i in range(n-1)) for obs in observations):
        return None, 'nonmonotonic_ctc_anchors'
    spreads = [max(obs[i] for obs in observations)-min(obs[i] for obs in observations) for i in range(n)]
    if max(spreads) > max_spread:
        return None, 'unstable_character_anchors'
    centers = [median(obs[i] for obs in observations) for i in range(n)]
    start, end = line.get('start'), line.get('end')
    if not _valid(start) or not _valid(end) or end <= start:
        return None, 'invalid_line_interval'
    if centers[0] < start-0.5 or centers[-1] > end+0.5:
        return None, 'anchors_outside_line'
    boundaries = [float(start)] + [(centers[i]+centers[i+1])/2 for i in range(n-1)] + [float(end)]
    if any(boundaries[i+1]-boundaries[i] < min_duration for i in range(n)):
        return None, 'implausibly_short_character'
    if any(boundaries[i+1]-boundaries[i] > 3.0 for i in range(n)):
        # Only adjust a trailing interval, and only with an explicit acoustic cue.
        if any(boundaries[i+1]-boundaries[i] > 3.0 for i in range(n-1)):
            return None, 'implausibly_long_character'
        if final_offset is None or not _valid(final_offset) or not (boundaries[-2] + min_duration <= final_offset <= end):
            return None, 'implausibly_long_character'
        boundaries[-1] = float(final_offset)
        if boundaries[-1] - boundaries[-2] > 3.0:
            return None, 'implausibly_long_character'
    result = copy.deepcopy(tokens)
    for i, token in enumerate(result):
        token['start'] = round(boundaries[i], 3)
        token['end'] = round(boundaries[i+1], 3)
    return result, None


def build_word_preview(original, hybrid, shadow, *, audio_path=None):
    if not all(isinstance(x, dict) for x in (original, hybrid, shadow)):
        raise ValueError('Expected three JSON objects')
    orig_lines, lines = original.get('lines'), hybrid.get('lines')
    if not isinstance(orig_lines, list) or not isinstance(lines, list) or len(orig_lines) != len(lines):
        raise ValueError('Timeline mismatch')
    selected = set(hybrid.get('hybrid_metadata', {}).get('selected_lines', []))
    output = copy.deepcopy(hybrid)
    applied, rejected = [], []
    for i, (old, line) in enumerate(zip(orig_lines, output['lines'])):
        lid = line.get('line_id', i)
        if lid != old.get('line_id', i) or line.get('text') != old.get('text'):
            raise ValueError('Timeline identity mismatch')
        if lid not in selected:
            continue
        anchors = _anchors(shadow, lid)
        offset_cue = None
        if audio_path is not None and len(anchors) >= 2:
            try:
                last_anchor = median(obs[-1] for obs in anchors if obs)
                offset_cue = estimate_final_vocal_offset(audio_path, last_anchor, line['end'])
            except (OSError, ValueError, RuntimeError, KeyError):
                offset_cue = None  # Missing/unreadable audio must never break preview.
        tokens, reason = reconstruct(line, anchors, final_offset=(offset_cue or {}).get('offset_seconds'))
        if reason:
            # Prevent a uniform-shifted, known-bad token timeline from being
            # presented as word-level improvement. Restore original tokens.
            output['lines'][i] = copy.deepcopy(old)
            entry = {'line_id': lid, 'reason': reason, 'observations': len(anchors)}
            if reason == 'implausibly_long_character':
                entry['anchor_diagnostics'] = inspect_character_anchors(line, anchors)
                entry['offset_diagnostics'] = offset_cue or {'status': 'no_reliable_vocal_offset'}
            rejected.append(entry)
        else:
            line['tokens'] = tokens
            line['needs_review'] = True
            entry = {'line_id': lid, 'observations': len(anchors)}
            if offset_cue and tokens[-1]['end'] == offset_cue['offset_seconds']:
                entry['final_offset_cue'] = offset_cue
            applied.append(entry)
    output['status'] = 'review_required'
    output['ctc_word_preview_metadata'] = {
        'status': 'preview_only', 'method': 'joint_ctc_token_midpoint_reconstruction',
        'warning': 'CTC peaks and vocal silence are not verified phoneme boundaries. No original files changed. Rejected lines revert to the original line and tokens.',
        'applied_count': len(applied), 'rejected_count': len(rejected),
        'applied': applied, 'rejected': rejected,
    }
    return output
