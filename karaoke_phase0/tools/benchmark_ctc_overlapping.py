"""Experimental grouped known-lyrics CTC alignment; never modifies source timeline.

Overlapping groups of 2-4 consecutive supported lines, aligns their concatenated tokens in a
single local audio window, and reports per-line token-derived boundaries.
"""
import argparse
import importlib.util
import json
from pathlib import Path


def load_joint_module():
    path = Path(__file__).with_name('benchmark_ctc_joint_lines.py')
    if not path.is_file():
        raise FileNotFoundError('Install the earlier Joint CTC patch first')
    spec = importlib.util.spec_from_file_location('karaoke_joint_ctc', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def make_overlapping_groups(lines, supported, size=3, stride=2, max_gap=18.0):
    """Sliding groups inside contiguous supported runs, covering every line."""
    if not 2 <= size <= 4 or not 1 <= stride < size or max_gap <= 0:
        raise ValueError('Invalid overlapping group settings')
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
    result = []
    for run in runs:
        if len(run) <= size:
            result.append(run)
            continue
        starts = list(range(0, len(run)-size+1, stride))
        if starts[-1] != len(run)-size:
            starts.append(len(run)-size)
        result.extend(run[start:start+size] for start in starts)
    return result


def summarize_consensus(groups, lines, tolerance=0.5):
    """Keep independent observations; median is diagnostic, not a correction."""
    from statistics import median
    observations = {i: [] for i in range(len(lines))}
    for group in groups:
        if group.get('status') != 'candidate_needs_review':
            continue
        for item in group.get('lines', []):
            observations[item['line_id']].append(float(item['start_seconds']))
    result = []
    for i, line in enumerate(lines):
        values = sorted(observations[i])
        spread = values[-1]-values[0] if values else None
        result.append({'line_id': i, 'original_start': line['start'],
                       'observations': [round(v, 3) for v in values],
                       'observation_count': len(values),
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


def run(args):
    import numpy as np
    import soundfile as sf
    import torch
    from scipy.signal import resample_poly
    from math import gcd
    from transformers import AutoProcessor, AutoModelForCTC
    from opencc import OpenCC

    joint = load_joint_module()
    lines = json.loads(Path(args.timeline).read_text(encoding='utf-8'))['lines']
    converter = OpenCC('t2s')
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    tokenizer = processor.tokenizer
    supported, excluded = {}, {}
    for i, line in enumerate(lines):
        normalized = ''.join(c for c in converter.convert(line['text']) if c.isalnum())
        ids = tokenizer(normalized, add_special_tokens=False).input_ids
        if not ids or tokenizer.unk_token_id in ids or tokenizer.decode(ids, skip_special_tokens=True).replace(' ', '') != normalized:
            excluded[i] = 'unknown_or_inexact_tokenization'
        else:
            supported[i] = (normalized, ids)
    groups = make_overlapping_groups(lines, supported, args.group_size, args.stride, args.max_gap)
    wav, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    wav = wav.mean(axis=1)
    if sr != 16000:
        g = gcd(sr, 16000)
        wav = resample_poly(wav, 16000//g, sr//g).astype('float32')
    duration = len(wav) / 16000
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False).eval().to(args.device)
    blank = model.config.pad_token_id
    if blank is None:
        raise ValueError('Model has no CTC blank token')
    results = []
    for group in groups:
        # A deliberately bounded search window, anchored on the old timeline.
        # Results can inherit its errors; they are NOT independent ground truth.
        start = max(0.0, float(lines[group[0]]['start']) - args.pad_before)
        last = group[-1]
        nominal_end = float(lines[last].get('end') or (float(lines[last]['start']) + 7.0))
        end = min(duration, max(nominal_end, float(lines[last]['start']) + 2.0) + args.pad_after)
        row = {'line_ids': group, 'window_seconds': [round(start, 3), round(end, 3)], 'status': 'pending'}
        if end <= start or end-start > args.max_window:
            row.update(status='window_rejected', reason='invalid_or_too_long_window')
            results.append(row)
            continue
        clip = wav[int(start*16000):int(end*16000)]
        ids_by_line = [supported[i][1] for i in group]
        ids = [token for part in ids_by_line for token in part]
        if len(ids) > args.max_tokens:
            row.update(status='window_rejected', reason='too_many_tokens')
            results.append(row)
            continue
        with torch.inference_mode():
            inputs = processor(clip, sampling_rate=16000, return_tensors='pt')
            logits = model(inputs.input_values.to(args.device)).logits[0]
            log_probs = torch.log_softmax(logits, dim=-1).cpu().numpy()
        # Joint algorithm supports one split index; its traceback contains all
        # token spans, which can be partitioned at every line boundary.
        hit = joint.joint_viterbi(log_probs, ids, blank, len(ids_by_line[0])) if len(group) > 1 else None
        if hit is None:
            row.update(status='no_path')
        else:
            dt = (len(clip)/16000) / len(log_probs)
            line_bounds = boundaries(hit['token_spans'], [len(x) for x in ids_by_line], lambda frame: start+frame*dt)
            row.update(status='candidate_needs_review', score=round(hit['total_log_probability'], 4), lines=[
                {'line_id': i, 'text': lines[i]['text'], 'original_start': lines[i]['start'],
                 **bound, 'delta_vs_original_seconds': round(bound['start_seconds']-float(lines[i]['start']), 3)}
                for i, bound in zip(group, line_bounds)])
        results.append(row)
        print('Group', ','.join(map(str, group)), row['status'])
    report = {'status': 'experimental_uncalibrated', 'method': 'overlapping_grouped_joint_ctc_viterbi',
              'warning': 'Diagnostic only; windows use existing timeline as hints. No timeline modified. Validate manually.',
              'model': args.model, 'group_size': args.group_size, 'stride': args.stride, 'excluded_lines': excluded, 'groups': results,
              'consensus': summarize_consensus(results, lines, args.consistency_tolerance)}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--timeline', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    p.add_argument('--group-size', type=int, choices=[2,3,4], default=3)
    p.add_argument('--stride', type=int, default=2)
    p.add_argument('--consistency-tolerance', type=float, default=0.5)
    p.add_argument('--max-gap', type=float, default=18)
    p.add_argument('--pad-before', type=float, default=4)
    p.add_argument('--pad-after', type=float, default=3)
    p.add_argument('--max-window', type=float, default=48)
    p.add_argument('--max-tokens', type=int, default=100)
    args = p.parse_args()
    if not 1 <= args.stride < args.group_size or args.consistency_tolerance < 0 or args.max_gap <= 0 or args.pad_before < 0 or args.pad_after < 0 or args.max_window <= 0 or args.max_tokens <= 0:
        p.error('Invalid window settings')
    run(args)

if __name__ == '__main__':
    main()
