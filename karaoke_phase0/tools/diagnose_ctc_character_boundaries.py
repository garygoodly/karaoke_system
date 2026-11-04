"""Read-only character-level diagnostics for selected sliding-window joint CTC groups.

Uses the same anchored windows as benchmark_ctc_sliding_v4.py. Does not change song data.
"""
import argparse
import importlib.util
import json
from pathlib import Path


def load_joint():
    path = Path(__file__).with_name('benchmark_ctc_joint_lines.py')
    if not path.exists():
        raise FileNotFoundError('Install Joint CTC patch before running diagnostics')
    spec = importlib.util.spec_from_file_location('ctc_joint_boundary', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def partition_tokens(group, ids_by_line, spans, frame_to_time):
    if len(spans) != sum(map(len, ids_by_line)):
        raise ValueError('CTC traceback length differs from token count')
    result = []
    offset = 0
    for line_id, ids in zip(group, ids_by_line):
        tokens = []
        for span in spans[offset:offset + len(ids)]:
            tokens.append({'start_seconds': round(frame_to_time(span['start_frame']), 3),
                           'end_seconds': round(frame_to_time(span['end_frame']), 3)})
        result.append({'line_id': line_id, 'tokens': tokens,
                       'start_seconds': tokens[0]['start_seconds'],
                       'end_seconds': tokens[-1]['end_seconds']})
        offset += len(ids)
    return result


def boundary_summary(rows, target):
    result = []
    for row in rows:
        if row.get('status') != 'candidate_needs_review':
            continue
        lines = row['lines']
        for idx, line in enumerate(lines):
            if line['line_id'] != target:
                continue
            prev = lines[idx - 1] if idx else None
            first = line['tokens'][0]
            prev_last = prev['tokens'][-1] if prev else None
            result.append({'group': row['line_ids'],
                           'target_first_start': first['start_seconds'],
                           'target_first_end': first['end_seconds'],
                           'previous_last_end': prev_last['end_seconds'] if prev_last else None,
                           'gap_seconds': round(first['start_seconds'] - prev_last['end_seconds'], 3) if prev_last else None})
    return result


def run(args):
    import torch
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    from transformers import AutoProcessor, AutoModelForCTC
    from opencc import OpenCC

    joint = load_joint()
    lines = json.loads(Path(args.timeline).read_text(encoding='utf-8'))['lines']
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    tok = processor.tokenizer
    cc = OpenCC('t2s')
    normalized = {}
    for i, line in enumerate(lines):
        text = ''.join(c for c in cc.convert(line['text']) if c.isalnum())
        ids = tok(text, add_special_tokens=False).input_ids
        if ids and tok.unk_token_id not in ids and tok.decode(ids, skip_special_tokens=True).replace(' ', '') == text and len(ids) == len(text):
            normalized[i] = (text, ids)
    audio, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    if sr != 16000:
        g = gcd(sr, 16000)
        audio = resample_poly(audio, 16000//g, sr//g).astype('float32')
    duration = len(audio) / 16000
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False).eval().to(args.device)
    blank = model.config.pad_token_id
    if blank is None:
        raise ValueError('Model missing CTC blank ID')
    groups = []
    for target in args.line_ids:
        for start_idx in (target - 2, target - 1, target):
            group = list(range(start_idx, start_idx + 3))
            if min(group) < 0 or max(group) >= len(lines) or any(i not in normalized for i in group):
                continue
            if group not in groups:
                groups.append(group)
    rows = []
    for group in groups:
        start = max(0., float(lines[group[0]]['start']) - args.pad_before)
        last = group[-1]
        nominal_end = float(lines[last].get('end') or float(lines[last]['start']) + 7)
        end = min(duration, max(nominal_end, float(lines[last]['start']) + 2) + args.pad_after)
        row = {'line_ids': group, 'window_seconds': [round(start, 3), round(end, 3)]}
        if end <= start or end - start > args.max_window:
            row['status'] = 'window_rejected'; rows.append(row); continue
        clip = audio[int(start * 16000):int(end * 16000)]
        ids_by_line = [normalized[i][1] for i in group]
        ids = [item for part in ids_by_line for item in part]
        if len(ids) > args.max_tokens:
            row['status'] = 'too_many_tokens'; rows.append(row); continue
        with torch.inference_mode():
            inputs = processor(clip, sampling_rate=16000, return_tensors='pt')
            logits = model(inputs.input_values.to(args.device)).logits[0]
            lp = torch.log_softmax(logits, dim=-1).cpu().numpy()
        hit = joint.joint_viterbi(lp, ids, blank, len(ids_by_line[0]))
        if hit is None:
            row['status'] = 'no_path'; rows.append(row); continue
        dt = len(clip) / 16000 / len(lp)
        parts = partition_tokens(group, ids_by_line, hit['token_spans'], lambda frame: start + frame * dt)
        for line, i in zip(parts, group):
            line['text'] = lines[i]['text']
            line['characters'] = list(normalized[i][0])
            for token, char in zip(line['tokens'], line['characters']):
                token['character'] = char
        row.update(status='candidate_needs_review', lines=parts)
        rows.append(row)
        print('Group', ','.join(map(str, group)), row['status'])
    report = {'status': 'diagnostic_only', 'method': 'joint_ctc_character_traceback',
              'warning': 'Token boundaries are Viterbi assignments, not verified phonetic boundaries. Windows depend on original timeline. No source files modified.',
              'model': args.model, 'groups': rows,
              'target_summaries': [{'line_id': i, 'observations': boundary_summary(rows, i)} for i in args.line_ids]}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', output)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio', required=True)
    p.add_argument('--timeline', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    p.add_argument('--line-ids', nargs='+', type=int, default=[2, 24])
    p.add_argument('--pad-before', type=float, default=4.)
    p.add_argument('--pad-after', type=float, default=3.)
    p.add_argument('--max-window', type=float, default=48.)
    p.add_argument('--max-tokens', type=int, default=100)
    args = p.parse_args()
    if any(i < 0 for i in args.line_ids) or args.pad_before < 0 or args.pad_after < 0 or args.max_window <= 0 or args.max_tokens <= 0:
        p.error('Invalid diagnostic settings')
    run(args)


if __name__ == '__main__':
    main()
