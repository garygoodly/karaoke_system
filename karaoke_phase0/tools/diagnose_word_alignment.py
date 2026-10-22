"""Inspect WhisperX character alignment on one known-lyrics phrase only."""
import argparse
import json
import math
from pathlib import Path
import unicodedata


def is_sung_character(char):
    return bool(char.strip()) and not all(unicodedata.category(c).startswith('P') for c in char)


def inspect_dictionary(text, metadata):
    dictionary = metadata.get('dictionary', {})
    chars = [c for c in text if is_sung_character(c)]
    missing = [c for c in chars if c.lower() not in dictionary]
    return {'dictionary_size': len(dictionary), 'characters_checked': len(chars),
            'unsupported_characters': list(dict.fromkeys(missing)),
            'dictionary_sample': list(dictionary)[:25]}


def summarize_chars(chars):
    results = []
    for token in chars:
        char = str(token.get('char', ''))
        if not is_sung_character(char):
            continue
        start, end = token.get('start'), token.get('end')
        duration = None if start is None or end is None else round(float(end) - float(start), 4)
        results.append({'char': char, 'start': start, 'end': end, 'duration': duration,
                        'suspicious': duration is None or duration < .06 or duration > 2.5})
    return results


def run(args):
    import whisperx
    timeline = json.loads(Path(args.timeline).read_text(encoding='utf-8'))
    selected = next((line for line in timeline['lines'] if line['line_id'] == args.line_id), None)
    if selected is None:
        raise ValueError(f'line_id={args.line_id} not found in timeline')
    audio = whisperx.load_audio(str(args.vocals))
    duration = len(audio) / 16000
    left = max(0., float(selected['start']) - args.padding)
    right = min(duration, float(selected['end']) + args.padding)
    first, last = int(left * 16000), int(right * 16000)
    clip = audio[first:last]
    if len(clip) < 1600:
        raise ValueError('Audio clip too short')
    model, metadata = whisperx.load_align_model(language_code=args.language, device=args.device,
                                                 model_name=args.model_name)
    text = selected['text']
    prepared = [{'start': 0., 'end': len(clip) / 16000, 'text': text}]
    aligned = whisperx.align(prepared, model, metadata, clip, args.device,
                             return_char_alignments=True)
    raw_segments = aligned.get('segments', [])
    raw_chars = raw_segments[0].get('chars', []) if raw_segments else []
    raw_summary = summarize_chars(raw_chars)
    existing_summary = summarize_chars([{'char': t['text'], 'start': t['start'], 'end': t['end']}
                                         for t in selected.get('tokens', [])])
    result = {'schema_version': 1, 'line_id': args.line_id, 'lyrics': text,
              'model_name_requested': args.model_name, 'language': args.language,
              'device': args.device, 'clip_start_seconds': first / 16000,
              'clip_end_seconds': last / 16000, 'dictionary': inspect_dictionary(text, metadata),
              'raw_whisperx_segments_local_time': raw_segments,
              'raw_char_summary_local_time': raw_summary,
              'existing_timeline_char_summary_global_time': existing_summary,
              'raw_suspicious_count': sum(t['suspicious'] for t in raw_summary),
              'existing_suspicious_count': sum(t['suspicious'] for t in existing_summary),
              'note': 'Diagnostic only. Do not use these timestamps for Karaoke scoring.'}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + '.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    temp.replace(destination)
    print('Saved:', destination)
    print('Unsupported characters:', result['dictionary']['unsupported_characters'])
    print('Raw suspicious characters:', result['raw_suspicious_count'], '/', len(raw_summary))
    print('Existing suspicious characters:', result['existing_suspicious_count'], '/', len(existing_summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vocals', type=Path, required=True)
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--line-id', type=int, default=0)
    parser.add_argument('--language', default='zh')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--model-name', default=None)
    parser.add_argument('--padding', type=float, default=.35)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
