"""Conservative same-length Han normalization and single-character fallback.

Only use on lines already rejected by the ordinary Mandarin G2P pass.
Original lyric text is never modified.
"""
import re

HAN = re.compile(r'[\u3400-\u9fff]')
VARIANTS = {'説': '說', '着': '著', '剎': '刹'}


def normalized_char_spaced(text):
    """Normalize selected variants and split adjacent Han characters for MFA.

    Mapping is one-to-one; every Han character retains its original index.
    Returns (MFA text, list of original Han characters, list of MFA characters).
    """
    original = [c for c in text if HAN.fullmatch(c)]
    normalized = [VARIANTS.get(c, c) for c in original]
    if not original or any(not HAN.fullmatch(c) for c in normalized):
        raise ValueError('No safely normalizable Han characters')
    return ' '.join(normalized), original, normalized


def restore_characters(tokens, original, normalized):
    """Restore original display glyphs only if token sequence maps 1:1."""
    if [t.get('text') for t in tokens] != normalized:
        raise ValueError('character_sequence_mismatch')
    return [{**t, 'text': c} for t, c in zip(tokens, original)]
