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
    """Experimental supplied-lyrics alignment. Unmatched lines require manual review."""
    from difflib import SequenceMatcher
    import whisperx
    audio = whisperx.load_audio(str(vocals))
    compute_type = 'float16' if device == 'cuda' else 'int8'
    import torch
    from omegaconf.listconfig import ListConfig

    asr = None
    with torch.serialization.safe_globals([ListConfig]):
        asr = whisperx.load_model(
            'small',
            device,
            compute_type=compute_type,
            language=language,
        )
    # asr = whisperx.load_model('small', device, compute_type=compute_type, language=language)
    recognized = asr.transcribe(audio, batch_size=4, language=language).get('segments', [])
    del asr
    if not recognized:
        raise RuntimeError('No vocal transcript found; check separation or review lyrics.')
    model, metadata = whisperx.load_align_model(language_code=language, device=device, model_name=model_name)
    cursor, prepared, warnings = 0, [], []
    for idx, line in enumerate(lyric_lines):
        target = _normalize(line['text'])
        candidates = []
        for j in range(cursor, min(cursor+12, len(recognized))):
            for end in range(j+1, min(j+5, len(recognized))+1):
                chunk = ''.join(r.get('text','') for r in recognized[j:end])
                similarity = SequenceMatcher(None, target, _normalize(chunk)).ratio()
                hint = line.get('hint_start')
                distance = abs(float(recognized[j]['start'])-hint) if hint is not None else 0
                score = similarity - min(distance/30, .25) if hint is not None else similarity
                candidates.append((score, similarity, j, end))
        if not candidates:
            warnings.append({'line_id':idx,'reason':'no transcript candidate'})
            continue
        _, similarity, j, end = max(candidates)
        if similarity < .45:
            warnings.append({'line_id':idx,'reason':'low transcript match','similarity':round(similarity,3)})
            continue
        start = float(recognized[j]['start'])
        finish = float(recognized[end-1]['end'])
        hint = line.get('hint_start')
        if hint is not None and abs(start-hint)>3:
            warnings.append({'line_id':idx,'reason':'LRC hint mismatch','offset_s':round(start-hint,2)})
        if hint is not None and abs(start-hint)<=3:
            start = max(0, min(start, hint)-.25)
        prepared.append({'start':start,'end':max(finish,start+.2),'text':line['text']})
        cursor = end
    if not prepared:
        raise RuntimeError('No lines matched; cannot produce a usable timeline.')
    aligned = whisperx.align(prepared, model, metadata, audio, device, return_char_alignments=True)
    # WhisperX does not guarantee preserving arbitrary input fields such as line_id.
    # Preserve source order explicitly and never silently mark missing tokens as valid.
    segments = aligned.get('segments', [])
    matched_ids = [i for i in range(len(lyric_lines)) if i not in {w['line_id'] for w in warnings if w['reason'] in ('no transcript candidate','low transcript match')}]
    mapped = []
    for position, idx in enumerate(matched_ids):
        if position >= len(segments):
            warnings.append({'line_id':idx,'reason':'alignment segment missing'})
            continue
        seg = segments[position]
        raw_tokens = seg.get('chars', []) or seg.get('words', [])
        tokens = []
        for token in raw_tokens:
            if token.get('start') is not None and token.get('end') is not None:
                tokens.append({'text':token.get('char',token.get('word','')),
                               'start':float(token['start']),'end':float(token['end'])})
        if not tokens:
            warnings.append({'line_id':idx,'reason':'no timed characters'})
        mapped.append({'line_id':idx,'text':lyric_lines[idx]['text'],
                       'start':float(seg.get('start',prepared[position]['start'])),
                       'end':float(seg.get('end',prepared[position]['end'])),
                       'tokens':tokens,'needs_review':not bool(tokens)})
    payload = {'language':language,'source_line_count':len(lyric_lines),
               'lines':mapped,'warnings':warnings,
               'status':'review_required' if warnings or len(mapped)!=len(lyric_lines) else 'provisional',
               'note':'Provisional alignment; manual validation is required before Ready.'}
    output = Path(out)
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp = output.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(output)
    return payload
