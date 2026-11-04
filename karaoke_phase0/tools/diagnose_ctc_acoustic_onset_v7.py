"""Read-only acoustic onset candidates near v6 CTC token peaks.

RMS and positive spectral flux are non-lexical cues. They cannot prove which
syllable began; this tool never edits a lyrics timeline or labels a true onset.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def features(audio, sr, hop_ms=10, frame_ms=30):
    if sr <= 0 or not 0 < hop_ms <= frame_ms:
        raise ValueError('invalid frame settings')
    hop = max(1, round(sr * hop_ms / 1000))
    width = max(2, round(sr * frame_ms / 1000))
    if len(audio) < width:
        return np.array([]), np.array([]), np.array([])
    # centered analysis frames, no silent zero padding at file edges
    starts = np.arange(0, len(audio) - width + 1, hop)
    frames = np.lib.stride_tricks.sliding_window_view(np.asarray(audio, dtype=np.float64), width)[starts]
    frames = frames * np.hanning(width)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    spec = np.abs(np.fft.rfft(frames, axis=1))
    spec /= np.maximum(spec.sum(axis=1, keepdims=True), 1e-10)
    flux = np.r_[0.0, np.maximum(np.diff(spec, axis=0), 0).sum(axis=1)]
    return (starts + width / 2) / sr, rms, flux


def onset_candidates(times, rms, flux, peak, previous_end=None, lookback=1.5, max_results=5):
    if lookback <= 0 or max_results < 1:
        raise ValueError('invalid search parameters')
    if len(times) == 0:
        return []
    lower = max(0.0, peak - lookback)
    if previous_end is not None:
        lower = max(lower, float(previous_end))
    mask = (times >= lower) & (times <= peak + 0.05)
    inds = np.flatnonzero(mask)
    if len(inds) < 3:
        return []
    # Locally normalized features; threshold excludes weak background artifacts.
    r = rms[inds]
    f = flux[inds]
    rscale = max(float(np.quantile(r, 0.9)), 1e-9)
    fscale = max(float(np.quantile(f, 0.9)), 1e-9)
    rnorm = np.clip(r / rscale, 0, 1)
    fnorm = np.clip(f / fscale, 0, 1)
    rise = np.maximum(np.diff(rnorm, prepend=rnorm[0]), 0)
    score = 0.55 * fnorm + 0.45 * rise
    maxima = [k for k in range(1, len(inds)-1) if score[k] >= score[k-1] and score[k] > score[k+1] and rnorm[k] >= 0.12]
    maxima.sort(key=lambda k: (-score[k], times[inds[k]]))
    chosen = []
    for k in maxima:
        t = float(times[inds[k]])
        if any(abs(t - x['time_seconds']) < 0.12 for x in chosen):
            continue
        chosen.append({'time_seconds': round(t, 3), 'cue_score': round(float(score[k]), 4),
                       'rms_relative': round(float(rnorm[k]), 4), 'flux_relative': round(float(fnorm[k]), 4)})
        if len(chosen) == max_results:
            break
    return chosen


def analyze(audio, sr, rows, lookback=1.5):
    times, rms, flux = features(audio, sr)
    out = []
    for row in rows:
        peak = row.get('token_peak_median')
        anchored = [x['previous_last_token_end'] for x in row.get('observations', [])
                    if x.get('passes_order') and x.get('previous_last_token_end') is not None]
        # Conservative boundary: do not search earlier than the earliest valid
        # previous-line ending, but preserve raw context for audit.
        prev = min(anchored) if anchored else None
        candidates = onset_candidates(times, rms, flux, float(peak), prev, lookback) if peak is not None else []
        out.append({'line_id': row['line_id'], 'token_peak_seconds': peak,
                    'previous_end_constraint_seconds': prev,
                    'search_start_seconds': round(max(0, float(peak)-lookback, prev if prev is not None else 0), 3) if peak is not None else None,
                    'candidate_onsets': candidates, 'estimated_acoustic_onset': None,
                    'status': 'candidate_cues_need_listening' if candidates else 'no_acoustic_cue',
                    'warning': 'RMS/flux peaks may be instruments, consonants, or internal syllables; not validated onsets.'})
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--v6', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--line-ids', nargs='+', type=int, default=[2, 5, 24])
    p.add_argument('--lookback-seconds', type=float, default=1.5)
    args = p.parse_args()
    if args.lookback_seconds <= 0:
        p.error('lookback-seconds must be positive')
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    audio, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    # 16k is sufficient for the onset diagnostics and reduces FFT cost.
    if sr != 16000:
        d = gcd(sr, 16000)
        audio = resample_poly(audio, 16000//d, sr//d)
        sr = 16000
    report = json.loads(Path(args.v6).read_text(encoding='utf-8'))
    selected = set(args.line_ids)
    rows = [x for x in report['lines'] if x['line_id'] in selected]
    output = {'status':'diagnostic_only', 'method':'ctc_acoustic_onset_cues_v7',
              'warning':'No validated acoustic onset or timeline edits. Scores are relative within each search window.',
              'lines': analyze(audio, sr, rows, args.lookback_seconds)}
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    for x in output['lines']:
        print(f"Line {x['line_id']}: peak={x['token_peak_seconds']}, onset_cues={len(x['candidate_onsets'])}, status={x['status']}")
    print('Report:', target)

if __name__ == '__main__':
    main()
