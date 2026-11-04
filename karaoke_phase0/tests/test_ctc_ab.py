import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('benchmark_ctc_ab', Path(__file__).resolve().parents[1]/'tools'/'benchmark_ctc_ab.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def c(start,end,score):
    return {'start_seconds':start,'end_seconds':end,'total_log_probability':score}

def test_dedup_same_event():
    hits=mod.deduplicate([c(32.462,34.104,-15),c(32.477,34.139,-22),c(120,124,-30)])
    assert len(hits)==2 and hits[0]['start_seconds']==32.462

def test_dedup_different_events():
    assert len(mod.deduplicate([c(10,11,-2),c(12,13,-3)]))==2

def test_asr_delta():
    x=mod.analyze_candidates([c(32.462,34.104,-15)],32.,5)
    assert x['candidates'][0]['delta_vs_asr_start_seconds']==0.462

def test_no_asr():
    x=mod.analyze_candidates([c(32,34,-15)],None)
    assert x['candidates'][0]['delta_vs_asr_start_seconds'] is None
