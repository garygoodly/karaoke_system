"""Align supplied lyrics without loading WhisperX ASR/Pyannote VAD.

LRC timestamps bound the alignment window. Plain TXT needs a lightweight
transcription to locate phrases; faster-whisper runs without Pyannote VAD.
"""
from difflib import SequenceMatcher
from pathlib import Path
import json
import re


def normalize(text):
    return re.sub(r'[^\w\u3400-\u9fff]+', '', text).lower()


def global_match_lines(lines, recognized, min_similarity=.32, max_span=2):
    """Globally optimize order-preserving, non-reused ASR segment assignments.

    Skipping an ASR segment is cheaper than skipping a lyric line; a good
    early match is preferred over jumping to a later repeated chorus.
    Returns (start_index, end_exclusive, similarity) or None per lyric line.
    """
    n, m = len(lines), len(recognized)
    negative = float('-inf')
    dp = [[negative] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    def offer(i, j, value, previous):
        if value > dp[i][j] + 1e-9:
            dp[i][j] = value
            back[i][j] = previous

    for i in range(n + 1):
        for j in range(m + 1):
            score = dp[i][j]
            if score == negative:
                continue
            if j < m:
                offer(i, j + 1, score - .18, (i, j, None))
            if i < n:
                offer(i + 1, j, score - .9, (i, j, None))
            if i < n and j < m:
                target = normalize(lines[i]['text'])
                for end in range(j + 1, min(m, j + max_span) + 1):
                    candidate = normalize(''.join(s.text for s in recognized[j:end]))
                    sim = SequenceMatcher(None, target, candidate).ratio()
                    if sim < min_similarity:
                        continue
                    # Small preference for local/short matches; no arbitrary jumps.
                    reward = 2.0 * sim - .55 - .12 * (end - j - 1)
                    offer(i + 1, end, score + reward, (i, j, (j, end, sim)))
    result = [None] * n
    i, j = n, m
    while i or j:
        previous = back[i][j]
        if previous is None:
            raise RuntimeError('Global alignment backtrace failed')
        pi, pj, match = previous
        if match is not None:
            result[pi] = match
        i, j = pi, pj
    return result


def timing_warnings(line_id, line, song_duration):
    """Flag implausible character timings without silently changing them."""
    issues = []
    tokens = [t for t in line.get('tokens', []) if str(t.get('text', '')).strip()]
    previous_end = None
    for token in tokens:
        start, end = token.get('start'), token.get('end')
        if start is None or end is None or not (0 <= start < end <= song_duration + .05):
            issues.append({'line_id': line_id, 'reason': 'invalid character timing',
                           'token': token.get('text')})
            continue
        length = end - start
        if length < .06:
            issues.append({'line_id': line_id, 'reason': 'suspiciously short character',
                           'token': token.get('text'), 'duration': round(length, 3)})
        elif length > 2.5:
            issues.append({'line_id': line_id, 'reason': 'suspiciously long character',
                           'token': token.get('text'), 'duration': round(length, 3)})
        if previous_end is not None and start < previous_end - .05:
            issues.append({'line_id': line_id, 'reason': 'overlapping character timing',
                           'token': token.get('text')})
        previous_end = end
    if not tokens:
        issues.append({'line_id': line_id, 'reason': 'no timed characters'})
    return issues


def locate_lines(lines, audio, device, language, diagnostic_path=None):
    """Return candidate segments indexed by source line, plus warnings."""
    duration = len(audio) / 16000
    hints = [x.get('hint_start') for x in lines]
    warnings = []
    located = []
    if all(h is not None for h in hints):
        for idx, line in enumerate(lines):
            start = float(hints[idx])
            next_hints = [float(h) for h in hints[idx + 1:] if float(h) > start]
            end = min(duration, min(next_hints) if next_hints else start + 8.0)
            if start < 0 or start >= duration or end <= start:
                warnings.append({'line_id': idx, 'reason': 'invalid LRC timing'})
                continue
            located.append((idx, {'start': start, 'end': end, 'text': line['text']}))
        return located, warnings, 'lrc_hints'

    # TXT has no timestamps. ASR here is used only to locate phrases; supplied
    # lyrics remain the authority for the final alignment text.
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device=device,
                         compute_type='float16' if device == 'cuda' else 'int8')
    segments, _ = model.transcribe(audio, language=language, vad_filter=False,
                                   beam_size=5)
    recognized = list(segments)
    del model
    diagnostics = {
        'schema_version': 1, 'language': language,
        'audio_duration_seconds': round(duration, 3),
        'asr_segments': [
            {'index': i, 'start': float(seg.start), 'end': float(seg.end),
             'text': seg.text} for i, seg in enumerate(recognized)
        ],
        'line_matches': [], 'unused_asr_segment_indices': [],
        'purpose': 'Diagnostic only; ASR text is not ground truth.'
    }
    decisions = global_match_lines(lines, recognized)
    used_indices = set()
    for idx, decision in enumerate(decisions):
        if decision is None:
            warnings.append({'line_id': idx, 'reason': 'no reliable ordered transcript match'})
            diagnostics['line_matches'].append({
                'line_id': idx, 'lyrics': lines[idx]['text'], 'status': 'unmatched',
                'reason': 'no reliable ordered transcript match'})
            continue
        j, end, similarity = decision
        start = max(0., float(recognized[j].start) - .15)
        finish = min(duration, float(recognized[end - 1].end) + .15)
        valid = finish > start
        diagnostics['line_matches'].append({
            'line_id': idx, 'lyrics': lines[idx]['text'],
            'candidate_start_index': j, 'candidate_end_index_exclusive': end,
            'candidate_start_seconds': float(recognized[j].start),
            'candidate_end_seconds': float(recognized[end - 1].end),
            'candidate_text': ''.join(seg.text for seg in recognized[j:end]),
            'similarity': round(float(similarity), 4),
            'status': 'matched' if valid else 'unmatched'})
        if not valid:
            warnings.append({'line_id': idx, 'reason': 'invalid transcript timing'})
            continue
        located.append((idx, {'start': start, 'end': finish, 'text': lines[idx]['text']}))
        used_indices.update(range(j, end))
    diagnostics['unused_asr_segment_indices'] = [
        i for i in range(len(recognized)) if i not in used_indices
    ]
    if diagnostic_path is not None:
        write_diagnostics(diagnostic_path, diagnostics)
    return located, warnings, 'transcript_localization' 


def write_diagnostics(path, data):
    """Atomically persist a diagnostic snapshot; never overwrite the source lyrics."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(target)


def align_located_lines(whisperx, audio, located, lyric_lines, model, metadata,
                        device, song_duration, pad_seconds=0.35):
    """Forced-align the *supplied* lyrics on isolated local vocal clips.

    WhisperX timestamps from a cropped clip are local to that clip. Convert
    them to global song time exactly once. Never substitute ASR transcription.
    """
    sample_rate = 16000  # whisperx.load_audio uses 16 kHz mono
    mapped, warnings = [], []
    for idx, candidate in located:
        text = lyric_lines[idx]['text']
        # A small pad permits boundary correction, without leaking into distant
        # repeated choruses. Clamp at the neighboring located phrase midpoint.
        start = max(0., float(candidate['start']))
        end = min(song_duration, float(candidate['end']))
        if not text.strip() or end <= start:
            warnings.append({'line_id': idx, 'reason': 'invalid alignment window'})
            continue
        left = max(0., start - pad_seconds)
        right = min(song_duration, end + pad_seconds)
        first = int(left * sample_rate)
        last = min(len(audio), int(right * sample_rate))
        clip = audio[first:last]
        if len(clip) < sample_rate // 10:
            warnings.append({'line_id': idx, 'reason': 'audio clip too short'})
            continue
        offset = first / sample_rate
        # IMPORTANT: text is from lyrics.txt / lyrics.lrc, not from ASR.
        prepared = [{'start': 0.0, 'end': len(clip) / sample_rate,
                     'text': text}]
        try:
            aligned = whisperx.align(prepared, model, metadata, clip, device,
                                     return_char_alignments=True)
            segments = aligned.get('segments') or []
            if not segments:
                raise ValueError('no aligned segment')
            seg = segments[0]
            tokens = []
            for token in (seg.get('chars') or []):
                char = str(token.get('char', ''))
                if not char.strip():
                    continue  # whitespace is layout, not a sung character
                t0, t1 = token.get('start'), token.get('end')
                if t0 is None or t1 is None:
                    warnings.append({'line_id': idx, 'reason': 'untimed character',
                                     'token': char})
                    continue
                a, b = float(t0) + offset, float(t1) + offset
                if not (0 <= a < b <= song_duration + .05):
                    warnings.append({'line_id': idx, 'reason': 'invalid character timing',
                                     'token': char})
                    continue
                tokens.append({'text': char, 'start': round(a, 3),
                               'end': round(b, 3)})
            # A returned segment alone does not establish valid character timing.
            if not tokens:
                warnings.append({'line_id': idx, 'reason': 'no timed characters'})
                continue
            entry = {'line_id': idx, 'text': text,
                     'start': round(float(seg.get('start', 0.)) + offset, 3),
                     'end': round(float(seg.get('end', len(clip)/sample_rate)) + offset, 3),
                     'tokens': tokens}
            issues = timing_warnings(idx, entry, song_duration)
            warnings.extend(issues)
            # Flag missing tokens rather than treating an incomplete sentence as valid.
            expected = [c for c in text if not c.isspace() and not re.match(r'[^\w\u3400-\u9fff]', c)]
            actual = [t['text'] for t in tokens]
            if actual != expected:
                warnings.append({'line_id': idx, 'reason': 'incomplete character alignment',
                                 'expected_count': len(expected), 'timed_count': len(actual)})
            entry['needs_review'] = any(w['line_id'] == idx for w in warnings)
            mapped.append(entry)
        except Exception as exc:
            warnings.append({'line_id': idx, 'reason': 'forced alignment failed',
                             'detail': str(exc)[:300]})
    return mapped, warnings


def align_known_lyrics(vocals, lyric_lines, out, language='zh', device='cpu', model_name=None):
    import whisperx
    audio = whisperx.load_audio(str(vocals))
    diagnostic_path = Path(out).parent / 'asr_segments.json'
    located, warnings, method = locate_lines(
        lyric_lines, audio, device, language, diagnostic_path=diagnostic_path)
    if not located:
        raise RuntimeError('Could not locate any lyrics; manual alignment required.')
    # No whisperx.load_model(), and therefore no Pyannote VAD initialization.
    model, metadata = whisperx.load_align_model(
        language_code=language, device=device, model_name=model_name)
    mapped, timing_issues = align_located_lines(
        whisperx, audio, located, lyric_lines, model, metadata, device,
        len(audio) / 16000)
    warnings.extend(timing_issues)
    result = {'language': language, 'method': method + '+known_lyrics_local_forced_alignment',
              'source_line_count': len(lyric_lines), 'lines': mapped,
              'warnings': warnings, 'status': 'review_required',
              'note': 'Provisional local forced alignment; review before Ready.'}
    output = Path(out)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(output)
    return result
