import html
import os
import json
from pathlib import Path


def generate(timeline_path, pitch_path, audio_path, output):
    import numpy as np
    timeline=json.loads(Path(timeline_path).read_text(encoding='utf-8'))
    p=np.load(pitch_path)
    pts=[{'t':round(float(t),3),'m':round(float(m),2)} for t,m in zip(p['time'],p['midi']) if np.isfinite(m)]
    data=json.dumps({'lines':timeline['lines'],'pitch':pts},ensure_ascii=False).replace('</','<\\/')
    # Relative local audio URL; browser may require running the local HTTP server.
    audio=html.escape(os.path.relpath(str(Path(audio_path).resolve()),str(Path(output).resolve().parent)).replace(os.sep,"/"),quote=True)
    page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Karaoke Phase 0 Preview</title>
<style>body{background:#101827;color:#eee;font-family:system-ui;margin:25px}main{max-width:1100px;margin:auto}#lyrics{font-size:30px;text-align:center;margin:35px 0;min-height:75px}.token{color:#aaa}.done{color:#ffcb40}.current{color:#ffcb40;text-decoration:underline}canvas{background:#1b263b;width:100%;height:260px}audio{width:100%}.note{color:#aaa}</style>
<main><h2>Phase 0 · Lyrics + Pitch Verification</h2><p class="note">Experimental output. Review AI timestamps against audio; no scoring is performed.</p>
<audio id="player" controls src="AUDIO_PATH"></audio><div id="lyrics">等待播放</div><canvas id="plot" width="1100" height="260"></canvas>
<p id="status"></p></main><script>const DATA=PAYLOAD;const player=document.getElementById('player'),label=document.getElementById('lyrics'),canvas=document.getElementById('plot'),ctx=canvas.getContext('2d');
function draw(){let t=player.currentTime,lines=DATA.lines;let active=lines.find(l=>t>=l.start&&t<=l.end)||lines.filter(l=>l.start<=t).at(-1);if(active){let tokens=active.tokens||[];label.innerHTML=tokens.length?tokens.map(c=>{let v=t>=c.end?'done':t>=c.start?'current':'token';return '<span class="'+v+'">'+escapeHtml(c.char||c.word||'')+'</span>'}).join(''):escapeHtml(active.text);}ctx.clearRect(0,0,1100,260);ctx.strokeStyle='#3d5068';for(let y=20;y<260;y+=40){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1100,y);ctx.stroke()}let left=t-2.8;ctx.fillStyle='#4e9bf5';for(const p of DATA.pitch){let x=(p.t-left)*137.5;if(x<0||x>1100)continue;let y=250-(p.m-42)*5;if(y<0||y>260)continue;ctx.fillRect(x,y,2,3)}ctx.strokeStyle='#facc15';ctx.beginPath();ctx.moveTo(385,0);ctx.lineTo(385,260);ctx.stroke();document.getElementById('status').textContent='Song time '+t.toFixed(2)+'s | '+lines.length+' aligned lines | '+DATA.pitch.length+' pitch frames';requestAnimationFrame(draw)}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}requestAnimationFrame(draw);</script></html>'''
    Path(output).write_text(page.replace('AUDIO_PATH',audio).replace('PAYLOAD',data),encoding='utf-8')
