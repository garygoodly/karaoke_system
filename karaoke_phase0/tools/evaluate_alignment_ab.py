"""Compare character boundaries against manually annotated ground truth (global seconds)."""
import argparse, csv, statistics
from pathlib import Path

def load(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def evaluate(reference, prediction):
    gt = load(reference); pred = load(prediction)
    groups = {}
    for row in pred:
        groups.setdefault((row['line_id'], row['character']), []).append(row)
    offsets = {}; errors=[]; missing=0
    for row in gt:
        if not row['start_s_global'] or not row['end_s_global']:
            continue
        key=(row['line_id'],row['character']); i=offsets.get(key,0); offsets[key]=i+1
        candidates=groups.get(key,[])
        if i>=len(candidates): missing+=1;continue
        p=candidates[i]
        for col in ('start_s_global','end_s_global'):
            errors.append(abs(float(p[col])-float(row[col])))
    if not errors: raise SystemExit('No comparable labeled boundaries; fill ground truth first.')
    ordered=sorted(errors); p90=ordered[max(0,int(.9*len(ordered)+.999999)-1)]
    print(f'boundaries={len(errors)} missing_characters={missing} MAE_ms={statistics.mean(errors)*1000:.1f} P90_ms={p90*1000:.1f}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--truth',required=True);p.add_argument('--prediction',required=True)
    a=p.parse_args();evaluate(a.truth,a.prediction)
