import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('diagnose_pitch_score',Path(__file__).resolve().parents[1]/'tools'/'diagnose_pitch_score.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_confidence_and_octave_outlier():
    refs=[{'time':0,'hz':220,'periodicity':0.9},{'time':0.1,'hz':220,'periodicity':0.9}]
    users=[{'time_s':'0','crepe_hz':'880','crepe_periodicity':'0.1'},
           {'time_s':'0.1','crepe_hz':'220','crepe_periodicity':'0.9'}]
    r=module.evaluate(refs,users)
    assert r['counts']['user_low_confidence']==1
    assert r['matched']==1 and r['score']==100
    assert module.evaluate(refs,users,0.05)['counts']['error_over_600']==1


def test_capture_time_alignment():
    refs=[{'time':0,'hz':220,'periodicity':1},{'time':0.2,'hz':440,'periodicity':1}]
    users=[{'time_s':'0','playback_time_s':'0.2','crepe_hz':'220','crepe_periodicity':'1'}]
    assert module.evaluate(refs,users)['score']==100
    assert module.evaluate(refs,users,use_capture_time=False)['score']==0
