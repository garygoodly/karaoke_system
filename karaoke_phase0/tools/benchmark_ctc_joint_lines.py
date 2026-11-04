"""Experimental joint CTC alignment of two adjacent known-lyrics lines.

Runs one acoustic inference over a user-selected short window. The same CTC path
must consume both lines in order. Never writes to the source song directory.
"""
import argparse
import json
from pathlib import Path
import numpy as np




# Shared pure algorithms; preserve legacy public names for existing benchmarks/tests.
import sys as _ctc_sys
from pathlib import Path as _ctc_Path
_ctc_src = str(_ctc_Path(__file__).resolve().parents[1] / 'src')
if _ctc_src not in _ctc_sys.path:
    _ctc_sys.path.insert(0, _ctc_src)
from karaoke_phase0.alignment.ctc_core import joint_viterbi

def run(args):
    import torch
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    from transformers import AutoProcessor, AutoModelForCTC
    from opencc import OpenCC
    timeline = json.loads(Path(args.timeline).read_text(encoding='utf-8'))['lines']
    if args.line1 < 0 or args.line2 >= len(timeline) or args.line2 != args.line1 + 1:
        raise ValueError('Choose two consecutive line indices')
    converter = OpenCC('t2s')
    texts = [''.join(c for c in converter.convert(timeline[i]['text']) if c.isalnum()) for i in (args.line1, args.line2)]
    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False)
    def exact_tokens(text):
        ids = processor.tokenizer(text, add_special_tokens=False).input_ids
        if not ids or processor.tokenizer.unk_token_id in ids or processor.tokenizer.decode(ids, skip_special_tokens=True).replace(' ','') != text:
            raise ValueError(f'Tokenizer cannot exactly encode {text!r}')
        return ids
    first, second = [exact_tokens(t) for t in texts]
    wav, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    wav = wav.mean(axis=1)
    if sr != 16000:
        g = gcd(sr,16000)
        wav = resample_poly(wav,16000//g,sr//g).astype('float32')
    if not 0 <= args.start < args.end <= len(wav)/16000:
        raise ValueError('Window must be inside audio')
    crop = wav[int(args.start*16000):int(args.end*16000)]
    if args.device == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    model = AutoModelForCTC.from_pretrained(args.model, trust_remote_code=False).eval().to(args.device)
    blank = model.config.pad_token_id
    with torch.inference_mode():
        inputs = processor(crop,sampling_rate=16000,return_tensors='pt')
        logits = model(inputs.input_values.to(args.device)).logits[0]
        lp = torch.log_softmax(logits,dim=-1).cpu().numpy()
    result = joint_viterbi(lp,first+second,blank,len(first))
    if result is None:
        raise RuntimeError('No joint alignment path found')
    dt = len(crop)/16000/len(lp)
    def stamp(frame):
        return round(args.start+frame*dt,3)
    for span in result['token_spans']:
        span['start_seconds'] = stamp(span['start_frame'])
        span['end_seconds'] = stamp(span['end_frame'])
    for key in ('line1_last_token','line2_first_token'):
        result[key] = dict(result[key],start_seconds=stamp(result[key]['start_frame']),end_seconds=stamp(result[key]['end_frame']))
    result['joint_start_seconds'] = stamp(result['start_frame'])
    result['joint_end_seconds'] = stamp(result['end_frame'])
    result['line2_start_seconds'] = result['line2_first_token']['start_seconds']
    result['line1_end_seconds'] = result['line1_last_token']['end_seconds']
    report = {'status':'experimental_uncalibrated','method':'joint_ctc_subsequence_viterbi',
              'warning':'Not ground truth. Short-window, character-CTC alignment; do not modify timeline.',
              'model':args.model,'line_ids':[args.line1,args.line2], 'model_texts':texts,
              'window_seconds':[args.start,args.end], 'result':result}
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Line {args.line1} last token ends: {result['line1_end_seconds']}s")
    print(f"Line {args.line2} first token starts: {result['line2_start_seconds']}s")
    print(f'Report: {out}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audio',required=True);p.add_argument('--timeline',required=True)
    p.add_argument('--model',required=True);p.add_argument('--output',required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cuda')
    p.add_argument('--line1',type=int,default=23);p.add_argument('--line2',type=int,default=24)
    p.add_argument('--start',type=float,default=220);p.add_argument('--end',type=float,default=236)
    run(p.parse_args())


if __name__=='__main__':
    main()
