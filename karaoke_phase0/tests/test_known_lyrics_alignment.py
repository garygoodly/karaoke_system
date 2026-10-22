from types import SimpleNamespace
import numpy as np
from karaoke_phase0.known_lyrics_alignment import locate_lines, normalize


def test_normalize():
    assert normalize('陽光，下！') == '陽光下'


def test_lrc_windows_without_asr():
    lines = [{'text': '第一句', 'hint_start': 2.0},
             {'text': '第二句', 'hint_start': 5.0}]
    located, warnings, method = locate_lines(lines, np.zeros(16000 * 10), 'cpu', 'zh')
    assert method == 'lrc_hints'
    assert not warnings
    assert located[0][1]['end'] == 5.0
    assert located[1][1]['end'] == 10.0


def test_bad_lrc_is_reviewed():
    lines = [{'text': '錯誤', 'hint_start': 15.0},
             {'text': '正常', 'hint_start': 2.0}]
    located, warnings, _ = locate_lines(lines, np.zeros(16000 * 10), 'cpu', 'zh')
    assert len(located) == 1
    assert warnings[0]['line_id'] == 0
