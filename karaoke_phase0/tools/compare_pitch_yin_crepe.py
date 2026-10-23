"""Compare YIN-style autocorrelation/CMNDF and torchcrepe on identical WAV samples.

This is an offline A/B diagnostic, not a ground-truth accuracy benchmark.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd


def load_mono(path, sr=16000, start=0.0, duration=30.0):
    with sf.SoundFile(str(path)) as f:
        f.seek(min(len(f), round(start * f.samplerate)))
        frames = len(f) - f.tell() if duration is None else min(len(f)-f.tell(), round(duration*f.samplerate))
        audio = f.read(frames, dtype='float32', always_2d=True).mean(axis=1)
        orig_sr = f.samplerate
    if orig_sr != sr:
        d = gcd(orig_sr, sr)
        audio = resample_poly(audio, sr//d, orig_sr//d).astype('float32')
    return audio


def yin_frame(frame, sr, fmin=75.0, fmax=900.0, threshold=0.15, min_db=-52.0):
    frame = np.asarray(frame, dtype=np.float64)
    rms = np.sqrt(np.mean(frame*frame))
    if rms < 10**(min_db/20):
        return np.nan, 'below_rms_gate'
    frame -= np.mean(frame)
    low = max(2, int(sr/fmax))
    high = min(int(sr/fmin), len(frame)//2)
    if high <= low:
        return np.nan, 'invalid_range'
    # Difference function and cumulative mean normalized difference (YIN).
    diff = np.zeros(high+1)
    for tau in range(1, high+1):
        delta = frame[:-tau] - frame[tau:]
        diff[tau] = np.dot(delta, delta)
    cmnd = np.ones(high+1)
    running = np.cumsum(diff[1:])
    cmnd[1:] = diff[1:]*np.arange(1, high+1)/np.maximum(running, 1e-15)
    candidates = np.where(cmnd[low:high+1] < threshold)[0]
    if not len(candidates):
        return np.nan, 'low_periodicity'
    tau = int(candidates[0]+low)
    while tau < high and cmnd[tau+1] < cmnd[tau]:
        tau += 1
    if 1 < tau < high:
        a,b,c = cmnd[tau-1:tau+2]
        denom = a-2*b+c
        if abs(denom)>1e-12:
            tau = tau + float(np.clip(0.5*(a-c)/denom, -1, 1))
    return float(sr/tau), 'voiced'


def yin_track(audio, sr=16000, hop=160, frame_size=4096, threshold=0.15, min_db=-52):
    pad = frame_size//2
    padded = np.pad(audio, (pad,pad))
    pitches=[]; reasons=[]
    for center in range(0, len(audio), hop):
        segment=padded[center:center+frame_size]
        if len(segment)!=frame_size: break
        f0, reason=yin_frame(segment,sr,threshold=threshold,min_db=min_db)
        pitches.append(f0);reasons.append(reason)
    return np.asarray(pitches),reasons


def crepe_track(audio, sr=16000, hop=160, model='tiny', periodicity=0.3, device='cpu'):
    try:
        import torch
        import torchcrepe
    except ImportError as exc:
        raise RuntimeError('torchcrepe is not installed. Install with: uv pip install torchcrepe') from exc
    if device=='cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA requested but unavailable')
    x=torch.from_numpy(audio.copy()).unsqueeze(0).to(device)
    with torch.no_grad():
        f0, pd = torchcrepe.predict(x,sr,hop,75,900,model=model,batch_size=512,
                                     device=device,return_periodicity=True)
    hz=f0.squeeze().detach().cpu().numpy().astype(float)
    conf=pd.squeeze().detach().cpu().numpy().astype(float)
    hz[conf < periodicity]=np.nan
    return hz,conf


def stats(f0, hop_seconds):
    f0=np.asarray(f0,dtype=float)
    valid=np.isfinite(f0)&(f0>0)
    transitions=valid[1:]&valid[:-1]
    jumps=np.abs(1200*np.log2(np.maximum(f0[1:],1)/np.maximum(f0[:-1],1)))
    return {'frames':int(len(f0)), 'voiced_fraction':float(valid.mean()) if len(f0) else 0,
            'unvoiced_fraction':float(1-valid.mean()) if len(f0) else 1,
            'octave_sized_jumps_over_900_cents':int(np.sum(transitions&(jumps>900))),
            'median_f0_hz':float(np.median(f0[valid])) if valid.any() else None,
            'hop_seconds':hop_seconds}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--wav',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('benchmarks/pitch_ab'))
    p.add_argument('--start',type=float,default=20)
    p.add_argument('--duration',type=float,default=30)
    p.add_argument('--yin-threshold',type=float,default=0.15)
    p.add_argument('--rms-db',type=float,default=-52)
    p.add_argument('--crepe-periodicity',type=float,default=0.3)
    p.add_argument('--model',choices=['tiny','full'],default='tiny')
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=p.parse_args()
    if args.start<0 or args.duration<=0: p.error('start must be >=0 and duration >0')
    audio=load_mono(args.wav,start=args.start,duration=args.duration)
    if len(audio)<4096: p.error('Selected audio segment is too short')
    hop=160
    yin, reasons=yin_track(audio,threshold=args.yin_threshold,min_db=args.rms_db)
    crepe, confidence=crepe_track(audio,model=args.model,periodicity=args.crepe_periodicity,device=args.device)
    n=min(len(yin),len(crepe))
    times=args.start+np.arange(n)*hop/16000
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'pitch_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['time_s','yin_hz','yin_reason','crepe_hz','crepe_periodicity'])
        for i in range(n):
            writer.writerow([round(float(times[i]),4),float(yin[i]) if np.isfinite(yin[i]) else '',reasons[i],
                             float(crepe[i]) if np.isfinite(crepe[i]) else '',float(confidence[i])])
    report={'input':str(args.wav),'start_seconds':args.start,'duration_seconds':len(audio)/16000,
            'yin':stats(yin[:n],hop/16000),'torchcrepe':stats(crepe[:n],hop/16000),
            'caveat':'No ground truth. Voiced fraction and jumps measure behavior, not pitch accuracy. '
                     'YIN here is a Python YIN-style reference, not an exact port of the browser implementation.'}
    (args.output/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(12,4))
    ax.plot(times,yin[:n],label='YIN reference',linewidth=1,alpha=.7)
    ax.plot(times,crepe[:n],label='torchcrepe',linewidth=1,alpha=.7)
    ax.set(xlabel='Song time (s)',ylabel='F0 (Hz)',title='Pitch tracking A/B (no ground truth)')
    ax.legend();fig.tight_layout();fig.savefig(args.output/'pitch_comparison.png',dpi=150);plt.close(fig)
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
