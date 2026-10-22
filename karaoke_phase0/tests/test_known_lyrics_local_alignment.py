import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np

path = Path(__file__).resolve().parents[1] / 'src/karaoke_phase0/known_lyrics_alignment.py'
spec = importlib.util.spec_from_file_location('known', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FakeWhisperX:
    def __init__(self): self.calls = []
    def align(self, segments, model, metadata, clip, device, return_char_alignments):
        self.calls.append((segments, len(clip)))
        chars = [{'char': ch, 'start': i*.15, 'end': (i+1)*.15}
                 for i, ch in enumerate(segments[0]['text'])]
        return {'segments': [{'start': 0., 'end': len(chars)*.15, 'chars': chars}]}

def test_uses_supplied_lyrics_and_restores_global_time():
    fake = FakeWhisperX()
    audio = np.zeros(16000*100, dtype='float32')
    located = [(3, {'start': 31., 'end': 37., 'text': '其餘你還愛我'})]
    lyrics = [{'text': ''} for _ in range(4)]
    lyrics[3] = {'text': '基於你還愛我'}
    lines, warnings = mod.align_located_lines(fake, audio, located, lyrics, None, None, 'cpu', 100.)
    assert fake.calls[0][0][0]['text'] == '基於你還愛我'
    assert lines[0]['tokens'][0]['text'] == '基'
    assert abs(lines[0]['tokens'][0]['start'] - 30.65) < .001
    assert not warnings

def test_missing_characters_are_flagged():
    class Partial(FakeWhisperX):
        def align(self, *args, **kwargs):
            return {'segments': [{'start': 0, 'end': 1,
                    'chars': [{'char': '你', 'start': 0, 'end': .2}]}]}
    audio = np.zeros(16000*5, dtype='float32')
    lines, warnings = mod.align_located_lines(Partial(), audio,
        [(0, {'start': 1, 'end': 2})], [{'text': '你好'}], None, None, 'cpu', 5.)
    assert lines[0]['needs_review']
    assert any(w['reason'] == 'incomplete character alignment' for w in warnings)

def test_failed_alignment_does_not_fabricate_timestamps():
    class Broken(FakeWhisperX):
        def align(self, *args, **kwargs): raise RuntimeError('model error')
    lines, warnings = mod.align_located_lines(Broken(), np.zeros(16000*5),
        [(0, {'start': 1, 'end': 2})], [{'text': '你好'}], None, None, 'cpu', 5.)
    assert not lines
    assert warnings[0]['reason'] == 'forced alignment failed'
