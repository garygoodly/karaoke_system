import importlib.util
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('pitch_ab',Path(__file__).resolve().parents[1]/'tools'/'compare_pitch_yin_crepe.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_yin_sine_220():
    sr=16000
    t=np.arange(4096)/sr
    hz,reason=module.yin_frame((0.2*np.sin(2*np.pi*220*t)).astype('float32'),sr)
    assert reason=='voiced' and abs(hz-220)<3

def test_yin_low_volume_gate():
    hz,reason=module.yin_frame(np.zeros(4096),16000)
    assert np.isnan(hz) and reason=='below_rms_gate'

def test_stats_octave_jump():
    s=module.stats([220,220,440,440,float('nan')],0.01)
    assert s['octave_sized_jumps_over_900_cents']==1
