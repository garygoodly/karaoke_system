"""Experimental full-song MFA pass from an existing line-level timeline.

Never replaces the WhisperX timeline; output remains review_required.
"""
import json
import re
import subprocess
from .process_environment import run_mfa_command
import wave
from pathlib import Path

from .mfa_workflow import run_benchmark
from .chinese_fallback import normalized_char_spaced, restore_characters

HAN = re.compile(r'[\u3400-\u9fff]')
LATIN_WORD = re.compile(r"[A-Za-z]+(?:[-’']+[A-Za-z]+)*")


def unsupported_language_lines(lines):
    """Skip mixed-language utterances rather than feed English into Mandarin G2P.

    These lines remain in QA and must be manually aligned before Karaoke Ready.
    """
    return {i: 'unsupported_language: ' + ', '.join(sorted(set(LATIN_WORD.findall(line['text']))))
            for i, line in enumerate(lines) if LATIN_WORD.search(line['text'])}



def plan_lines(lines, timeline, duration, pad=0.12):
    """Plan independent padded clips; check overlaps on aligned tokens later."""
    candidates = {}
    for entry in timeline.get('lines', []):
        idx = entry.get('line_id')
        if not isinstance(idx, int) or idx < 0 or idx >= len(lines) or idx in candidates:
            continue
        try:
            a, b = float(entry['start']), float(entry['end'])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= a < b <= duration and lines[idx]['text'].strip():
            candidates[idx] = (a, b)
    planned, errors = {}, {}
    for idx, (a, b) in candidates.items():
        start, end = max(0.0, a - pad), min(duration, b + pad)
        if end - start < .12:
            errors[idx] = 'too_short'
        else:
            planned[idx] = (start, end)
    for idx in range(len(lines)):
        if idx not in planned and idx not in errors:
            errors[idx] = 'missing_or_invalid_line_timing'
    return planned, errors


def flag_token_overlaps(results, tolerance=0.02):
    """Flag overlapping aligned character times without rejecting padded clips."""
    previous = None
    for line in results:
        tokens = line.get('tokens') or []
        if not tokens:
            continue
        starts = [float(t['start']) for t in tokens]
        ends = [float(t['end']) for t in tokens]
        if previous is not None:
            prior_line, prior_end = previous
            if min(starts) < prior_end - tolerance:
                for target, other in ((prior_line, line), (line, prior_line)):
                    target.setdefault('warnings', []).append({
                        'reason': 'overlapping_character_times',
                        'other_line_id': other['line_id'],
                    })
        previous = (line, max(ends))


def write_corpus(vocals, lines, windows, corpus):
    """Crop PCM WAV by frame index, preserving original channels and sample rate."""
    with wave.open(str(vocals), 'rb') as audio:
        if audio.getcomptype() != 'NONE':
            raise ValueError('Only uncompressed PCM WAV supported')
        rate, total = audio.getframerate(), audio.getnframes()
        params = audio.getparams()
        offsets = {}
        for idx, (a, b) in sorted(windows.items()):
            first, last = round(a*rate), round(b*rate)
            if first < 0 or last > total or first >= last:
                raise ValueError(f'Invalid crop for line {idx}')
            audio.setpos(first)
            payload = audio.readframes(last-first)
            name = f'line_{idx:03d}'
            with wave.open(str(corpus / f'{name}.wav'), 'wb') as out:
                out.setparams(params)
                out.writeframes(payload)
            (corpus / f'{name}.txt').write_text(lines[idx]['text'], encoding='utf-8')
            offsets[name] = first/rate
    return offsets


def run_full_song(folder, output, base_dictionary, mfa_exe, converter,
                  acoustic_model='mandarin_mfa', g2p_model='mandarin_taiwan_mfa',
                  extra_oovs=(), timeout=1800):
    from .alignment_workflow import lyrics_path
    from .core import parse_lyrics
    folder, output = Path(folder).resolve(), Path(output).resolve()
    generated = folder / 'generated'
    vocals = generated / 'vocals.wav'
    baseline = generated / 'lyrics_timeline.json'
    if not vocals.is_file() or not baseline.is_file():
        raise FileNotFoundError('Requires generated/vocals.wav and lyrics_timeline.json')
    if output == generated or output == folder or generated not in output.parents:
        raise ValueError('Output must be a new subdirectory under song/generated')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Output must be new or empty; existing analyses are preserved')
    lines = parse_lyrics(lyrics_path(folder))
    timeline = json.loads(baseline.read_text(encoding='utf-8'))
    if timeline.get('source_line_count') != len(lines):
        raise ValueError('Baseline line count differs from current lyrics; rerun line localization')
    with wave.open(str(vocals), 'rb') as audio:
        duration = audio.getnframes()/audio.getframerate()
    windows, errors = plan_lines(lines, timeline, duration)
    language_errors = unsupported_language_lines(lines)
    for idx, reason in language_errors.items():
        windows.pop(idx, None)
        errors[idx] = reason
    if not windows:
        raise RuntimeError('No Mandarin lyric windows; manual line alignment required')
    output.mkdir(parents=True, exist_ok=True)
    staging = output/'input_clips'; staging.mkdir()
    offsets = write_corpus(vocals, lines, windows, staging)
    # Ask MFA's own Mandarin tokenizer which compound words are missing.
    # Lexicon-only segmentation cannot reliably discover words such as "泡沫".
    oov_dir = output/'oov_diagnostics'
    scan = run_mfa_command([str(mfa_exe), 'find_oovs', str(staging),
                           str(base_dictionary), str(oov_dir)],
                          capture_output=True, text=True, timeout=timeout, check=False)
    (output/'oov_scan.log').write_text((scan.stdout or '')+'\n'+(scan.stderr or ''),encoding='utf-8')
    if scan.returncode:
        raise RuntimeError('MFA find_oovs failed; inspect oov_scan.log')
    discovered = set(extra_oovs)
    for report_file in oov_dir.rglob('oovs_found_*.txt'):
        discovered.update(x.strip().split('\t')[0] for x in
                          report_file.read_text(encoding='utf-8-sig').splitlines() if x.strip())
    # A G2P coverage failure must not abort all other Mandarin lines.  Rebuild
    # the corpus after isolating only the lines containing unresolved words.
    # Preserve each attempt's diagnostics; never edit source lyrics or lexicon.
    experiment = output/'mfa_run'
    remaining = set(windows)
    attempt = 0
    while True:
        try:
            summary = run_benchmark(staging, experiment, base_dictionary, mfa_exe, converter,
                                    acoustic_model=acoustic_model, g2p_model=g2p_model,
                                    extra_oovs=sorted(discovered), timeout=timeout)
            break
        except RuntimeError as exc:
            report_file = experiment/'report.json'
            if not str(exc).startswith('Unresolved OOV:') or not report_file.is_file():
                raise
            blocked = json.loads(report_file.read_text(encoding='utf-8'))
            unresolved = blocked.get('dictionary', {}).get('unresolved', [])
            if not unresolved:
                raise
            affected = {i for i in remaining if any(w and w in lines[i]['text'] for w in unresolved)}
            if not affected:
                raise RuntimeError('G2P OOV cannot be mapped to any line; inspect mfa_run/report.json') from exc
            for i in affected:
                errors[i] = 'unresolved_pronunciation: ' + ', '.join(
                    w for w in unresolved if w and w in lines[i]['text'])
                name = f'line_{i:03d}'
                (staging/(name+'.wav')).unlink(missing_ok=True)
                (staging/(name+'.txt')).unlink(missing_ok=True)
            remaining -= affected
            if not remaining:
                summary = {'dictionary': blocked.get('dictionary', {}), 'clips': {}}
                break
            attempt += 1
            # Retain the failed run for investigation; the next run uses a new directory.
            experiment = output/f'mfa_run_retry_{attempt:02d}'
            discovered = {w for w in discovered if not any(w in lines[i]['text'] for i in affected)}
    # Retry only the rejected Chinese lines with one-to-one character spacing.
    # The 28 successful first-pass lines are not re-aligned or overwritten.
    fallback_results = {}
    rejected = [i for i in sorted(errors) if
                errors[i].startswith('unresolved_pronunciation:') and i in offsets]
    if rejected:
        fallback_corpus = output/'fallback_input_clips'
        fallback_corpus.mkdir()
        original_chars = {}
        for i in rejected:
            name = f'line_{i:03d}'
            try:
                fallback_text, originals, normalized = normalized_char_spaced(lines[i]['text'])
            except ValueError:
                continue
            original_chars[name] = (originals, normalized)
            import shutil
            shutil.copy2(output/'input_clips'/f'{name}.wav', fallback_corpus/f'{name}.wav') if (output/'input_clips'/f'{name}.wav').exists() else None
            # The isolation pass removed the original staging clips, so regenerate
            # a fresh WAV from the existing full-song audio instead.
            if not (fallback_corpus/f'{name}.wav').exists():
                write_corpus(vocals, lines, {i: windows[i]}, fallback_corpus)
            (fallback_corpus/f'{name}.txt').write_text(fallback_text, encoding='utf-8')
        # One failed character must not block the other fallback lines.
        for name, (originals, normalized) in original_chars.items():
            single_corpus = output/'fallback_single_corpus'/name
            single_corpus.mkdir(parents=True)
            import shutil
            shutil.copy2(fallback_corpus/f'{name}.wav', single_corpus/f'{name}.wav')
            shutil.copy2(fallback_corpus/f'{name}.txt', single_corpus/f'{name}.txt')
            fallback_output = output/'mfa_character_fallback'/name
            try:
                run_benchmark(single_corpus, fallback_output, base_dictionary, mfa_exe,
                              converter, acoustic_model=acoustic_model,
                              g2p_model=g2p_model, extra_oovs=(), timeout=timeout)
                char_file = fallback_output/(name+'_mfa_chars.json')
                if not char_file.is_file():
                    continue
                raw = json.loads(char_file.read_text(encoding='utf-8'))
                tokens = restore_characters(raw['tokens'], originals, normalized)
                if raw.get('unresolved'):
                    continue
                fallback_results[int(name.split('_')[1])] = {
                    'tokens': tokens, 'unresolved': []}
            except (RuntimeError, ValueError) as exc:
                fallback_output.mkdir(parents=True, exist_ok=True)
                (fallback_output/'fallback_error.txt').write_text(str(exc), encoding='utf-8')
    results = []
    for idx in range(len(lines)):
        name = f'line_{idx:03d}'
        if idx in fallback_results:
            raw = fallback_results[idx]
            offset = offsets[f'line_{idx:03d}']
            tokens = [{**t, 'start': round(t['start']+offset, 3),
                       'end': round(t['end']+offset, 3)} for t in raw['tokens']]
            errors.pop(idx, None)
            results.append({'line_id':idx,'text':lines[idx]['text'],
                            'status':'review_required', 'tokens':tokens,
                            'warnings':[{'reason':'character_g2p_fallback_needs_review'}] + raw['unresolved']})
            continue
        if idx in errors:
            results.append({'line_id':idx,'text':lines[idx]['text'],'status':'review_required',
                            'reason':errors[idx], 'tokens':[]})
            continue
        clip_result = summary.get('clips', {}).get(name, {})
        if clip_result.get('reason') or not (experiment/(name+'_mfa_chars.json')).is_file():
            reason = clip_result.get('reason', 'missing_character_output')
            errors[idx] = reason
            results.append({'line_id':idx,'text':lines[idx]['text'],
                            'status':'review_required','reason':reason,'tokens':[]})
            continue
        raw = json.loads((experiment/(name+'_mfa_chars.json')).read_text(encoding='utf-8'))
        offset = offsets[name]
        tokens = [{**t, 'start':round(t['start']+offset,3),
                   'end':round(t['end']+offset,3)} for t in raw['tokens']]
        expected = [c for c in lines[idx]['text'] if HAN.fullmatch(c)]
        actual = [t['text'] for t in tokens]
        warnings = list(raw['unresolved'])
        if expected != actual:
            warnings.append({'reason':'character_sequence_mismatch', 'expected':len(expected), 'actual':len(actual)})
        if any(t['end'] <= t['start'] or t['start'] < 0 or t['end'] > duration+.05 for t in tokens):
            warnings.append({'reason':'invalid_global_character_time'})
        results.append({'line_id':idx,'text':lines[idx]['text'],'status':'review_required',
                        'start':windows[idx][0],'end':windows[idx][1],
                        'tokens':tokens,'warnings':warnings})
    flag_token_overlaps(results)
    report = {'status':'review_required','method':'mfa_full_song_experimental',
              'source_line_count':len(lines),'processed_lines':len([i for i in windows if i not in errors]),
              'failed_lines':len(errors), 'skipped_unsupported_language_lines':sorted(language_errors),
              'dictionary':summary['dictionary'],
              'lines':results, 'note':'Experimental; never replaces lyrics_timeline.json.'}
    (output/'lyrics_timeline_mfa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'qa_report.json').write_text(json.dumps({'status':'review_required',
        'failed_line_ids':sorted(errors),'failed_reasons':errors,
        'lines_with_warnings':[x['line_id'] for x in results if x.get('warnings') or not x['tokens']]},
        ensure_ascii=False,indent=2),encoding='utf-8')
    return report
