"""Conservative vocal activity mask from separated vocals, lyric windows and F0.

Mask is an estimate of expected singing, not proof of actual vocalization.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf


def build_mask(vocals, timeline, reference, *, hop_seconds=0.02, frame_seconds=0.04,
               relative_energy=0.08, min_energy=0.0008, pad_seconds=0.12):
    lines = timeline.get('lines', [])
    windows = [(max(0.0, float(x['start']) - pad_seconds), float(x['end']) + pad_seconds)
               for x in lines if x.get('start') is not None and x.get('end') is not None
               and float(x['end']) > float(x['start'])]
    ref_frames = reference.get('frames', [])
    ref_times = np.array([float(x['time']) for x in ref_frames], dtype=float)
    ref_valid = np.array([x.get('hz') is not None and float(x['hz']) > 0 and
                          float(x.get('periodicity') or 0) >= 0.35 for x in ref_frames], dtype=bool)
    frames = []
    with sf.SoundFile(str(vocals)) as wav:
        sr = wav.samplerate
        hop = max(1, round(sr * hop_seconds))
        width = max(hop, round(sr * frame_seconds))
        # Sequential streaming, avoids loading long songs into RAM.
        mono = np.empty(0, dtype=np.float32)
        rms = []
        while True:
            chunk = wav.read(frames=hop * 256, dtype='float32', always_2d=True)
            if not len(chunk):
                break
            mono = np.concatenate((mono, chunk.mean(axis=1)))
            while len(mono) >= width:
                rms.append(float(np.sqrt(np.mean(np.square(mono[:width], dtype=np.float64)))))
                mono = mono[hop:]
        if len(mono) >= hop:
            rms.append(float(np.sqrt(np.mean(np.square(mono, dtype=np.float64)))))
    times = np.arange(len(rms)) * hop / sr
    inside = np.array([any(a <= t <= b for a, b in windows) for t in times], dtype=bool)
    rms_arr = np.asarray(rms)
    reference_energy = rms_arr[inside] if inside.any() else rms_arr
    floor = max(min_energy, float(np.percentile(reference_energy, 75)) * relative_energy) if len(reference_energy) else min_energy
    for t, level, within in zip(times, rms, inside):
        j = int(np.searchsorted(ref_times, t))
        nearby = [k for k in (j - 1, j) if 0 <= k < len(ref_times) and abs(ref_times[k] - t) <= 0.04]
        pitch = any(ref_valid[k] for k in nearby)
        # A detected pitch still needs audible vocal energy and lyric context.
        active = bool(within and level >= floor)
        frames.append({'time': round(float(t), 5), 'active': active, 'rms': round(level, 6),
                       'reference_voiced': bool(pitch)})
    return {'version': 1, 'hop_seconds': hop / sr, 'energy_threshold': floor,
            'source': 'vocals.wav', 'method': 'lyric_window_and_vocal_rms',
            'frames': frames, 'active_fraction': sum(f['active'] for f in frames) / len(frames) if frames else 0.0,
            'warning': 'Separated vocals may contain accompaniment bleed; mask is heuristic.'}


def singing_coverage(mask, user_frames, *, tolerance=0.06, min_confidence=0.35):
    """Compute expected singing coverage from captured frames, excluding intro/outro."""
    import bisect
    frames = mask['frames']
    times = [float(f['time']) for f in frames]
    counts = {'expected_frames': 0, 'user_voiced': 0, 'user_unvoiced': 0, 'outside_vocal_activity': 0,
              'no_mask_near_time': 0}
    for user in user_frames:
        t = float(user['time'])
        j = bisect.bisect_left(times, t)
        candidates = [k for k in (j - 1, j) if 0 <= k < len(times)]
        if not candidates or min(abs(times[k] - t) for k in candidates) > tolerance:
            counts['no_mask_near_time'] += 1
            continue
        k = min(candidates, key=lambda k: abs(times[k] - t))
        if not frames[k]['active']:
            counts['outside_vocal_activity'] += 1
            continue
        counts['expected_frames'] += 1
        try:
            hz = float(user.get('hz') or 0)
            confidence = float(user.get('periodicity') if user.get('periodicity') is not None else 1)
        except (ValueError, TypeError):
            hz, confidence = 0, 0
        counts['user_voiced' if np.isfinite(hz) and hz > 0 and confidence >= min_confidence else 'user_unvoiced'] += 1
    counts['singing_coverage'] = (counts['user_voiced'] / counts['expected_frames']
                                  if counts['expected_frames'] else None)
    return counts


def write_mask(vocals, timeline_path, reference_path, output):
    result = build_mask(vocals, json.loads(Path(timeline_path).read_text(encoding='utf-8-sig')),
                        json.loads(Path(reference_path).read_text(encoding='utf-8-sig')))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return result
