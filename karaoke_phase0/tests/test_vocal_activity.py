import numpy as np
import soundfile as sf
from karaoke_phase0.vocal_activity import build_mask, singing_coverage


def test_intro_excluded(tmp_path):
    sr = 8000
    t = np.arange(sr * 3) / sr
    signal = np.where(t >= 1, 0.2 * np.sin(2 * np.pi * 220 * t), 0).astype('float32')
    wav = tmp_path / 'vocals.wav'
    sf.write(wav, signal, sr)
    ref = {'frames': [{'time': i / 50, 'hz': 220, 'periodicity': 0.9} for i in range(150)]}
    mask = build_mask(wav, {'lines': [{'start': 1, 'end': 2.8}]}, ref)
    assert not any(x['active'] for x in mask['frames'] if x['time'] < 0.85)
    assert any(x['active'] for x in mask['frames'] if 1.2 < x['time'] < 2)
    users = [{'time': 0.3, 'hz': None}, {'time': 1.5, 'hz': 220, 'periodicity': 0.9},
             {'time': 1.7, 'hz': None}]
    c = singing_coverage(mask, users)
    assert c['outside_vocal_activity'] == 1
    assert c['expected_frames'] == 2
    assert c['singing_coverage'] == 0.5
