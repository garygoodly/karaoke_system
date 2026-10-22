"""Generate a local-server Lyrics QA page; audio is loaded automatically."""
import json
from pathlib import Path


def render(timeline, output):
    payload = json.dumps(timeline, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = r'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Karaoke Lyrics QA</title>
<style>
body{background:#101827;color:#f3f4f6;font:16px system-ui;margin:25px auto;max-width:1000px;padding:0 16px}
audio{width:100%}#line{font-size:36px;min-height:85px;text-align:center;margin:35px 0}
.word{color:#9ca3af}.done,.active{color:#facc15}.active{text-decoration:underline}
table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #334155;text-align:left}
small,.muted{color:#aab4c2}.warn{color:#fbbf24}.issue{display:block;width:100%;background:#1e293b;border:1px solid #334155;color:#f3f4f6;padding:10px;margin:7px 0;text-align:left;border-radius:6px;cursor:pointer}
.issue:hover,tr:hover{background:#29374e}tr{cursor:pointer}#status{color:#aab4c2}
</style>
<h2>Phase 0.3 · Lyrics Alignment QA</h2>
<p class="muted">Vocal audio loads automatically. Press Play to review provisional timestamps.</p>
<audio controls preload="metadata" id="audio" src="/vocals.wav"></audio><p id="status"></p>
<div id="line">按下播放開始檢查歌詞</div><p id="time"></p>
<h3>Review warnings (<span id="count"></span>)</h3><div id="warnings"></div>
<h3>Line timing</h3><table><thead><tr><th>#</th><th>Start</th><th>End</th><th>Lyrics</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const DATA=PAYLOAD;
const audio=document.getElementById('audio');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const lines=DATA.lines||[],warnings=DATA.warnings||[];
const byId=new Map(lines.map(l=>[Number(l.line_id),l]));
const fmt=v=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(2):'—';
const status=document.getElementById('status');
audio.addEventListener('loadedmetadata',()=>status.textContent='Vocal audio ready · '+fmt(audio.duration)+' s');
audio.addEventListener('error',()=>status.textContent='Cannot load vocals.wav. Reopen QA from the Song Library.');
function jump(l){if(!l||!Number.isFinite(Number(l.start)))return;audio.currentTime=Math.max(0,Number(l.start));audio.play().catch(()=>{status.textContent='Press Play to start audio.'})}
const warningBox=document.getElementById('warnings');document.getElementById('count').textContent=warnings.length;
if(!warnings.length)warningBox.textContent='No structural warnings. Manual listening is still required.';
for(const w of warnings){const b=document.createElement('button');b.className='issue';const l=byId.get(Number(w.line_id));const detail=w.similarity==null?'':' · similarity '+w.similarity;
b.textContent='Line '+(Number(w.line_id)+1)+' · '+(w.reason||'Review')+detail+(l?' · '+l.text:' · no aligned timestamp');
b.onclick=()=>jump(l);if(!l)b.title='No timestamp available; manual alignment is required';warningBox.appendChild(b)}
const rows=document.getElementById('rows');
for(const l of lines){const tr=document.createElement('tr');for(const value of [Number(l.line_id)+1,fmt(l.start),fmt(l.end),l.text,l.needs_review?'REVIEW':'Provisional']){const td=document.createElement('td');td.textContent=value??'';tr.appendChild(td)}tr.onclick=()=>jump(l);rows.appendChild(tr)}
function frame(){const t=audio.currentTime;document.getElementById('time').textContent='Song time: '+t.toFixed(2)+'s · '+DATA.status;
const l=lines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);
const target=document.getElementById('line');if(l){const tokens=l.tokens||[];target.innerHTML=tokens.length?tokens.map(w=>'<span class="'+(t>=w.end?'done':t>=w.start?'active':'word')+'">'+esc(w.text)+'</span>').join(''):esc(l.text)}else target.textContent='';requestAnimationFrame(frame)}requestAnimationFrame(frame);
</script></html>'''
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page.replace('PAYLOAD', payload), encoding='utf-8')
    return output
