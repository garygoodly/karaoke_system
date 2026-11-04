import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('benchmark_direct_ctc',Path(__file__).resolve().parents[1]/'tools'/'benchmark_direct_ctc.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_finds_subsequence_after_unrelated_audio():
    # blank=0, target=1,2; target begins at frame 3
    labels=[0,0,0,1,1,0,2,2,0,0]
    lp=np.full((len(labels),3),-12.0)
    for i,v in enumerate(labels): lp[i,v]=-.001
    hit=mod.ctc_subsequence_viterbi(lp,[1,2],0)
    assert hit is not None
    assert hit['start_frame'] in (3,4)
    assert hit['end_frame'] in (7,8,9)

def test_repeated_char_requires_blank():
    labels=[0,1,1,0,1,0]
    lp=np.full((len(labels),2),-10.)
    for i,v in enumerate(labels): lp[i,v]=-.001
    hit=mod.ctc_subsequence_viterbi(lp,[1,1],0)
    assert hit is not None and hit['start_frame'] in (1,2)

def test_invalid_token_rejected():
    import pytest
    with pytest.raises(ValueError):
        mod.ctc_subsequence_viterbi(np.zeros((4,3)),[0],0)
