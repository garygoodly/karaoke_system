"""Experimental known-text CTC audio search. Does not modify song data.

Requires an explicitly selected CTC acoustic model with a tokenizer supporting
all characters in the query. Model compatibility with Mandarin singing is NOT
assumed. Run `--help` for usage.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np






# Shared pure algorithms; preserve legacy public names for existing benchmarks/tests.
import sys as _ctc_sys
from pathlib import Path as _ctc_Path
_ctc_src = str(_ctc_Path(__file__).resolve().parents[1] / 'src')
if _ctc_src not in _ctc_sys.path:
    _ctc_sys.path.insert(0, _ctc_src)
from karaoke_phase0.alignment.ctc_core import ctc_subsequence_viterbi, tokenize_exact

def run(args):
    import soundfile as sf
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForCTC
    except ImportError as e:
        raise SystemExit('Install optional benchmark dependencies: uv pip install transformers') from e
    if not args.model:
        raise SystemExit('Specify --model with a verified Mandarin character-CTC model id or local path')
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False)
    model.eval()
    tokenizer = processor.tokenizer
    token_ids = tokenize_exact(args.text, tokenizer)
    blank_id = model.config.pad_token_id
    if blank_id is None:
        raise ValueError('Model has no pad_token_id/CTC blank configuration')
    wav, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    wav = wav.mean(axis=1)
    if sr != 16000:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(sr, 16000)
        wav = resample_poly(wav, 16000//g, sr//g).astype('float32')
    sr = 16000
    device = 'cuda' if args.device == 'cuda' and torch.cuda.is_available() else 'cpu'
    if args.device == 'cuda' and device != 'cuda':
        raise RuntimeError('CUDA requested but unavailable')
    model.to(device)
    chunk = int(args.chunk_seconds * sr)
    hop = int((args.chunk_seconds - args.overlap_seconds) * sr)
    if chunk <= 0 or hop <= 0:
        raise ValueError('chunk_seconds must exceed overlap_seconds >= 0')
    candidates = []
    with torch.inference_mode():
        for begin in range(0, len(wav), hop):
            audio = wav[begin:min(len(wav),begin+chunk)]
            if len(audio) < sr:
                continue
            inp = processor(audio, sampling_rate=sr, return_tensors='pt')
            input_values = inp.input_values.to(device)
            logits = model(input_values).logits
            lp = torch.log_softmax(logits[0], dim=-1).cpu().numpy()
            hit = ctc_subsequence_viterbi(lp, token_ids, blank_id)
            if hit is None:
                continue
            # Approximate frame times; CTC frames span chunk duration.
            seconds_per_frame = (len(audio)/sr) / len(lp)
            hit['start_seconds'] = round(begin/sr + hit['start_frame']*seconds_per_frame, 3)
            hit['end_seconds'] = round(begin/sr + hit['end_frame']*seconds_per_frame, 3)
            candidates.append(hit)
    candidates.sort(key=lambda c:c['total_log_probability'], reverse=True)
    result = {'status':'experimental_uncalibrated', 'method':'CTC_subsequence_viterbi',
              'audio':str(args.audio), 'text':args.text, 'model':args.model,
              'warning':'CTC log likelihood is not calibrated across durations or songs. Check actual audio manually. No timeline modified.',
              'candidates':candidates[:args.top_k]}
    out = Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Candidates: {len(candidates)}; report: {out}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio',required=True)
    p.add_argument('--text',required=True)
    p.add_argument('--model',required=True,help='Explicitly selected CTC Mandarin model ID or local path')
    p.add_argument('--output',required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--chunk-seconds',type=float,default=20.0)
    p.add_argument('--overlap-seconds',type=float,default=5.0)
    p.add_argument('--top-k',type=int,default=5)
    run(p.parse_args())

if __name__=='__main__':
    main()
