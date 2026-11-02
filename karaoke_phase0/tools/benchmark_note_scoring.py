"""Experimental reference-note segmentation and user-note A/B scoring.

Does not modify the existing frame scoring engine. Times in capture CSV are
already auto-sync adjusted; do not apply the offset again.
"""
import argparse
import bisect
import csv
import json
import math
import statistics
from pathlib import Path


def hz(v):
    try:
        v = float(v)
        return v if math.isfinite(v) and v > 0 else None
    except (ValueError, TypeError):
        return None


def cents(a, b):
    return 1200 * math.log2(b / a)


def score(error, tolerance=50, limit=300):
    return max(0.0, min(100.0, 100 * (limit - max(tolerance, abs(error))) / (limit - tolerance)))


def segment_notes(frames, min_conf=.35, jump_cents=85, min_duration=.16, max_gap=.08):
    """Segment consecutive reference F0 frames by pitch-change threshold.

    A segment is only a *candidate* note, not a verified melody note.
    """
    ordered = sorted(frames, key=lambda x: float(x['time']))
    groups, current = [], []
    def flush():
        if not current:
            return
        times = [float(f['time']) for f in current]
        step = statistics.median([b-a for a,b in zip(times,times[1:])]) if len(times)>1 else .02
        if times[-1] - times[0] + max(0,step) >= min_duration:
            groups.append({'start':times[0], 'end':times[-1]+max(0,step),
                           'reference_hz':statistics.median(float(f['hz']) for f in current),
                           'reference_frames':len(current)})
    for f in ordered:
        t = float(f['time']); v = hz(f.get('hz')); p = f.get('periodicity')
        good = v is not None and (p is None or float(p)>=min_conf)
        if not good:
            flush(); current=[]; continue
        if current and (t-float(current[-1]['time'])>max_gap or
                        abs(cents(statistics.median(float(z['hz']) for z in current[-7:]),v))>jump_cents):
            flush(); current=[]
        current.append(f)
    flush()
    return groups


def score_notes(notes, users, *, user_min_conf=.35, edge_trim=.06, min_user_frames=3, octave_invariant=False):
    """Score one median user F0 per reference note, with no interpolation across gaps."""
    ordered=sorted(users,key=lambda x:float(x['time']))
    times=[float(u['time']) for u in ordered]
    rows=[]
    for i,n in enumerate(notes):
        lo=n['start']+edge_trim; hi=n['end']-edge_trim
        if hi<=lo:
            rows.append({**n,'index':i,'status':'too_short_after_trim','user_frames':0,'score':None});continue
        samples=ordered[bisect.bisect_left(times,lo):bisect.bisect_right(times,hi)]
        valid=[hz(u.get('hz')) for u in samples if hz(u.get('hz')) is not None and
               (u.get('periodicity') is None or float(u['periodicity'])>=user_min_conf)]
        if len(valid)<min_user_frames:
            rows.append({**n,'index':i,'status':'insufficient_user_pitch','user_frames':len(valid),'score':None});continue
        uv=statistics.median(valid); err=cents(n['reference_hz'],uv)
        if octave_invariant: err=(err+600)%1200-600
        rows.append({**n,'index':i,'status':'scored','user_frames':len(valid),
                     'user_hz':round(uv,3),'error_cents':round(err,2),'score':round(score(err),2)})
    scored=[r for r in rows if r['score'] is not None]
    return {'notes':rows,'summary':{'reference_notes':len(notes),'scored_notes':len(scored),
        'note_coverage':round(len(scored)/len(notes),4) if notes else 0,
        'note_score':round(statistics.mean(r['score'] for r in scored),2) if scored else None,
        'warning':'Experimental note candidates from F0, not verified melody notes; compare with frame baseline, not commercial karaoke scores.'}}


def load_user(path):
    with open(path,encoding='utf-8-sig',newline='') as f:
        return [{'time':float(r['time_s']),'hz':hz(r.get('crepe_hz')),
                 'periodicity':float(r['crepe_periodicity']) if r.get('crepe_periodicity') else None}
                for r in csv.DictReader(f)]


def run(reference, capture, output, *, octave_invariant=False):
    ref=json.loads(Path(reference).read_text(encoding='utf-8-sig'))['frames']
    users=load_user(capture)
    notes=segment_notes(ref)
    result=score_notes(notes,users,octave_invariant=octave_invariant)
    # Same frame-level formula and thresholds as existing MVP, self-contained for A/B.
    times=[float(r['time']) for r in ref]
    frame_scores=[]
    for u in users:
        v=hz(u['hz']); p=u['periodicity']
        if v is None or (p is not None and p<.35): continue
        t=u['time']; k=bisect.bisect_left(times,t)
        options=[ref[j] for j in (k-1,k) if 0<=j<len(ref) and abs(times[j]-t)<=.04]
        if not options: continue
        r=min(options,key=lambda x:abs(x['time']-t)); rh=hz(r.get('hz')); rp=r.get('periodicity')
        if rh is None or (rp is not None and float(rp)<.35):continue
        err=cents(rh,v)
        if octave_invariant:err=(err+600)%1200-600
        frame_scores.append(score(err))
    result['summary']['frame_baseline_score']=round(statistics.mean(frame_scores),2) if frame_scores else None
    result['summary']['matched_frames']=len(frame_scores)
    result['summary']['octave_invariant']=octave_invariant
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'note_scoring_summary.json').write_text(json.dumps(result['summary'],indent=2,ensure_ascii=False),encoding='utf-8')
    with (out/'note_scoring_details.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['index','start','end','reference_hz','reference_frames','status','user_frames','user_hz','error_cents','score']
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(result['notes'])
    return result['summary']


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--user-csv',required=True)
    p.add_argument('--output',required=True);p.add_argument('--octave-invariant',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.reference,a.user_csv,a.output,octave_invariant=a.octave_invariant),indent=2))

if __name__=='__main__':main()
