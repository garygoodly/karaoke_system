import json
import re
import subprocess
from pathlib import Path

import numpy as np


def probe(path):
    p = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,bit_rate',
                        '-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)['format']


def parse_lyrics(path):
    raw = Path(path).read_text(encoding='utf-8-sig')
    lines = []
    for text in raw.splitlines():
        text = text.strip()
        if not text or re.match(r'^\[(ar|ti|al|by|offset):',text,re.I):
            continue
        hits = list(re.finditer(r'\[(\d+):(\d+(?:\.\d+)?)\]',text))
        lyric = re.sub(r'\[\d+:\d+(?:\.\d+)?\]','',text).strip()
        if not lyric:
            continue
        if hits:
            for h in hits:
                lines.append({'text':lyric,'hint_start':int(h.group(1))*60+float(h.group(2))})
        else:
            lines.append({'text':lyric,'hint_start':None})
    return lines


def separate(song, out, device='cpu'):
    out = Path(out)
    cmd = ['python','-m','demucs','--two-stems','vocals','-n','htdemucs','-d',device,
           '-o',str(out/'stems'),str(song)]
    subprocess.run(cmd,check=True)
    stem = out/'stems'/'htdemucs'/Path(song).stem
    return stem/'vocals.wav',stem/'no_vocals.wav'


def extract_pitch(vocals, out, start=0, duration=None, sr=16000, hop=320):
    import librosa
    kwargs={'sr':sr,'mono':True,'offset':start}
    if duration is not None: kwargs['duration']=duration
    y,_=librosa.load(str(vocals),**kwargs)
    f0, voiced, prob = librosa.pyin(y, sr=sr,hop_length=hop,fmin=librosa.note_to_hz('C2'),
                                    fmax=librosa.note_to_hz('C6'),fill_na=np.nan)
    times=librosa.times_like(f0,sr=sr,hop_length=hop)+start
    midi=np.full(len(f0),np.nan)
    good=np.isfinite(f0)&(f0>0)
    midi[good]=librosa.hz_to_midi(f0[good])
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out,time=times,midi=midi,voiced=voiced,confidence=prob)
    return len(times)


def _normalize(s):
    return re.sub(r'[^\w\u3400-\u9fff]+','',s).lower()


def align(vocals, lyric_lines, out, language='zh', device='cpu', model_name=None):
    """Experimental WhisperX forced alignment. Requires WhisperX and compatible align model.

    Transcript anchors are estimated using Whisper transcription. Supplied lyrics are preserved.
    Low-confidence or unmatched lines are flagged for manual review, never silently passed.
    """
    import whisperx
    from difflib import SequenceMatcher
    audio=whisperx.load_audio(str(vocals))
    model=whisperx.load_model('small',device,compute_type='float16' if device=='cuda' else 'int8',language=language)
    transcription=model.transcribe(audio,batch_size=4,language=language)
    del model
    recognized=transcription.get('segments',[])
    if not recognized: raise RuntimeError('No speech segments found; manual review required')
    align_model, metadata=whisperx.load_align_model(language_code=language,device=device,model_name=model_name)
    # Use sequential fuzzy transcript matching to estimate line anchors, not a fabricated success.
    cursor=0
    prepared=[]
    warnings=[]
    for i,line in enumerate(lyric_lines):
        target=_normalize(line['text'])
        candidates=[]
        for j in range(cursor,min(cursor+8,len(recognized))):
            for end in range(j+1,min(j+5,len(recognized))+1):
                chunk=''.join(x.get('text','') for x in recognized[j:end])
                similarity=SequenceMatcher(None,target,_normalize(chunk)).ratio()
                candidates.append((similarity,j,end))
        if not candidates:
            warnings.append({'line':i,'reason':'no transcript anchor'})
            continue
        similarity,j,end=max(candidates)
        if similarity<0.45:
            warnings.append({'line':i,'reason':'low transcript match','similarity':round(similarity,3)})
            continue
        start=float(recognized[j]['start'])
        finish=float(recognized[end-1]['end'])
        if line['hint_start'] is not None:
            if abs(start-line['hint_start'])>3:
                warnings.append({'line':i,'reason':'LRC hint mismatch','offset_s':round(start-line['hint_start'],2)})
            start=max(0,line['hint_start']-0.6)
            finish=max(finish,start+0.5)
        prepared.append({'start':start,'end':finish,'text':line['text'],'line_id':i})
        cursor=end
    if not prepared: raise RuntimeError('No lyrics aligned; review input/transcription')
    result=whisperx.align(prepared,align_model,metadata,audio,device,return_char_alignments=True)
    mapped=[]
    for seg in result.get('segments',[]):
        chars=seg.get('chars',[])
        valid=[c for c in chars if 'start' in c and 'end' in c]
        if not valid: warnings.append({'line':seg['line_id'],'reason':'no character timestamps'})
        mapped.append({'line_id':seg['line_id'],'text':seg['text'], 'start':seg.get('start'),
                       'end':seg.get('end'),'tokens':valid,'needs_review':len(valid)==0})
    payload={'language':language,'lines':mapped,'warnings':warnings,
             'status':'review_required' if warnings or len(mapped)!=len(lyric_lines) else 'provisional',
             'note':'Automatic alignment is provisional until ground-truth validation.'}
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return payload
