"""Experimental ordered full-song CTC search. Never modifies source song files."""
import argparse
import importlib.util
import json
from pathlib import Path


def deduplicate(candidates, tolerance=0.8):
    """Collapse overlapping-chunk detections of the same onset, keeping best score."""
    out = []
    for hit in sorted(candidates, key=lambda x: x['total_log_probability'], reverse=True):
        if not any(abs(hit['start_seconds'] - prev['start_seconds']) < tolerance for prev in out):
            out.append(hit)
    return sorted(out, key=lambda x: x['start_seconds'])


def ordered_path(lines, skip_penalty=-8.0, gap_penalty=0.015):
    """Monotonic DP over time-ordered candidates; missing lines are explicitly skipped.

    Candidate scores are uncalibrated; output is for diagnostics only.
    """
    states = [(float('-inf'), None, [])]
    # Dynamic programming over last accepted hit; skip leaves last accepted unchanged.
    states = {(None, None): (0.0, [])}
    for line in lines:
        updated = {}
        def offer(key, score, path):
            if key not in updated or score > updated[key][0]:
                updated[key] = (score, path)
        for (last_end, last_start), (score, path) in states.items():
            offer((last_end, last_start), score + skip_penalty, path + [None])
            for candidate in line['candidates']:
                start, end = candidate['start_seconds'], candidate['end_seconds']
                if end <= start or (last_end is not None and start < last_end - 0.1):
                    continue
                # Score is mean log probability; penalty discourages implausible jumps.
                gain = candidate['mean_log_probability'] * 10
                if last_end is not None:
                    gain -= gap_penalty * max(0, start - last_end)
                offer((end, start), score + gain, path + [candidate])
        states = updated
    if not states:
        return [None] * len(lines)
    return max(states.values(), key=lambda x: x[0])[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--timeline', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--device', choices=['cpu','cuda'], default='cuda')
    p.add_argument('--chunk-seconds', type=float, default=20)
    p.add_argument('--overlap-seconds', type=float, default=5)
    p.add_argument('--max-candidates', type=int, default=12)
    args = p.parse_args()
    if not (args.chunk_seconds > args.overlap_seconds >= 0) or args.max_candidates < 1:
        p.error('Invalid chunk/overlap or max-candidates')
    import numpy as np
    import soundfile as sf
    import torch
    from scipy.signal import resample_poly
    from math import gcd
    from transformers import AutoProcessor, AutoModelForCTC
    from opencc import OpenCC
    spec = importlib.util.spec_from_file_location('benchmark_direct_ctc', Path(__file__).with_name('benchmark_direct_ctc.py'))
    direct = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(direct)
    timeline = json.loads(Path(args.timeline).read_text(encoding='utf-8'))
    lines = timeline['lines']
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False).eval()
    blank = model.config.pad_token_id
    if blank is None:
        raise ValueError('Missing CTC blank ID')
    cc = OpenCC('t2s')
    queries = {}
    skipped = {}
    for idx, line in enumerate(lines):
        text = ''.join(c for c in cc.convert(line['text']) if c.isalnum())
        try:
            queries[idx] = (text, direct.tokenize_exact(text, processor.tokenizer))
        except (ValueError, KeyError) as exc:
            skipped[idx] = str(exc)
    wav, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    wav = wav.mean(axis=1)
    if sr != 16000:
        g = gcd(sr, 16000)
        wav = resample_poly(wav, 16000//g, sr//g).astype('float32')
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    model.to(args.device)
    chunk = int(args.chunk_seconds * 16000)
    hop = int((args.chunk_seconds - args.overlap_seconds) * 16000)
    hits = {i: [] for i in queries}
    with torch.inference_mode():
        for begin in range(0, len(wav), hop):
            audio = wav[begin:begin+chunk]
            if len(audio) < 16000:
                continue
            inp = processor(audio, sampling_rate=16000, return_tensors='pt')
            logits = model(inp.input_values.to(args.device)).logits[0]
            lp = torch.log_softmax(logits, dim=-1).cpu().numpy()
            dt = len(audio) / 16000 / len(lp)
            for idx, (_, tokens) in queries.items():
                hit = direct.ctc_subsequence_viterbi(lp, tokens, blank)
                if hit is not None:
                    hit['start_seconds'] = round(begin / 16000 + hit['start_frame'] * dt, 3)
                    hit['end_seconds'] = round(begin / 16000 + hit['end_frame'] * dt, 3)
                    hits[idx].append(hit)
    items = []
    for idx, line in enumerate(lines):
        unique = deduplicate(hits.get(idx, []))
        # Candidate shortlist by total score, then sorted in temporal order for DP.
        shortlist = sorted(sorted(unique, key=lambda h: h['total_log_probability'], reverse=True)[:args.max_candidates], key=lambda h: h['start_seconds'])
        items.append({'line_id': line.get('line_id', idx), 'text': line['text'],
                      'original_start': line.get('start'), 'model_text': queries.get(idx, ('',))[0],
                      'unknown_reason': skipped.get(idx), 'raw_count': len(hits.get(idx, [])),
                      'unique_count': len(unique), 'candidates': shortlist})
    path = ordered_path(items)
    for item, selected in zip(items, path):
        item['selected'] = selected
        item['delta_vs_original_seconds'] = round(selected['start_seconds'] - item['original_start'], 3) if selected and item['original_start'] is not None else None
        print(f"Line {item['line_id']}: original={item['original_start']}, CTC={selected['start_seconds'] if selected else None}, candidates={item['unique_count']}")
    report = {'status':'experimental_uncalibrated', 'method':'CTC_subsequence_viterbi_ordered_DP',
              'model':args.model, 'warning':'Diagnostic only. Scores and skipped-line penalty are not calibrated. Selected hits are NOT verified lyric boundaries. Do not overwrite timeline.',
              'lines':items}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', output)

if __name__ == '__main__':
    main()
