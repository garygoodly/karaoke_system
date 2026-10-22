"""Generate a local-server Lyrics QA page; audio is loaded automatically."""
import json
from pathlib import Path


def render(timeline, output, word_timings=None, player_mode=False):
    timeline = dict(timeline)
    timeline["word_timings"] = word_timings or {}
    timeline["player_mode"] = bool(player_mode)
    payload = json.dumps(timeline, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = r'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Karaoke Lyrics QA</title>
<style>
body{background:#101827;color:#f3f4f6;font:16px system-ui;margin:25px auto;max-width:1000px;padding:0 16px}
audio{width:100%}.player-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}.player-controls label{display:flex;gap:7px;align-items:center}.player-controls input[type=range]{width:125px}.player-controls button{padding:8px 14px;border-radius:8px;background:#2563eb;color:white;border:0;cursor:pointer}.player-controls button:disabled{opacity:.5}.player-controls[hidden]{display:none}.modes{display:flex;gap:8px;margin:12px 0}.modes button{padding:9px 16px;border:1px solid #64748b;border-radius:8px;background:#1e293b;color:white;cursor:pointer}.modes button.selected{background:#2563eb;border-color:#60a5fa}#line{font-size:36px;min-height:85px;text-align:center;margin:35px 0}
.word{color:#9ca3af}.done,.active{color:#facc15}.active{text-decoration:underline}
table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #334155;text-align:left}
small,.muted{color:#aab4c2}.warn{color:#fbbf24}.issue{display:block;width:100%;background:#1e293b;border:1px solid #334155;color:#f3f4f6;padding:10px;margin:7px 0;text-align:left;border-radius:6px;cursor:pointer}
.issue:hover,tr:hover{background:#29374e}tr{cursor:pointer}#status{color:#aab4c2}
</style>
<h2>Phase 0.3 · Lyrics Alignment QA</h2>
<p class="muted">Vocal audio loads automatically. Press Play to review provisional timestamps.</p>
<audio controls preload="metadata" id="audio" src="/vocals.wav"></audio>
<div id="playerControls" class="player-controls" hidden>
<button id="togglePlay" type="button">Play</button><button id="restart" type="button">Restart</button>
<label>Seek <input id="seek" type="range" min="0" max="100" value="0" step="0.1"></label>
<label>Instrumental <input id="instrumentalVolume" type="range" min="0" max="100" value="100"></label>
<label>Original vocal <input id="vocalVolume" type="range" min="0" max="100" value="0"></label>
<span id="playerClock">0:00</span></div><p id="status"></p>
<div class="modes" role="group" aria-label="Lyrics display mode"><button id="lineMode" type="button" class="selected">Line Mode</button><button id="wordMode" type="button">Word Mode</button></div><div id="line">按下播放開始檢查歌詞</div><p id="time"></p>
<h3>Review warnings (<span id="count"></span>)</h3><div id="warnings"></div>
<h3>Line timing</h3><table><thead><tr><th>#</th><th>Start</th><th>End</th><th>Lyrics</th><th>Status</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const DATA=PAYLOAD;
const playerMode=!!DATA.player_mode;
const audio=document.getElementById('audio');
let instrumental=null;
if(playerMode){
  // Instrumental is the master clock; original vocal is a synchronized optional layer.
  instrumental=document.createElement('audio');
  instrumental.preload='metadata';instrumental.src='/instrumental.wav';
  audio.controls=false;
  const controls=document.getElementById('playerControls');controls.hidden=false;
  const playButton=document.getElementById('togglePlay');
  const seek=document.getElementById('seek');
  const musicVol=document.getElementById('instrumentalVolume');
  const vocalVol=document.getElementById('vocalVolume');
  const clock=document.getElementById('playerClock');
  instrumental.volume=1;audio.volume=0;
  musicVol.oninput=()=>instrumental.volume=Number(musicVol.value)/100;
  vocalVol.oninput=()=>audio.volume=Number(vocalVol.value)/100;
  const stamp=t=>Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');
  const sync=()=>{
    if(!Number.isFinite(instrumental.currentTime))return;
    if(audio.readyState>=1 && Math.abs(audio.currentTime-instrumental.currentTime)>.10){
      audio.currentTime=Math.min(instrumental.currentTime,Number.isFinite(audio.duration)?audio.duration:instrumental.currentTime);
    }
  };
  const play=async()=>{
    try{
      sync();
      await instrumental.play();
      if(audio.readyState>=1){await audio.play();sync()}
      playButton.textContent='Pause';
    }catch(e){instrumental.pause();audio.pause();status.textContent='Playback blocked or audio unavailable: '+e.message;}
  };
  const pause=()=>{instrumental.pause();audio.pause();playButton.textContent='Play'};
  playButton.onclick=()=>instrumental.paused?play():pause();
  document.getElementById('restart').onclick=()=>{pause();instrumental.currentTime=0;audio.currentTime=0;play()};
  seek.oninput=()=>{if(Number.isFinite(instrumental.duration)){instrumental.currentTime=Number(seek.value)/100*instrumental.duration;sync()}};
  instrumental.addEventListener('timeupdate',()=>{
    sync();seek.value=instrumental.duration?String(100*instrumental.currentTime/instrumental.duration):'0';
    clock.textContent=stamp(instrumental.currentTime)+' / '+stamp(instrumental.duration||0);
  });
  instrumental.addEventListener('ended',()=>{pause();instrumental.currentTime=0;audio.currentTime=0;seek.value='0'});
  instrumental.addEventListener('error',()=>{status.textContent='Instrumental unavailable; verify generated/instrumental.wav'});
  audio.addEventListener('loadedmetadata',()=>{if(!instrumental.paused){sync();audio.play().catch(()=>{})}});
  audio.addEventListener('ended',()=>{if(!instrumental.paused)audio.pause()});
  setInterval(()=>{if(!instrumental.paused)sync()},250);
}
const playback=()=>playerMode?instrumental:audio;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const lines=DATA.lines||[],warnings=DATA.warnings||[];
let displayMode='line';
for(const mode of ['line','word']){document.getElementById(mode+'Mode').onclick=()=>{displayMode=mode;for(const m of ['line','word'])document.getElementById(m+'Mode').classList.toggle('selected',m===mode)}}
const wordTimings=DATA.word_timings||{};
const byId=new Map(lines.map(l=>[Number(l.line_id),l]));
const fmt=v=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(2):'—';
const status=document.getElementById('status');
audio.addEventListener('loadedmetadata',()=>status.textContent='Vocal audio ready · '+fmt(audio.duration)+' s');
audio.addEventListener('error',()=>status.textContent='Cannot load vocals.wav. Reopen QA from the Song Library.');
function jump(l){if(!l||!Number.isFinite(Number(l.start)))return;const t=Math.max(0,Number(l.start));playback().currentTime=t;if(playerMode){audio.currentTime=t;if(playback().paused)document.getElementById('togglePlay').click()}else audio.play().catch(()=>{status.textContent='Press Play to start audio.'})}
const warningBox=document.getElementById('warnings');document.getElementById('count').textContent=warnings.length;
if(!warnings.length)warningBox.textContent='No structural warnings. Manual listening is still required.';
for(const w of warnings){const b=document.createElement('button');b.className='issue';const l=byId.get(Number(w.line_id));const detail=w.similarity==null?'':' · similarity '+w.similarity;
b.textContent='Line '+(Number(w.line_id)+1)+' · '+(w.reason||'Review')+detail+(l?' · '+l.text:' · no aligned timestamp');
b.onclick=()=>jump(l);if(!l)b.title='No timestamp available; manual alignment is required';warningBox.appendChild(b)}
const rows=document.getElementById('rows');
for(const l of lines){const tr=document.createElement('tr');for(const value of [Number(l.line_id)+1,fmt(l.start),fmt(l.end),l.text,l.needs_review?'REVIEW':'Provisional']){const td=document.createElement('td');td.textContent=value??'';tr.appendChild(td)}tr.onclick=()=>jump(l);rows.appendChild(tr)}
function frame(){const t=playback().currentTime;document.getElementById('time').textContent='Song time: '+t.toFixed(2)+'s · '+DATA.status;
const l=lines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);
const target=document.getElementById('line');if(l){const tokens=displayMode==='word'?(wordTimings[String(l.line_id)]||[]):[];target.innerHTML=tokens.length?tokens.map(w=>'<span class="'+(t>=w.end?'done':t>=w.start?'active':'word')+'">'+esc(w.text)+'</span>').join(''):esc(l.text)}else target.textContent='';requestAnimationFrame(frame)}requestAnimationFrame(frame);
</script></html>'''
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page.replace('PAYLOAD', payload), encoding='utf-8')
    return output
