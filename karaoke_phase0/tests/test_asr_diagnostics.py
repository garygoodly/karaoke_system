import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from karaoke_phase0.known_lyrics_alignment import locate_lines


def test_txt_diagnostic_includes_unmatched_and_skipped_segments(monkeypatch, tmp_path):
    class FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio, **kwargs):
            segments = [
                SimpleNamespace(start=2.0, end=3.0, text='第一句'),
                SimpleNamespace(start=31.0, end=32.0, text='無關內容'),
                SimpleNamespace(start=88.0, end=89.0, text='第二句'),
            ]
            return iter(segments), None

    monkeypatch.setitem(sys.modules, 'faster_whisper', SimpleNamespace(WhisperModel=FakeWhisperModel))
    target = tmp_path / 'generated' / 'asr_segments.json'
    lines = [{'text': '第一句'}, {'text': '不存在的句子'}, {'text': '第二句'}]
    locate_lines(lines, np.zeros(16000 * 100), 'cpu', 'zh', diagnostic_path=target)
    data = json.loads(target.read_text(encoding='utf-8'))
    assert len(data['asr_segments']) == 3
    assert data['asr_segments'][1]['start'] == 31.0
    assert len(data['line_matches']) == 3
    assert data['line_matches'][1]['status'] == 'unmatched'
    assert data['line_matches'][2]['status'] == 'matched'
    assert 1 in data['unused_asr_segment_indices']


def test_lrc_does_not_create_asr_diagnostic(tmp_path):
    target = tmp_path / 'asr_segments.json'
    lines = [{'text': '第一句', 'hint_start': 1.0}]
    locate_lines(lines, np.zeros(16000 * 5), 'cpu', 'zh', diagnostic_path=target)
    assert not target.exists()
