"""Generate a local-server Lyrics QA page; audio is loaded automatically."""
import json
from pathlib import Path


def render(timeline, output, word_timings=None, player_mode=False, reference_pitch=None, vocal_activity=None):
    timeline = dict(timeline)
    timeline["word_timings"] = word_timings or {}
    timeline["player_mode"] = bool(player_mode)
    timeline["reference_pitch"] = reference_pitch or {"frames": []}
    timeline["vocal_activity"] = vocal_activity or {"frames": []}
    payload = json.dumps(timeline, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    page = r'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Karaoke Lyrics QA</title>
<style>
body{background:#101827;color:#f3f4f6;font:16px system-ui;margin:25px auto;max-width:1000px;padding:0 16px}
audio{width:100%}.player-controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:16px 0}.player-controls label{display:flex;gap:7px;align-items:center}.player-controls input[type=range]{width:125px}.player-controls button{padding:8px 14px;border-radius:8px;background:#2563eb;color:white;border:0;cursor:pointer}.player-controls button:disabled{opacity:.5}.player-controls[hidden]{display:none}.modes{display:flex;gap:8px;margin:12px 0}.modes button{padding:9px 16px;border:1px solid #64748b;border-radius:8px;background:#1e293b;color:white;cursor:pointer}.modes button.selected{background:#2563eb;border-color:#60a5fa}#line{font-size:36px;min-height:85px;text-align:center;margin:35px 0}
.word{color:#9ca3af}.done,.active{color:#facc15}.active{text-decoration:underline}
table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #334155;text-align:left}
small,.muted{color:#aab4c2}.warn{color:#fbbf24}.issue{display:block;width:100%;background:#1e293b;border:1px solid #334155;color:#f3f4f6;padding:10px;margin:7px 0;text-align:left;border-radius:6px;cursor:pointer}
.pitch-panel{margin-top:14px;padding:12px;border:1px solid #334155;border-radius:8px;background:#0f172a}.pitch-stats{display:flex;gap:24px;flex-wrap:wrap;margin:8px 0}.pitch-stats strong{font-size:22px;color:#67e8f9}#pitchCanvas{width:100%;height:140px;background:#0b1220;border-radius:6px}.mic-panel{padding:14px;border:1px solid #334155;border-radius:10px;margin:16px 0}.mic-panel[hidden]{display:none}.mic-panel label{display:inline-flex;gap:8px;align-items:center;margin:7px 12px 7px 0}.mic-panel select{max-width:300px;background:#1e293b;color:white;padding:7px}.mic-panel button{padding:8px 12px;background:#2563eb;color:white;border:0;border-radius:7px;cursor:pointer}.mic-panel meter{width:180px;height:16px;vertical-align:middle}.issue:hover,tr:hover{background:#29374e}tr{cursor:pointer}#status{color:#aab4c2}
</style>
<h2>Phase 0.3 · Lyrics Alignment QA</h2>
<p class="muted">Vocal audio loads automatically. Press Play to review provisional timestamps.</p>
<audio controls preload="metadata" id="audio" src="/vocals.wav"></audio>
<div id="playerControls" class="player-controls" hidden>
<button id="togglePlay" type="button">Play</button><button id="restart" type="button">Restart</button>
<label>Seek <input id="seek" type="range" min="0" max="100" value="0" step="0.1"></label>
<label>Instrumental <input id="instrumentalVolume" type="range" min="0" max="100" value="100"></label>
<label>Original vocal <input id="vocalVolume" type="range" min="0" max="100" value="0"></label>
<span id="playerClock">0:00</span></div>
<section id="microphonePanel" class="mic-panel" hidden aria-label="Microphone controls">
<strong>Microphone</strong><p class="muted">Mic access is local to your browser. Monitoring is OFF by default; use headphones if enabling it.</p>
<label>Input device <select id="micDevice" aria-label="Microphone input"><option value="">Default microphone</option></select></label>
<button id="micStart" type="button">Enable Mic</button>
<button id="micStop" type="button" disabled>Disable Mic</button>
<div><label>Input level <meter id="micLevel" min="0" max="1" value="0"></meter> <span id="micDb">−∞ dBFS</span></label></div>
<label>Mic Gain <input id="micGain" type="range" min="0" max="200" value="100" aria-label="Mic Gain"></label>
<label>Mute <input id="micMute" type="checkbox"></label>
<label>Monitoring <input id="micMonitor" type="checkbox"></label>
<p id="micStatus" role="status" class="muted">Microphone disabled</p>
<div class="pitch-panel" aria-label="Live pitch detection">
<strong>Live Pitch (microphone)</strong>
<label>Detector <select id="pitchDetector" aria-label="Pitch detector"><option value="crepe">torchcrepe (local Python)</option><option value="yin">YIN (browser)</option></select></label>
<span id="pitchBackendStatus" class="muted" role="status">YIN ready</span>
<label class="pitch-smoothing">torchcrepe smoothing (5 frames) <input id="crepeSmoothing" type="checkbox" checked aria-label="Enable torchcrepe 5-frame median smoothing"></label>
<label class="pitch-sensitivity">Pitch sensitivity <input id="pitchThreshold" type="range" min="-60" max="-20" step="1" value="-38" aria-label="Pitch detection minimum input level"> <output id="pitchThresholdValue">−38 dBFS</output></label>
<div class="pitch-stats"><div>Frequency <strong id="pitchHz">Unvoiced</strong></div><div>Note <strong id="pitchNote">—</strong></div></div>
<label>Reference smoothing (5 frames) <input id="referenceSmoothing" type="checkbox" checked></label>
<label>Auto timing sync <input id="autoTimingSync" type="checkbox" checked></label> <span id="autoTimingStatus" aria-live="polite">Collecting pitch history</span>
<label>Mic timing offset <input id="micTimingOffset" type="range" min="-500" max="500" step="10" value="0"> <output id="micTimingValue">0 ms</output></label>
<div class="pitch-stats" aria-label="Reference pitch comparison"><div>Reference <strong id="referenceHz">—</strong></div><div>Difference <strong id="pitchDifference">—</strong></div></div>
<div><button id="startPitchCapture" type="button">Start pitch capture</button> <button id="stopPitchCapture" type="button" disabled>Stop &amp; download CSV</button> <span id="pitchCaptureStatus">Not recording</span></div>
<section id="singingScorePanel" aria-label="Singing score results" style="display:none;border:1px solid #334155;padding:12px;margin:10px 0;border-radius:8px" aria-live="polite">
<strong>Experimental singing results</strong><div class="pitch-stats"><div>Pitch Accuracy <strong id="scoreAccuracy">—</strong></div><div>Singing Coverage <strong id="scoreCoverage">—</strong></div></div>
<div class="pitch-stats"><div>Note-Based v2 <strong id="scoreNoteV2">—</strong></div><div>Note Coverage <strong id="scoreNoteCoverage">—</strong></div><div>Unscored Notes <strong id="scoreUnscoredNotes">—</strong></div></div><p id="scoreNoteDetails" class="muted"></p><p id="scoreDetails" class="muted"></p><small>Pitch accuracy uses matched voiced frames. Coverage is an estimated reference vocal-activity ratio. No overall score.</small>
</section>
<canvas id="pitchCanvas" width="760" height="140" aria-label="Recent microphone pitch history"></canvas>
<p class="muted">Live F0 estimate; experimental scores appear after stopping pitch capture. Use headphones to avoid music leaking into the mic.</p>
</div>
</section><p id="status"></p>
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
  document.getElementById('microphonePanel').hidden=false;
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
// Microphone input stays local. Meter taps the raw mic input; monitor is opt-in.
let micStream=null,micContext=null,micSource=null,micGainNode=null,micAnalyser=null,micMonitorNode=null;
let micFrame=0;
const pitchHz=document.getElementById('pitchHz'),pitchNote=document.getElementById('pitchNote');
const pitchCanvas=document.getElementById('pitchCanvas');
const pitchHistory=[];let lastPitchUpdate=0;
const pitchDetector=document.getElementById('pitchDetector');
const pitchBackendStatus=document.getElementById('pitchBackendStatus');
const crepeSmoothing=document.getElementById('crepeSmoothing');
const crepePitchWindow=[];
const referenceFrames=Array.isArray(DATA.reference_pitch?.frames)?DATA.reference_pitch.frames:[];
const vocalActivityFrames=Array.isArray(DATA.vocal_activity?.frames)?DATA.vocal_activity.frames:[];
const referenceHz=document.getElementById('referenceHz');
const pitchDifference=document.getElementById('pitchDifference');
const referenceSmoothing=document.getElementById('referenceSmoothing');
const micTimingOffset=document.getElementById('micTimingOffset');
const micTimingValue=document.getElementById('micTimingValue');
const autoTimingSync=document.getElementById('autoTimingSync'),autoTimingStatus=document.getElementById('autoTimingStatus');
const micPitchSamples=[];let estimatedOffsetMs=0,offsetTrusted=false,lastAutoEstimate=0;
// Record pitch with its aligned reference timeline. CSV stays in the browser until downloaded.
const pitchCapture=[];let pitchCapturing=false,lastCaptureTime=-1;
const captureStart=document.getElementById('startPitchCapture'),captureStop=document.getElementById('stopPitchCapture'),captureStatus=document.getElementById('pitchCaptureStatus');
captureStart.onclick=()=>{document.getElementById('singingScorePanel').style.display='none';pitchCapture.length=0;lastCaptureTime=-1;pitchCapturing=true;captureStart.disabled=true;captureStop.disabled=false;captureStatus.textContent='Recording pitch…'};
function csvCell(v){return v===null||v===undefined?'':String(v)}
captureStop.onclick=()=>{
  pitchCapturing=false;captureStart.disabled=false;captureStop.disabled=true;
  const columns=['time_s','crepe_hz','crepe_periodicity','playback_time_s','offset_ms','offset_trusted','detector'];
  const rows=[columns.join(',')].concat(pitchCapture.map(p=>columns.map(k=>csvCell(p[k])).join(',')));
  const blob=new Blob([rows.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='karaoke_pitch_capture_'+Date.now()+'.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
  captureStatus.textContent=pitchCapture.length+' samples saved';showCaptureScore();
};
// Browser preview mirrors the offline experimental scoring rules (no overall score).
// Use the captured, already aligned time_s; do not apply offset_ms a second time.
function nearestFrame(frames,t,tolerance){
  let lo=0,hi=frames.length;
  while(lo<hi){const mid=(lo+hi)>>>1;if(Number(frames[mid].time)<t)lo=mid+1;else hi=mid}
  let best=null,dist=Infinity;
  for(const k of [lo-1,lo])if(k>=0&&k<frames.length){const d=Math.abs(Number(frames[k].time)-t);if(d<dist){dist=d;best=frames[k]}}
  return dist<=tolerance?best:null;
}
function scoreCapturedFrames(captured,reference,mask){
  let matched=0,scoreSum=0,expected=0,userVoiced=0,referenceUnvoiced=0;
  for(const row of captured){
    const t=Number(row.time_s),hz=Number(row.crepe_hz),conf=row.crepe_periodicity===''?null:Number(row.crepe_periodicity);
    if(!Number.isFinite(t))continue;
    const goodUser=row.crepe_hz!==''&&Number.isFinite(hz)&&hz>0&&(conf===null||conf>=0.35);
    const activity=nearestFrame(mask,t,0.06);
    if(activity&&activity.active){expected++;if(goodUser)userVoiced++}
    if(!goodUser)continue;
    const ref=nearestFrame(reference,t,0.04);
    if(!ref)continue;
    const refHz=Number(ref.hz),refConf=ref.periodicity==null?null:Number(ref.periodicity);
    if(ref.hz==null||!Number.isFinite(refHz)||refHz<=0||(refConf!==null&&refConf<0.35)){referenceUnvoiced++;continue}
    const cents=Math.abs(1200*Math.log2(hz/refHz));
    scoreSum+=cents<=50?100:Math.max(0,100*(300-cents)/250);
    matched++;
  }
  return {pitchScore:matched?scoreSum/matched:null,coverage:expected?userVoiced/expected:null,
          matched,expected,userVoiced,referenceUnvoiced,total:captured.length};
}
// Experimental note segmentation v2 ported from benchmark_note_scoring_v2.py.
// Scores only successfully matched candidate notes; missing notes remain unscored.
function noteCents(a,b){return 1200*Math.log2(b/a)}
function noteMedian(values){const a=[...values].sort((x,y)=>x-y),n=a.length;return n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2}
function validNoteHz(v){if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)&&x>0?x:null}
function segmentReferenceNotesV2(frames,start,end){
  const selected=frames.filter(f=>Number(f.time)>=start&&Number(f.time)<=end).slice().sort((a,b)=>Number(a.time)-Number(b.time));
  const values=selected.map((f,i)=>{
    const v=validNoteHz(f.hz),p=f.periodicity;
    if(v===null||(p!==null&&p!==undefined&&Number(p)<.35))return null;
    const nearby=[];
    for(let j=Math.max(0,i-2);j<Math.min(selected.length,i+3);j++){
      const q=selected[j],qv=validNoteHz(q.hz),qp=q.periodicity;
      if(qv!==null&&(qp===null||qp===undefined||Number(qp)>=.35)&&Math.abs(Number(q.time)-Number(f.time))<=.065&&Math.abs(noteCents(v,qv))<=180)nearby.push(Math.log2(qv));
    }
    return nearby.length?2**noteMedian(nearby):v;
  });
  const groups=[];let current=[];
  function flush(){if(!current.length)return;
    const duration=current[current.length-1][0]-current[0][0]+.02;
    if(duration>=.22&&current.length>=3)groups.push({start:current[0][0],end:Math.min(end,current[current.length-1][0]+.02),reference_hz:noteMedian(current.map(x=>x[1])),reference_frames:current.length});
  }
  for(let i=0;i<selected.length;i++){
    const v=values[i];if(v===null)continue;
    const t=Number(selected[i].time);
    if(current.length&&(t-current[current.length-1][0]>.12||Math.abs(noteCents(noteMedian(current.slice(-12).map(x=>x[1])),v))>110)){flush();current=[]}
    current.push([t,v]);
  }
  flush();
  const merged=[];
  for(const note of groups){
    const prev=merged[merged.length-1];
    if(prev&&note.start-prev.end<=.12&&Math.abs(noteCents(prev.reference_hz,note.reference_hz))<=55){
      prev.reference_hz=2**((Math.log2(prev.reference_hz)*prev.reference_frames+Math.log2(note.reference_hz)*note.reference_frames)/(prev.reference_frames+note.reference_frames));
      prev.end=note.end;prev.reference_frames+=note.reference_frames;
    }else merged.push({...note});
  }
  return merged;
}
function scoreCapturedNotesV2(captured,reference){
  const users=captured.map(r=>({time:Number(r.time_s),hz:validNoteHz(r.crepe_hz),periodicity:r.crepe_periodicity===''?null:Number(r.crepe_periodicity)})).filter(r=>Number.isFinite(r.time)).sort((a,b)=>a.time-b.time);
  if(users.length<2)return {score:null,coverage:null,referenceNotes:0,scoredNotes:0,unscoredNotes:0};
  const notes=segmentReferenceNotesV2(reference,Math.max(0,users[0].time),users[users.length-1].time);
  let total=0,scored=0;
  for(const note of notes){
    const lo=note.start+.06,hi=note.end-.06;
    if(hi<=lo)continue;
    const valid=users.filter(u=>u.time>=lo&&u.time<=hi&&u.hz!==null&&(u.periodicity===null||u.periodicity>=.35)).map(u=>u.hz);
    if(valid.length<3)continue;
    const err=Math.abs(noteCents(note.reference_hz,noteMedian(valid)));
    total+=Math.max(0,Math.min(100,100*(300-Math.max(50,err))/250));scored++;
  }
  return {score:scored?total/scored:null,coverage:notes.length?scored/notes.length:null,referenceNotes:notes.length,scoredNotes:scored,unscoredNotes:notes.length-scored};
}
function showCaptureScore(){
  const panel=document.getElementById('singingScorePanel');panel.style.display='block';
  const result=scoreCapturedFrames(pitchCapture,referenceFrames,vocalActivityFrames);
  document.getElementById('scoreAccuracy').textContent=result.pitchScore===null?'Not available':result.pitchScore.toFixed(2)+' / 100';
  document.getElementById('scoreCoverage').textContent=result.coverage===null?'Mask missing':(100*result.coverage).toFixed(2)+'%';
  const noteResult=scoreCapturedNotesV2(pitchCapture,referenceFrames);
  document.getElementById('scoreNoteV2').textContent=noteResult.score===null?'Not available':noteResult.score.toFixed(2)+' / 100';
  document.getElementById('scoreNoteCoverage').textContent=noteResult.coverage===null?'Not available':(100*noteResult.coverage).toFixed(2)+'%';
  document.getElementById('scoreUnscoredNotes').textContent=String(noteResult.unscoredNotes);
  document.getElementById('scoreNoteDetails').textContent=`${noteResult.scoredNotes}/${noteResult.referenceNotes} candidate notes scored. Experimental; no verified melody ground truth.`;
  document.getElementById('scoreDetails').textContent=`${result.matched} matched pitch frames; ${result.userVoiced}/${result.expected} expected singing frames voiced; ${result.total} recorded frames.`;
}
function recordPitchSample(hz,periodicity){
  if(!pitchCapturing||!micStream||!playerMode||instrumental.paused)return;
  const t=instrumental.currentTime;
  if(lastCaptureTime>=0&&t<lastCaptureTime-0.1){pitchCapturing=false;captureStart.disabled=false;captureStop.disabled=false;captureStatus.textContent='Seek detected: stop & download this segment';return}
  lastCaptureTime=t;
  const trusted=autoTimingSync.checked&&offsetTrusted;
  const offset=autoTimingSync.checked?(trusted?estimatedOffsetMs:0):Number(micTimingOffset.value);
  pitchCapture.push({time_s:(t-offset/1000).toFixed(4),crepe_hz:hz>0?hz.toFixed(3):'',crepe_periodicity:Number.isFinite(periodicity)?periodicity.toFixed(4):'',playback_time_s:t.toFixed(4),offset_ms:offset,offset_trusted:trusted?1:0,detector:pitchDetector.value});
  captureStatus.textContent='Recording '+pitchCapture.length+' frames';
}

function resetAutoSync(){micPitchSamples.length=0;estimatedOffsetMs=0;offsetTrusted=false;lastAutoEstimate=0;autoTimingStatus.textContent='Collecting pitch history'}
autoTimingSync.onchange=()=>{resetAutoSync();micTimingOffset.disabled=autoTimingSync.checked;updateReference()};
micTimingOffset.disabled=true;
micTimingOffset.oninput=()=>{micTimingValue.textContent=micTimingOffset.value+' ms';updateReference()};
referenceSmoothing.onchange=()=>updateReference();
let currentMicHz=null,lastMicMeasurementAt=null;
// Search actual timestamps: chunked extraction can duplicate boundary frames.
function referenceIndex(t){
  let lo=0,hi=referenceFrames.length;
  while(lo<hi){const mid=(lo+hi)>>>1;if(referenceFrames[mid].time<t)lo=mid+1;else hi=mid}
  if(lo===0)return 0;
  if(lo===referenceFrames.length)return lo-1;
  return Math.abs(referenceFrames[lo-1].time-t)<=Math.abs(referenceFrames[lo].time-t)?lo-1:lo;
}
function referenceAt(t){
  if(!Number.isFinite(t)||t<0||!referenceFrames.length)return null;
  const k=referenceIndex(t),center=referenceFrames[k];
  if(Math.abs(center.time-t)>0.075)return null;
  if(!referenceSmoothing.checked)return center.hz>0?center.hz:null;
  // Centered 5-frame median; never bridge silence or gaps in the reference.
  const values=[];
  for(let i=k-2;i<=k+2;i++){
    const f=referenceFrames[i];
    if(!f||!(f.hz>0)||Math.abs(f.time-center.time)>0.055)return center.hz>0?center.hz:null;
    values.push(f.hz);
  }
  values.sort((a,b)=>a-b);
  return values[2];
}
function updateReference(){
  const t=playerMode&&instrumental?instrumental.currentTime:audio.currentTime;
  // Offset is microphone capture delay relative to playback; positive means
  // the mic sample belongs to an earlier point in the song.
  const offset=autoTimingSync.checked?(offsetTrusted?estimatedOffsetMs:0):Number(micTimingOffset.value);
  const alignedTime=t-offset/1000;
  const f=referenceAt(alignedTime);
  referenceHz.textContent=f>0?f.toFixed(1)+' Hz':'Unvoiced';
  // Do not show a stale pitch difference after singing stops or mic is disabled.
  const fresh=lastMicMeasurementAt!==null&&performance.now()-lastMicMeasurementAt<350;
  if(f>0&&currentMicHz>0&&fresh&&(!playerMode||!instrumental.paused)){
    const cents=1200*Math.log2(currentMicHz/f);
    pitchDifference.textContent=(cents>=0?'+':'')+cents.toFixed(0)+' cents';
  }else pitchDifference.textContent='—';
}
setInterval(updateReference,100);
// Causal median: only previously received F0 samples, no look-ahead latency.
// Unvoiced frames reset the window, so we never manufacture voiced pitches.
function medianPitchFrame(hz, enabled){
  if(hz===null || !Number.isFinite(hz) || hz<=0){crepePitchWindow.length=0;return null}
  crepePitchWindow.push(hz);
  if(crepePitchWindow.length>5)crepePitchWindow.shift();
  if(!enabled)return hz;
  const sorted=[...crepePitchWindow].sort((a,b)=>a-b);
  return sorted[Math.floor(sorted.length/2)];
}
crepeSmoothing.onchange=()=>{crepePitchWindow.length=0};
let pitchSocket=null,pitchSocketGeneration=0,lastCrepeResult=0;
// Estimate a single lag from the *shape* of the pitch contour, not absolute
// pitch error. Flat sustained notes and ambiguous matches cannot calibrate.
function estimateAutomaticOffset(){
  if(!autoTimingSync.checked||micPitchSamples.length<35)return;
  const samples=micPitchSamples.filter(x=>x.hz>0&&Number.isFinite(x.t));
  if(samples.length<35){autoTimingStatus.textContent='Waiting for voiced notes';return}
  const span=samples.at(-1).t-samples[0].t;
  if(span<5){autoTimingStatus.textContent='Waiting for pitch changes';return}
  const points=[];
  for(let i=2;i<samples.length;i+=2){
    const a=samples[i-2],b=samples[i];
    if(b.t-a.t<0.08||b.t-a.t>0.6)continue;
    const delta=1200*Math.log2(b.hz/a.hz);
    if(Math.abs(delta)>=35&&Math.abs(delta)<700)points.push({a:a.t,b:b.t,delta});
  }
  if(points.length<9){autoTimingStatus.textContent='Need more pitch changes';return}
  const candidates=[];
  for(let offset=-400;offset<=400;offset+=25){
    let loss=0,n=0;
    for(const pt of points){
      const x=referenceAt(pt.a-offset/1000),y=referenceAt(pt.b-offset/1000);
      if(!(x>0&&y>0))continue;
      const refDelta=1200*Math.log2(y/x);
      if(Math.abs(refDelta)>900)continue;
      loss+=Math.min(250,Math.abs(pt.delta-refDelta));n++;
    }
    if(n>=9) candidates.push({offset,loss:loss/n,n});
  }
  if(candidates.length<8){autoTimingStatus.textContent='Insufficient matching reference';return}
  candidates.sort((a,b)=>a.loss-b.loss);
  const best=candidates[0];
  const separated=candidates.filter(x=>Math.abs(x.offset-best.offset)>=150);
  const alternative=separated.length?separated[0]:null;
  // Conservative acceptance: reject weak or nearly equivalent lag matches.
  if(!alternative||best.loss>85||alternative.loss-best.loss<12){
    autoTimingStatus.textContent=offsetTrusted?'Auto '+estimatedOffsetMs+' ms (holding)':'Ambiguous timing; using 0 ms';return;
  }
  estimatedOffsetMs=best.offset;offsetTrusted=true;
  autoTimingStatus.textContent='Auto '+estimatedOffsetMs+' ms';
}
function showPitch(hz){
  if(autoTimingSync.checked&&hz>0&&micStream&&(!playerMode||!instrumental.paused)){
    const t=playerMode&&instrumental?instrumental.currentTime:audio.currentTime;
    if(micPitchSamples.length&&t<micPitchSamples.at(-1).t-0.25)resetAutoSync();
    micPitchSamples.push({t,hz});
    while(micPitchSamples.length>180||micPitchSamples.length&&t-micPitchSamples[0].t>14)micPitchSamples.shift();
    if(performance.now()-lastAutoEstimate>1500){lastAutoEstimate=performance.now();estimateAutomaticOffset()}
  }
  currentMicHz=hz;lastMicMeasurementAt=performance.now();updateReference();
  pitchHz.textContent=hz===null?'Unvoiced':hz.toFixed(1)+' Hz';
  pitchNote.textContent=pitchToNote(hz);
  pitchHistory.push(hz);if(pitchHistory.length>120)pitchHistory.shift();drawPitch();
}
function closePitchSocket(){
  pitchSocketGeneration++;
  if(pitchSocket){const ws=pitchSocket;pitchSocket=null;ws.close()}
}
function connectPitchSocket(){
  closePitchSocket();
  if(pitchDetector.value!=='crepe'||!micStream)return;
  const generation=pitchSocketGeneration;
  const ws=new WebSocket('ws://127.0.0.1:8766');pitchSocket=ws;
  pitchBackendStatus.textContent='Connecting to local torchcrepe…';
  ws.onopen=()=>{if(generation===pitchSocketGeneration)pitchBackendStatus.textContent='torchcrepe connected'};
  ws.onmessage=e=>{
    if(generation!==pitchSocketGeneration)return;
    try{
      const data=JSON.parse(e.data);
      if(data.error){pitchBackendStatus.textContent=data.error;showPitch(null);return}
      lastCrepeResult=performance.now();
      const rawHz=typeof data.hz==='number'&&Number.isFinite(data.hz)&&data.hz>0?data.hz:null;
      showPitch(medianPitchFrame(rawHz,crepeSmoothing.checked));recordPitchSample(rawHz,Number(data.periodicity));
      pitchBackendStatus.textContent='torchcrepe · periodicity '+Number(data.periodicity||0).toFixed(2);
    }catch(err){pitchBackendStatus.textContent='Invalid pitch response'}
  };
  ws.onerror=()=>{if(generation===pitchSocketGeneration)pitchBackendStatus.textContent='Start local backend: python tools/run_live_torchcrepe.py'};
  ws.onclose=()=>{if(generation===pitchSocketGeneration)pitchBackendStatus.textContent='torchcrepe disconnected'};
}
pitchDetector.onchange=()=>{resetPitch();if(pitchDetector.value==='crepe')connectPitchSocket();else{closePitchSocket();pitchBackendStatus.textContent='YIN ready'}};

const pitchThreshold=document.getElementById('pitchThreshold'),pitchThresholdValue=document.getElementById('pitchThresholdValue');
function pitchMinimumRms(){return Math.pow(10,Number(pitchThreshold.value)/20)}
function updatePitchThresholdLabel(){pitchThresholdValue.textContent=pitchThreshold.value+' dBFS'}
pitchThreshold.addEventListener('input',updatePitchThresholdLabel);updatePitchThresholdLabel();
// YIN cumulative mean normalized difference: return null for silence/unvoiced/noisy input.
function detectPitch(samples,sampleRate,minRms=0.012){
  const n=samples.length;let energy=0,mean=0;
  for(const x of samples){energy+=x*x;mean+=x}
  const rms=Math.sqrt(energy/n);
  if(rms<minRms)return null;
  mean/=n;
  const minLag=Math.max(2,Math.floor(sampleRate/900));
  const maxLag=Math.min(Math.floor(sampleRate/75),Math.floor(n/2)-1);
  if(maxLag<=minLag)return null;
  const diff=new Float64Array(maxLag+1);const window=Math.min(Math.floor(n/2),2048);
  for(let lag=1;lag<=maxLag;lag++){
    let sum=0;
    for(let i=0;i<window;i++){
      const delta=(samples[i]-mean)-(samples[i+lag]-mean);
      sum+=delta*delta;
    }
    diff[lag]=sum;
  }
  const normalized=new Float64Array(maxLag+1);
  let cumulative=0;let best=-1;
  for(let lag=1;lag<=maxLag;lag++){
    cumulative+=diff[lag];
    const cmnd=cumulative>0?diff[lag]*lag/cumulative:1;
    normalized[lag]=cmnd;
  }
  for(let lag=minLag;lag<=maxLag;lag++){
    if(normalized[lag]<0.15){
      best=lag;
      while(best+1<=maxLag&&normalized[best+1]<normalized[best])best++;
      break;
    }
  }
  if(best<0||normalized[best]>0.15)return null;
  let lag=best;
  if(best>1&&best<maxLag){
    const a=normalized[best-1],b=normalized[best],c=normalized[best+1];
    const denom=a-2*b+c;
    if(Math.abs(denom)>1e-10)lag+=Math.max(-1,Math.min(1,0.5*(a-c)/denom));
  }
  const hz=sampleRate/lag;
  return Number.isFinite(hz)&&hz>=75&&hz<=900?hz:null;
}
function pitchToNote(hz){
  if(hz===null)return '—';
  const midi=Math.round(69+12*Math.log2(hz/440));
  return ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][(midi+120)%12]+(Math.floor(midi/12)-1);
}
function drawPitch(){
  const ctx=pitchCanvas.getContext('2d');if(!ctx)return;
  const w=pitchCanvas.width,h=pitchCanvas.height;
  ctx.clearRect(0,0,w,h);ctx.strokeStyle='#334155';ctx.lineWidth=1;
  for(let i=1;i<4;i++){const y=i*h/4;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
  ctx.strokeStyle='#67e8f9';ctx.lineWidth=2;ctx.beginPath();let active=false;
  for(let i=0;i<pitchHistory.length;i++){
    const hz=pitchHistory[i];if(hz===null){active=false;continue}
    const x=i/(120-1)*w;
    const y=h-(Math.log2(hz/75)/Math.log2(900/75))*h;
    if(!active)ctx.moveTo(x,y);else ctx.lineTo(x,y);
    active=true;
  }
  ctx.stroke();
}
function resetPitch(){resetAutoSync();crepePitchWindow.length=0;pitchHistory.length=0;currentMicHz=null;lastMicMeasurementAt=null;pitchHz.textContent='Unvoiced';pitchNote.textContent='—';lastPitchUpdate=0;drawPitch()}

const micDevice=document.getElementById('micDevice');
const micStart=document.getElementById('micStart'),micStop=document.getElementById('micStop');
const micGain=document.getElementById('micGain'),micMute=document.getElementById('micMute');
const micMonitor=document.getElementById('micMonitor'),micStatus=document.getElementById('micStatus');
const micLevel=document.getElementById('micLevel'),micDb=document.getElementById('micDb');
async function listMicrophones(){
  if(!navigator.mediaDevices?.enumerateDevices)return;
  try{
    const devices=(await navigator.mediaDevices.enumerateDevices()).filter(x=>x.kind==='audioinput');
    const selected=micDevice.value;
    micDevice.replaceChildren(new Option('Default microphone',''));
    for(const [i,d] of devices.entries())micDevice.add(new Option(d.label||'Microphone '+(i+1),d.deviceId));
    if([...micDevice.options].some(x=>x.value===selected))micDevice.value=selected;
  }catch(e){micStatus.textContent='Cannot list microphones: '+e.message}
}
function updateMicGain(){if(micGainNode)micGainNode.gain.value=micMute.checked?0:Number(micGain.value)/100}
function updateMicMonitor(){if(micMonitorNode)micMonitorNode.gain.value=micMonitor.checked?1:0}
function meterFrame(){
  if(!micAnalyser)return;
  const samples=new Float32Array(micAnalyser.fftSize);micAnalyser.getFloatTimeDomainData(samples);
  let sum=0;for(const x of samples)sum+=x*x;
  const rms=Math.sqrt(sum/samples.length),db=rms>0?20*Math.log10(rms):-Infinity;
  micLevel.value=Math.min(1,rms*5);micDb.textContent=Number.isFinite(db)?db.toFixed(1)+' dBFS':'−∞ dBFS';
  if(performance.now()-lastPitchUpdate>=85){
    lastPitchUpdate=performance.now();
    if(pitchDetector.value==='yin'){
      const yinHz=detectPitch(samples,micContext.sampleRate,pitchMinimumRms());showPitch(yinHz);recordPitchSample(yinHz,null);
    }else if(pitchSocket?.readyState===WebSocket.OPEN){
      // Send the latest raw microphone snapshot. Backend handles downsampling,
      // buffering and inference; no audio is uploaded to the internet.
      if(pitchSocket.bufferedAmount<32768){
        const packet=new ArrayBuffer(4+samples.length*4);
        const view=new DataView(packet);view.setUint32(0,micContext.sampleRate,true);
        new Float32Array(packet,4).set(samples);
        pitchSocket.send(packet);
      }
      if(performance.now()-lastCrepeResult>1200){showPitch(null);pitchBackendStatus.textContent='Waiting for torchcrepe inference'}
    }
  }
  micFrame=requestAnimationFrame(meterFrame);
}
async function stopMicrophone(){
  closePitchSocket();
  cancelAnimationFrame(micFrame);micFrame=0;
  if(micStream)micStream.getTracks().forEach(t=>t.stop());
  micStream=null;micAnalyser=null;micSource=null;micGainNode=null;micMonitorNode=null;
  if(micContext){const ctx=micContext;micContext=null;await ctx.close().catch(()=>{})}
  resetPitch();micLevel.value=0;micDb.textContent='−∞ dBFS';micStart.disabled=false;micStop.disabled=true;
  micMonitor.checked=false;micStatus.textContent='Microphone disabled';
}
async function startMicrophone(){
  if(micStream)return;
  if(!navigator.mediaDevices?.getUserMedia){micStatus.textContent='Microphone requires localhost or a secure HTTPS context.';return}
  micStart.disabled=true;micStatus.textContent='Requesting microphone permission…';
  try{
    const deviceId=micDevice.value;
    micStream=await navigator.mediaDevices.getUserMedia({audio:{deviceId:deviceId?{exact:deviceId}:undefined,echoCancellation:true,noiseSuppression:true},video:false});
    const AudioCtx=window.AudioContext||window.webkitAudioContext;
    micContext=new AudioCtx();await micContext.resume();
    micSource=micContext.createMediaStreamSource(micStream);
    micAnalyser=micContext.createAnalyser();micAnalyser.fftSize=4096;
    micGainNode=micContext.createGain();micMonitorNode=micContext.createGain();
    micSource.connect(micAnalyser);micSource.connect(micGainNode);
    micGainNode.connect(micMonitorNode);micMonitorNode.connect(micContext.destination);
    updateMicGain();updateMicMonitor();micStop.disabled=false;
    micStatus.textContent='Microphone active (local only)';if(pitchDetector.value==='crepe')connectPitchSocket();meterFrame();await listMicrophones();
    micStream.getAudioTracks()[0]?.addEventListener('ended',()=>{stopMicrophone()});
  }catch(e){await stopMicrophone();micStatus.textContent='Microphone unavailable: '+e.message}
}
micStart.onclick=startMicrophone;micStop.onclick=()=>stopMicrophone();
micGain.oninput=updateMicGain;micMute.onchange=updateMicGain;micMonitor.onchange=updateMicMonitor;
micDevice.onchange=async()=>{if(micStream){await stopMicrophone();await startMicrophone()}};
if(playerMode){listMicrophones();navigator.mediaDevices?.addEventListener?.('devicechange',listMicrophones)}
window.addEventListener('pagehide',()=>{if(micStream)micStream.getTracks().forEach(t=>t.stop());if(micContext)micContext.close().catch(()=>{})});

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
