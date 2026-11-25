"""Diagnostic-only cross-line CTC conflict validation; never changes timestamps."""
from __future__ import annotations
import wave
from pathlib import Path
from statistics import median


def _rms_windows(audio_path, lo, hi, step=0.05):
    """Read only the requested WAV interval, with no third-party dependency."""
    import numpy as np
    with wave.open(str(audio_path), 'rb') as wav:
        rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
        if width not in (1, 2, 3, 4) or rate <= 0:
            raise ValueError('Unsupported PCM WAV')
        begin = max(0, int(lo * rate)); stop = min(wav.getnframes(), int(hi * rate))
        wav.setpos(begin)
        frames = max(1, round(step * rate))
        output = []
        pos = begin
        while pos < stop:
            count = min(frames, stop - pos)
            data = wav.readframes(count)
            if not data: break
            if width == 1:
                values = np.frombuffer(data, dtype=np.uint8).astype(np.float64) - 128.0
            elif width == 2:
                values = np.frombuffer(data, dtype='<i2').astype(np.float64)
            elif width == 4:
                values = np.frombuffer(data, dtype='<i4').astype(np.float64)
            else:
                raw = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
                values = (raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16))
                values = ((values ^ 0x800000) - 0x800000).astype(np.float64)
            if channels not in (1, 2):
                raise ValueError('Only mono/stereo PCM supported')
            values = values.reshape(-1, channels).mean(axis=1)
            rms = float(np.sqrt(np.mean(values * values))) / float(1 << (8 * width - 1))
            output.append({'time_seconds': round((pos + count / 2) / rate, 3),
                           'rms': round(rms, 6)})
            pos += count
        return output


def diagnose_boundary(shadow, timeline, *, previous_line_id=18, audio_path=None):
    """Distinguish repeated-token ambiguity from observed energy dips.

    An RMS valley is *not* a confirmed vocal offset or lyric boundary.
    CTC group overlap is not independent statistical replication.
    """
    current_id = previous_line_id + 1
    lines = {row.get('line_id', i): row for i, row in enumerate(timeline['lines'])}
    prev, curr = lines[previous_line_id], lines[current_id]
    evidence = []
    for gi, group in enumerate(shadow.get('groups', [])):
        if group.get('status') != 'candidate_needs_review': continue
        for row in group.get('lines', []):
            if row.get('line_id') == current_id and isinstance(row.get('start_seconds'), (int, float)):
                evidence.append({'group_index': gi, 'start_seconds': row['start_seconds'],
                                 'first_anchor_seconds': (row.get('character_anchors') or [None])[0]})
    starts = sorted(e['start_seconds'] for e in evidence)
    candidate = round(median(starts), 3) if starts else None
    prev_text = ''.join(c for c in prev['text'] if not c.isspace())
    curr_text = ''.join(c for c in curr['text'] if not c.isspace())
    # Repeated tokens near the boundary can cause CTC to attach to prior lyrics.
    repeated = sorted(set(prev_text[-5:]) & set(curr_text[:5]))
    original_end = prev.get('end')
    report = {
        'status': 'diagnostic_only', 'line_ids': [previous_line_id, current_id],
        'original_previous_end': original_end, 'original_current_start': curr.get('start'),
        'ctc_group_evidence': evidence, 'ctc_candidate_median': candidate,
        'ctc_spread_seconds': round(starts[-1] - starts[0], 3) if len(starts) >= 2 else None,
        'overlap_with_original_previous_end_seconds': round(original_end - candidate, 3) if candidate is not None else None,
        'repeated_boundary_characters': repeated,
        'repeated_token_ambiguity': bool(repeated),
        'acoustic_evidence': {'status': 'not_available'},
        'auto_adopt': False,
        'warning': 'CTC peaks and RMS valleys do not establish which lyric was sung. Never auto-adopt.',
    }
    if audio_path is not None and Path(audio_path).is_file() and candidate is not None:
        try:
            lo = max(0, min(candidate, original_end) - 1.0)
            hi = max(candidate, original_end) + 1.0
            frames = _rms_windows(audio_path, lo, hi)
            positive = [f['rms'] for f in frames if f['rms'] > 0]
            reference = median(positive) if positive else 0
            # A local low-energy cue is only a candidate, not a syllable boundary.
            valleys = [f for f in frames if reference > 0 and f['rms'] <= reference * 0.25]
            report['acoustic_evidence'] = {
                'status': 'rms_valleys_unverified', 'window_seconds': [round(lo, 3), round(hi, 3)],
                'rms_reference': round(reference, 6),
                'low_energy_cues': valleys,
                'frame_step_seconds': 0.05,
                'warning': 'Low RMS may be breath, silence, separation artifact or accompaniment; not phoneme identification.',
            }
        except (ValueError, OSError, EOFError) as exc:
            report['acoustic_evidence'] = {'status': 'audio_unreadable', 'reason': str(exc)}
    return report
