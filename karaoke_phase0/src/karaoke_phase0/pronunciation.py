"""Conservative MFA dictionary augmentation for known Mandarin lyrics.

Never invent phone symbols. Unknown pronunciations remain unresolved unless a
verified G2P callback supplies a phone sequence from the model's phone set.
"""
from pathlib import Path
import re

HAN = re.compile(r'[\u3400-\u9fff]+')


def read_dictionary(path):
    entries = {}
    for raw in Path(path).read_text(encoding='utf-8-sig').splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        word = parts[0]
        # MFA dictionary with pronunciation + silence probabilities: four floats.
        probabilities = len(parts) >= 6 and all(_is_float(x) for x in parts[1:5])
        phones = parts[5:] if probabilities else parts[1:]
        if phones:
            entries.setdefault(word, []).append(tuple(phones))
    return entries


def _is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def segment(text, lexicon):
    """Maximum-match segmentation; preserve unknown Han spans for OOV reporting."""
    chunks = HAN.findall(text)
    result = []
    for chunk in chunks:
        i = 0
        while i < len(chunk):
            matches = [w for w in lexicon if chunk.startswith(w, i)]
            if matches:
                word = max(matches, key=len)
            else:
                word = chunk[i]
            result.append(word)
            i += len(word)
    return result


def build_dictionary(base_path, output_path, lyrics, g2p=None, valid_phones=None):
    """Create full derived dictionary and report OOVs without touching base.

    g2p(word) is an optional *verified* phoneme generator returning a list of
    phones. With no G2P, use uniquely pronounced component characters only.
    Ambiguous words remain unresolved instead of choosing a random reading.
    """
    base = Path(base_path)
    output = Path(output_path)
    if base.resolve() == output.resolve():
        raise ValueError('Never overwrite the pretrained dictionary')
    lexicon = read_dictionary(base)
    original = base.read_text(encoding='utf-8-sig')
    # Prefer phrase-level words when provided, otherwise use maximum-match.
    words = sorted(set(word for line in lyrics for word in segment(line, lexicon)))
    missing = [w for w in words if w not in lexicon]
    additions, unresolved = {}, []
    for word in missing:
        phones = None
        if g2p is not None:
            candidate = g2p(word)
            if candidate:
                phones = tuple(candidate)
        if phones is None:
            components = [lexicon.get(c, []) for c in word]
            if all(len(set(options)) == 1 for options in components):
                phones = tuple(p for options in components for p in options[0])
        if not phones or (valid_phones is not None and any(p not in valid_phones for p in phones)):
            unresolved.append(word)
            continue
        additions[word] = phones
    output.parent.mkdir(parents=True, exist_ok=True)
    # Write atomically and use standard MFA 5-field numeric format for additions.
    tmp = output.with_suffix(output.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        f.write(original.rstrip('\n') + '\n')
        for word, phones in sorted(additions.items()):
            f.write(f"{word}\t0.99\t0.25\t1.0\t1.0\t{' '.join(phones)}\n")
    tmp.replace(output)
    return {'oov': missing, 'added': sorted(additions), 'unresolved': unresolved,
            'requires_review': bool(unresolved)}
