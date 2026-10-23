"""Extract reference F0 from a separated vocal WAV, offline and locally."""
import json
from pathlib import Path


def note_cents(reference_hz, user_hz):
    import math
    if not all(isinstance(x, (float, int)) and math.isfinite(x) and x > 0 for x in (reference_hz, user_hz)):
        return None
    return 1200 * math.log2(user_hz / reference_hz)


def nearest_reference(frames, t, tolerance=0.075):
    """Return a voiced frame within tolerance of playback time, else None."""
    if not frames or t < 0:
        return None
    import bisect
    times = [f['time'] for f in frames]
    k = bisect.bisect_left(times, t)
    options = [frames[j] for j in (k - 1, k) if 0 <= j < len(frames)]
    candidates = [f for f in options if abs(f['time'] - t) <= tolerance and f.get('hz') is not None]
    return min(candidates, key=lambda f: abs(f['time'] - t)) if candidates else None


def extract_reference(wav_path, output_path, *, device='cpu', periodicity_threshold=0.35, hop_ms=20):
    import numpy as np
    import torch
    import torchcrepe
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    from math import gcd
    sr, data = wavfile.read(str(wav_path))
    if data.ndim == 2:
        data = data.astype(np.float32).mean(axis=1)
    if data.dtype.kind in 'iu':
        data = data.astype(np.float32) / float(max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max))
    else:
        data = data.astype(np.float32)
    if sr != 16000:
        g = gcd(int(sr), 16000)
        data = resample_poly(data, 16000 // g, int(sr) // g).astype(np.float32)
    hop = int(16000 * hop_ms / 1000)
    # Bounded chunks to avoid GPU/CPU memory spikes on multi-minute songs.
    frames = []
    for start in range(0, len(data), 16000 * 15):
        chunk = data[start:start + 16000 * 15]
        if len(chunk) < 1024:
            continue
        audio = torch.tensor(chunk, dtype=torch.float32, device=device).unsqueeze(0)
        with torch.inference_mode():
            hz, p = torchcrepe.predict(audio, 16000, hop, 75, 900, model='tiny',
                                        device=device, batch_size=512, return_periodicity=True)
        frequencies = hz[0].cpu().numpy()
        confidence = p[0].cpu().numpy()
        for i, (f, c) in enumerate(zip(frequencies, confidence)):
            valid = np.isfinite(f) and f > 0 and c >= periodicity_threshold
            frames.append({'time': round((start + i * hop) / 16000, 4),
                           'hz': round(float(f), 3) if valid else None,
                           'periodicity': round(float(c), 4)})
    result = {'version': 1, 'source': Path(wav_path).name, 'method': 'torchcrepe-tiny',
              'hop_seconds': hop / 16000, 'periodicity_threshold': periodicity_threshold,
              'frames': frames, 'status': 'experimental'}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    return result
