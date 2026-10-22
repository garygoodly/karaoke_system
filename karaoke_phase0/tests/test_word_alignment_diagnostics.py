import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'tools' / 'diagnose_word_alignment.py'
spec = importlib.util.spec_from_file_location('diagnose_word_alignment', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_punctuation_not_sung():
    assert module.is_sung_character('陽')
    assert not module.is_sung_character('?')
    assert not module.is_sung_character(' ')


def test_dictionary_missing_characters():
    result = module.inspect_dictionary('陽光？', {'dictionary': {'陽': 1}})
    assert result['unsupported_characters'] == ['光']
    assert result['characters_checked'] == 2


def test_suspicious_durations():
    items = module.summarize_chars([
        {'char': '陽', 'start': 0, 'end': .02},
        {'char': '光', 'start': .02, 'end': .4},
        {'char': '?', 'start': .4, 'end': .5},
    ])
    assert len(items) == 2
    assert [x['suspicious'] for x in items] == [True, False]
