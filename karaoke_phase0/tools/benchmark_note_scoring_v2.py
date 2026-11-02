"""Experimental note segmentation v2; independent of the existing GUI scorer."""
import argparse
import csv
import json
import math
import statistics
from pathlib import Path

from benchmark_note_scoring import hz, cents, score, load_user, segment_notes, score_notes


def segment_notes_v2(frames, start, end, *, min_conf=.35, min_duration=.22,
                     max_gap=.12, pitch_tolerance=110, median_window=5):
    """Smooth pitch, join brief gaps and modest vibrato; never bridge long rests.

    Candidate notes are NOT verified melody notes. Times use the reference clock.
    """
    if not (math.isfinite(start) and math.isfinite(end) and end > start):
        raise ValueError('Invalid capture interval')
    selected = sorted((f for f in frames if start <= float(f['time']) <= end),
                      key=lambda f: float(f['time']))
    if not selected:
        return []
    # Smooth in cents, not Hz, without crossing long gaps or large pitch jumps.
    values = []
    for i, f in enumerate(selected):
        v = hz(f.get('hz'))
        p = f.get('periodicity')
        valid = v is not None and (p is None or float(p) >= min_conf)
        if not valid:
            values.append(None)
            continue
        nearby=[]
        for j in range(max(0,i-median_window//2), min(len(selected),i+median_window//2+1)):
            q=selected[j]; qv=hz(q.get('hz')); qp=q.get('periodicity')
            if qv is not None and (qp is None or float(qp)>=min_conf) and abs(float(q['time'])-float(f['time'])) <= .065 and abs(cents(v,qv)) <= 180:
                nearby.append(math.log2(qv))
        values.append(2**statistics.median(nearby) if nearby else v)
    groups=[]; current=[]
    def flush():
        if not current:
            return
        duration=current[-1][0]-current[0][0]+.02
        if duration >= min_duration and len(current)>=3:
            groups.append({'start':current[0][0], 'end':min(end,current[-1][0]+.02),
                           'reference_hz':statistics.median(v for _,v in current),
                           'reference_frames':len(current)})
    for f,v in zip(selected,values):
        t=float(f['time'])
        if v is None:
            continue  # gaps checked when next voiced sample arrives
        if current and (t-current[-1][0]>max_gap or
                        abs(cents(statistics.median(x[1] for x in current[-12:]),v))>pitch_tolerance):
            flush();current=[]
        current.append((t,v))
    flush()
    # Merge adjacent same-pitch candidates separated by a short unvoiced region.
    merged=[]
    for note in groups:
        if merged and note['start']-merged[-1]['end'] <= max_gap and abs(cents(merged[-1]['reference_hz'],note['reference_hz']))<=pitch_tolerance/2:
            prev=merged[-1]
            prev['reference_hz']=2**((math.log2(prev['reference_hz'])*prev['reference_frames']+math.log2(note['reference_hz'])*note['reference_frames'])/(prev['reference_frames']+note['reference_frames']))
            prev['end']=note['end'];prev['reference_frames']+=note['reference_frames']
        else:merged.append(note.copy())
    return merged


def run(reference, capture, output, octave_invariant=False):
    ref=json.loads(Path(reference).read_text(encoding='utf-8-sig'))['frames']
    users=load_user(capture)
    if not users:raise ValueError('Empty capture')
    start=max(0,min(u['time'] for u in users)); end=max(u['time'] for u in users)
    if end<=start:raise ValueError('Capture has no time span')
    old=segment_notes(ref)
    old_window=[n for n in old if n['end']>start and n['start']<end]
    new=segment_notes_v2(ref,start,end)
    v1=score_notes(old_window,users,octave_invariant=octave_invariant)
    v2=score_notes(new,users,octave_invariant=octave_invariant)
    # Match only note candidates inside the capture window; do not claim melody accuracy.
    summary={'capture_start_s':round(start,3),'capture_end_s':round(end,3),
             'v1_window':v1['summary'],'v2_window':v2['summary'],
             'warning':'Scores are conditional on successfully scored candidate notes; not comparable to commercial karaoke grades. No ground truth.'}
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'note_scoring_v2_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    for label,data in [('v1',v1),('v2',v2)]:
        with (out/f'{label}_notes.csv').open('w',newline='',encoding='utf-8-sig') as f:
            fields=['index','start','end','reference_hz','reference_frames','status','user_frames','user_hz','error_cents','score']
            w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(data['notes'])
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--user-csv',required=True);p.add_argument('--output',required=True);p.add_argument('--octave-invariant',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.reference,a.user_csv,a.output,a.octave_invariant),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
