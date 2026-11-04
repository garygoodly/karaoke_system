"""Experimental five-line CTC vs ASR benchmark. Read-only song inputs."""
import argparse
import importlib.util
import json
from pathlib import Path


def overlap_ratio(a, b):
    intersection = max(0., min(a['end_seconds'], b['end_seconds']) - max(a['start_seconds'], b['start_seconds']))
    shorter = min(a['end_seconds']-a['start_seconds'], b['end_seconds']-b['start_seconds'])
    return intersection / shorter if shorter > 0 else 0.


def deduplicate(candidates, threshold=0.7):
    """Keep highest-total-log-likelihood hit from overlapping chunk detections."""
    retained = []
    for candidate in sorted(candidates, key=lambda c: c['total_log_probability'], reverse=True):
        if not any(overlap_ratio(candidate, existing) >= threshold for existing in retained):
            retained.append(candidate)
    return retained


def analyze_candidates(candidates, asr_start, top_k=5):
    unique = deduplicate(candidates)
    return {'raw_count': len(candidates), 'unique_count': len(unique),
            'candidates': [{**c, 'delta_vs_asr_start_seconds': round(c['start_seconds'] - asr_start, 3) if asr_start is not None else None}
                           for c in unique[:top_k]]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--timeline', required=True)
    p.add_argument('--asr', required=True, help='Original asr_segments.json with line_matches')
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--line-ids', nargs='+', type=int, default=[0,1,2,3,5])
    p.add_argument('--device', choices=['cpu','cuda'], default='cuda')
    p.add_argument('--chunk-seconds', type=float, default=20.)
    p.add_argument('--overlap-seconds', type=float, default=5.)
    p.add_argument('--top-k', type=int, default=5)
    args = p.parse_args()
    if not (args.chunk_seconds > args.overlap_seconds >= 0):
        p.error('chunk-seconds must be greater than overlap-seconds >= 0')
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import AutoProcessor, AutoModelForCTC
    from opencc import OpenCC
    from scipy.signal import resample_poly
    from math import gcd
    # Reuse existing, tested Viterbi implementation; no duplicate algorithm.
    spec = importlib.util.spec_from_file_location('benchmark_direct_ctc', Path(__file__).with_name('benchmark_direct_ctc.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    timeline = json.loads(Path(args.timeline).read_text(encoding='utf-8'))
    asr = json.loads(Path(args.asr).read_text(encoding='utf-8'))
    matches = {int(x['line_id']):x for x in asr.get('line_matches', [])}
    lines = {int(x['line_id']):x for x in timeline['lines']}
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False).eval()
    blank_id = model.config.pad_token_id
    if blank_id is None: raise ValueError('Missing CTC blank ID')
    cc = OpenCC('t2s')
    queries = {}
    for line_id in args.line_ids:
        if line_id not in lines: raise ValueError(f'Unknown line_id {line_id}')
        text = cc.convert(lines[line_id]['text'])
        # Drop punctuation and whitespace only; never silently replace unknown characters.
        text = ''.join(c for c in text if c.isalnum())
        queries[line_id] = (text, module.tokenize_exact(text, processor.tokenizer))
    wav, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    wav = wav.mean(axis=1)
    if sr != 16000:
        g = gcd(sr,16000)
        wav = resample_poly(wav, 16000//g, sr//g).astype('float32')
    sr = 16000
    if args.device == 'cuda' and not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable')
    model.to(args.device)
    chunk = int(args.chunk_seconds*sr)
    hop = int((args.chunk_seconds-args.overlap_seconds)*sr)
    results = {line_id: [] for line_id in queries}
    with torch.inference_mode():
        for begin in range(0,len(wav),hop):
            audio = wav[begin:begin+chunk]
            if len(audio) < sr: continue
            inp = processor(audio, sampling_rate=sr, return_tensors='pt')
            logits = model(inp.input_values.to(args.device)).logits[0]
            lp = torch.log_softmax(logits, dim=-1).cpu().numpy()
            dt = (len(audio)/sr)/len(lp)
            for line_id, (_, ids) in queries.items():
                hit = module.ctc_subsequence_viterbi(lp, ids, blank_id)
                if hit:
                    hit['start_seconds'] = round(begin/sr + hit['start_frame']*dt,3)
                    hit['end_seconds'] = round(begin/sr + hit['end_frame']*dt,3)
                    results[line_id].append(hit)
    report = {'status':'experimental_uncalibrated', 'model':args.model,
              'warning':'Not ground truth. CTC total log scores depend on duration; ranking may favor short false matches. Do not modify timeline.',
              'lines': []}
    for line_id, (text, _) in queries.items():
        match = matches.get(line_id,{})
        asr_start = match.get('candidate_start_seconds')
        item = {'line_id':line_id, 'original_text':lines[line_id]['text'], 'model_text':text,
                'timeline_start':lines[line_id].get('start'), 'asr_start':asr_start,
                'asr_similarity':match.get('similarity'),
                **analyze_candidates(results[line_id],asr_start,args.top_k)}
        report['lines'].append(item)
        best = item['candidates'][0] if item['candidates'] else None
        print(f'Line {line_id}: ASR={asr_start}, CTC={best["start_seconds"] if best else None}, raw={item["raw_count"]}, unique={item["unique_count"]}')
    out = Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Report: {out}')


if __name__ == '__main__':
    main()
