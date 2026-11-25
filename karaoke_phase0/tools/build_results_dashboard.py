"""Generate an offline, self-contained singing diagnostics dashboard (stdlib only)."""
import argparse
import bisect
import csv
import html
import json
import math
from pathlib import Path


def load_data(reference, capture, timeline, notes=None):
    ref = json.loads(Path(reference).read_text(encoding='utf-8-sig'))['frames']
    lines = json.loads(Path(timeline).read_text(encoding='utf-8-sig'))['lines']
    with open(capture, encoding='utf-8-sig', newline='') as f:
        user = list(csv.DictReader(f))
    note_rows = []
    if notes:
        with open(notes, encoding='utf-8-sig', newline='') as f:
            note_rows = list(csv.DictReader(f))
    return ref, user, lines, note_rows


def number(v):
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def make_report(reference, capture, timeline, notes=None):
    ref, user, lines, note_rows = load_data(reference, capture, timeline, notes)
    times = [float(f['time']) for f in ref]
    if not times:
        raise ValueError('Reference frames are empty')
    points = []
    for row in user:
        t = number(row.get('time_s'))
        if t is None:
            continue
        i = bisect.bisect_left(times, t)
        nearest = min((j for j in (i - 1, i) if 0 <= j < len(ref)), key=lambda j: abs(times[j] - t), default=None)
        r = ref[nearest] if nearest is not None and abs(times[nearest] - t) <= 0.06 else None
        rhz = number(r.get('hz')) if r else None
        uhz = number(row.get('crepe_hz'))
        confidence = number(row.get('crepe_periodicity'))
        # Reference pitch and user pitch are independent; do not interpolate across unvoiced gaps.
        err = 1200 * math.log2(uhz / rhz) if uhz and rhz and uhz > 0 and rhz > 0 and (confidence is None or confidence >= 0.35) else None
        points.append({'t':round(t,3),'ref':rhz,'user':uhz,'confidence':confidence,'error':round(err,2) if err is not None else None})
    # Line diagnostics are explicitly frame-based and not the v2 note score.
    line_stats = []
    for line in lines:
        start, end = number(line.get('start')), number(line.get('end'))
        if start is None or end is None or end <= start:
            continue
        segment = [p for p in points if start <= p['t'] < end]
        matched = [p for p in segment if p['error'] is not None]
        errors = sorted(abs(p['error']) for p in matched)
        median = errors[len(errors)//2] if errors else None
        line_stats.append({'id':line.get('line_id'),'text':line.get('text',''),'start':start,'end':end,'samples':len(segment),'matched':len(matched),'coverage':round(len(matched)/len(segment)*100,1) if segment else None,'median_error_cents':round(median,1) if median is not None else None})
    notes_summary = {'scored':0,'total':len(note_rows),'average_score':None}
    if note_rows:
        scores = [number(n.get('score')) for n in note_rows if n.get('status')=='scored']
        scores = [s for s in scores if s is not None]
        notes_summary.update(scored=len(scores),average_score=round(sum(scores)/len(scores),2) if scores else None)
    return {'points':points,'lines':line_stats,'notes':notes_summary,'meta':{'capture_frames':len(points),'reference_frames':len(ref),'matched_frames':sum(p['error'] is not None for p in points),'time_basis':'capture time_s (already auto-sync corrected)','line_metric':'median absolute cents among matched frames; NOT a commercial score','note_metric':'optional precomputed v2 candidate notes'}}


def render_html(data):
    payload = json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return '''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Karaoke | Singing Results</title>
<style>body{margin:0;background:#0b1220;color:#e8edf7;font:15px system-ui,"Microsoft JhengHei",sans-serif}main{max-width:1150px;margin:auto;padding:30px}h1{margin:0 0 6px;font-size:29px}p,.muted{color:#9facbf}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:22px 0}.card,.panel{background:#141e30;border:1px solid #29354a;border-radius:14px;padding:20px}.value{font-size:30px;font-weight:750;color:#6ee7b7}.panel{margin:16px 0}svg{width:100%;height:auto;background:#101a2b;border-radius:10px}.legend{display:flex;gap:22px;flex-wrap:wrap;margin:12px 0}.swatch{display:inline-block;width:13px;height:3px;vertical-align:middle;margin-right:6px}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #29354a;text-align:left}th{color:#9facbf}input{width:100%} .scroll{overflow:auto}small{color:#9facbf}</style></head><body><main><h1>演唱結果分析 <small>Offline Diagnostics</small></h1><p>使用已錄製的 Pitch Capture 與 Reference；不需要麥克風、GPU 或網路。</p><section class="cards" id="cards"></section><section class="panel"><h2>Reference vs Your Pitch</h2><div class="legend"><span><i class="swatch" style="background:#6ee7b7"></i>Reference</span><span><i class="swatch" style="background:#60a5fa"></i>Your Pitch</span></div><label>時間視窗（起點）：<span id="windowLabel"></span><input id="timeSlider" type="range" min="0" max="0" step="1" value="0"></label><svg id="pitch" viewBox="0 0 1040 330" role="img" aria-label="Pitch comparison"></svg></section><section class="panel"><h2>Pitch Error Timeline</h2><p>絕對音準誤差（cents），灰色區段代表無法有效比較，不應直接判定漏唱。</p><svg id="error" viewBox="0 0 1040 200" role="img" aria-label="Absolute pitch error"></svg></section><section class="panel scroll"><h2>逐句分析（診斷指標，非正式分數）</h2><table><thead><tr><th>歌詞</th><th>時間</th><th>有效配對</th><th>配對率</th><th>誤差中位數</th></tr></thead><tbody id="lines"></tbody></table></section><p>限制：Reference F0 可能有誤；歌詞時間窗可能重疊；本報表不將無 F0 視為漏唱，也不把逐句誤差轉換為正式分數。</p></main><script>
const D=__DATA__;const P=D.points;const maxT=Math.ceil(Math.max(0,...P.map(x=>x.t)));const slider=document.getElementById('timeSlider');slider.max=Math.max(0,maxT-20);
function el(tag,attrs={},text=''){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text)n.textContent=text;return n}
function plot(id,kind,start){const s=document.getElementById(id);s.replaceChildren();const w=1040,h=kind==='pitch'?330:200,left=58,right=20,top=20,bottom=32;const end=start+20;const arr=P.filter(x=>x.t>=start&&x.t<=end);const ymin=kind==='pitch'?70:0,ymax=kind==='pitch'?900:650;const x=t=>left+(t-start)/20*(w-left-right),y=v=>top+(ymax-v)/(ymax-ymin)*(h-top-bottom);for(let v=ymin;v<=ymax;v+=kind==='pitch'?100:100){const yy=y(v);s.append(el('line',{x1:left,y1:yy,x2:w-right,y2:yy,stroke:'#26384e'}));s.append(el('text',{x:6,y:yy+4,fill:'#9facbf','font-size':12},String(v)))}for(let t=Math.ceil(start/5)*5;t<=end;t+=5){s.append(el('text',{x:x(t)-8,y:h-9,fill:'#9facbf','font-size':12},String(t)+'s'))}
const keys=kind==='pitch'?[['ref','#6ee7b7'],['user','#60a5fa']]:[['error','#f59e0b']];for(const [key,color] of keys){let segment=[];function flush(){if(segment.length>1)s.append(el('polyline',{points:segment.join(' '),fill:'none',stroke:color,'stroke-width':2,'stroke-linejoin':'round'}));segment=[]}let last=null;for(const p of arr){const val=key==='error'&&p.error!==null?Math.abs(p.error):p[key];if(val===null||val===undefined||val<ymin||val>ymax||(last!==null&&p.t-last>0.3)){flush();last=p.t;if(val===null||val===undefined||val<ymin||val>ymax)continue}segment.push(x(p.t).toFixed(1)+','+y(val).toFixed(1));last=p.t}flush()}}
function draw(){const start=Number(slider.value);document.getElementById('windowLabel').textContent=start+'–'+(start+20)+' s';plot('pitch','pitch',start);plot('error','error',start)}slider.addEventListener('input',draw);draw();
const cards=[['Capture Frames',D.meta.capture_frames],['Matched Frames',D.meta.matched_frames],['Line Windows',D.lines.length],['v2 Note Candidates',D.notes.total?D.notes.scored+' / '+D.notes.total:'未提供']];for(const [label,value] of cards){const c=document.createElement('div');c.className='card';const l=document.createElement('div');l.className='muted';l.textContent=label;const v=document.createElement('div');v.className='value';v.textContent=value;c.append(l,v);document.getElementById('cards').append(c)}for(const line of D.lines){const tr=document.createElement('tr');const fields=[line.text,`${line.start.toFixed(1)}–${line.end.toFixed(1)}s`,`${line.matched}/${line.samples}`,line.coverage===null?'—':line.coverage+'%',line.median_error_cents===null?'—':line.median_error_cents+' ¢'];for(const v of fields){const td=document.createElement('td');td.textContent=v;tr.append(td)}document.getElementById('lines').append(tr)}
</script></body></html>'''.replace('__DATA__',payload)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True);p.add_argument('--user-csv',required=True);p.add_argument('--timeline',required=True);p.add_argument('--notes');p.add_argument('--output',required=True)
    a=p.parse_args();result=make_report(a.reference,a.user_csv,a.timeline,a.notes);out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(render_html(result),encoding='utf-8');print('Created:',out,'matched:',result['meta']['matched_frames'])
if __name__=='__main__':main()
