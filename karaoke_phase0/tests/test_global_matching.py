import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('matcher', ROOT / 'src/karaoke_phase0/known_lyrics_alignment.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_repeated_chorus_keeps_first_occurrence():
    lyrics = ['甲乙丙', '基於你還愛我', '美麗的泡沫', '你所有承諾',
              '基於你還愛我', '美麗的泡沫']
    asr = ['甲乙丙', '其餘你還愛我', '美麗的泡沫', '你所有沉默',
           '其餘你還愛我', '美麗的泡沫']
    segments = [SimpleNamespace(text=x, start=i * 7, end=i * 7 + 6)
                for i, x in enumerate(asr)]
    matches = module.global_match_lines([{'text': x} for x in lyrics], segments)
    assert [m[0] if m else None for m in matches] == list(range(6))


def test_timing_flags():
    line = {'tokens': [{'text': '你', 'start': 1.0, 'end': 1.02},
                       {'text': '愛', 'start': 1.02, 'end': 5.5}]}
    issues = module.timing_warnings(3, line, 10)
    assert {x['reason'] for x in issues} == {'suspiciously short character', 'suspiciously long character'}


def test_missing_line_not_fabricated():
    lines = [{'text': '甲乙丙'}, {'text': '完全不相干'}]
    segments = [SimpleNamespace(text='甲乙丙', start=0, end=1)]
    assert module.global_match_lines(lines, segments)[1] is None
