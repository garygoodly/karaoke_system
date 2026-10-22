"""Experimental MFA TextGrid -> Chinese character timing (no invented equal splits).

For multi-character words, detect one tone-marked vowel nucleus per Han character.
If phonetic evidence is ambiguous, keep the word unresolved for manual review.
Times are relative to each clip, or global with --offset.
"""
import argparse
import json
import re
from pathlib import Path

TONE = re.compile('[˥˦˧˨˩]')
HAN = re.compile(r'[\u3400-\u9fff]')
CODAS = {'n', 'ŋ', 'm'}


def parse_textgrid(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    tiers = {}
    for match in re.finditer(r'\bitem \[\d+\]:\s*class = "IntervalTier"\s*name = "([^"]+)"(.*?)(?=\n\s*item \[\d+\]:|\Z)', text, re.S):
        name, block = match.groups()
        entries = []
        pattern = r'intervals \[\d+\]:\s*xmin = ([\d.]+)\s*xmax = ([\d.]+)\s*text = "([^"]*)"'
        for m in re.finditer(pattern, block):
            entries.append({'start': float(m[1]), 'end': float(m[2]), 'text': m[3]})
        tiers[name] = entries
    if 'words' not in tiers or 'phones' not in tiers:
        raise ValueError('TextGrid requires words and phones interval tiers')
    return tiers


def convert(tiers, offset=0.0):
    result, unresolved = [], []
    phones = tiers['phones']
    for word in tiers['words']:
        label = word['text'].strip()
        if not label:
            continue
        chars = list(label)
        within = [p for p in phones if p['text'].strip() and p['start'] >= word['start'] - .011 and p['end'] <= word['end'] + .011]
        if not all(HAN.fullmatch(c) for c in chars):
            unresolved.append({'word': label, 'reason': 'non_han_or_mixed', 'start': word['start'] + offset})
            continue
        if any(p['text'] == 'spn' for p in within) or not within:
            unresolved.append({'word': label, 'reason': 'unknown_or_missing_phones', 'start': word['start'] + offset})
            continue
        if len(chars) == 1:
            result.append({'text': label, 'start': round(word['start'] + offset, 3), 'end': round(word['end'] + offset, 3), 'source': 'mfa_word'})
            continue
        nuclei = [i for i, p in enumerate(within) if TONE.search(p['text'])]
        if len(nuclei) != len(chars):
            unresolved.append({'word': label, 'reason': 'syllable_count_mismatch', 'expected': len(chars), 'nuclei': len(nuclei), 'start': word['start'] + offset})
            continue
        boundaries = [word['start']]
        for a, b in zip(nuclei, nuclei[1:]):
            between = within[a + 1:b]
            if between:
                # Nasal codas belong to the preceding syllable. The remaining
                # consonant onset begins the following syllable.
                onset = next((p for p in between if p['text'] not in CODAS), None)
                # m + glide (w/y) starts the next syllable; ŋ + k is a coda + onset.
                if between[0]['text'] == 'm' and len(between) > 1 and between[1]['text'] in {'w', 'j'}:
                    split = between[0]['start']
                else:
                    split = onset['start'] if onset else within[b]['start']
            else:
                split = within[b]['start']
            boundaries.append(split)
        boundaries.append(word['end'])
        if any(y <= x for x, y in zip(boundaries, boundaries[1:])):
            unresolved.append({'word': label, 'reason': 'invalid_boundaries', 'start': word['start'] + offset})
            continue
        for c, a, b in zip(chars, boundaries, boundaries[1:]):
            result.append({'text': c, 'start': round(a + offset, 3), 'end': round(b + offset, 3), 'source': 'mfa_phone_heuristic', 'needs_review': True})
    return {'tokens': result, 'unresolved': unresolved, 'status': 'experimental_review_required'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('textgrid', type=Path)
    p.add_argument('--offset', type=float, default=0.0, help='Clip start in original song seconds')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    data = convert(parse_textgrid(args.textgrid), args.offset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"tokens={len(data['tokens'])} unresolved={len(data['unresolved'])} -> {args.output}")


if __name__ == '__main__':
    main()
