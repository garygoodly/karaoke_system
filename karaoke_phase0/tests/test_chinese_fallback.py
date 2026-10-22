import pytest
from karaoke_phase0.chinese_fallback import normalized_char_spaced, restore_characters

@pytest.mark.parametrize('source,expected', [
    ('説甚麼你愛我', '說 甚 麼 你 愛 我'),
    ('相擁着寂寞', '相 擁 著 寂 寞'),
    ('才如此難過', '才 如 此 難 過'),
    ('只一剎的花火', '只 一 刹 的 花 火'),
    ('就像已傷的心不勝折磨', '就 像 已 傷 的 心 不 勝 折 磨'),
])
def test_character_fallback(source, expected):
    text, original, normalized = normalized_char_spaced(source)
    assert text == expected
    assert len(original) == len(normalized)
    restored = restore_characters([{'text': c, 'start': i, 'end': i + 1}
                                   for i, c in enumerate(normalized)], original, normalized)
    assert ''.join(t['text'] for t in restored) == source


def test_mismatch_is_rejected():
    with pytest.raises(ValueError, match='character_sequence_mismatch'):
        restore_characters([{'text': '錯'}], ['說'], ['說'])
