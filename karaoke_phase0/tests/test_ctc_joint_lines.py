import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location('joint_ctc',Path(__file__).resolve().parents[1]/'tools'/'benchmark_ctc_joint_lines.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_joint_boundary_monotonic():
    # blank=0, A=1, B=2, C=3; adjacent lines: AB | C
    labels=[0,1,1,0,2,0,3,3,0]
    logits=np.full((len(labels),4),-12.0)
    for i,t in enumerate(labels): logits[i,t]=0.0
    r=mod.joint_viterbi(logits,[1,2,3],0,2)
    assert r is not None
    assert r['line1_last_token']['end_frame'] <= r['line2_first_token']['start_frame']
    assert r['line2_first_token']['start_frame'] == 6


def test_repeated_tokens_require_blank():
    labels=[1,0,1,2]
    logits=np.full((len(labels),3),-12.0)
    for i,t in enumerate(labels): logits[i,t]=0.0
    r=mod.joint_viterbi(logits,[1,1,2],0,2)
    assert r['token_spans'][0]['end_frame'] <= r['token_spans'][1]['start_frame']


def test_invalid_split():
    try: mod.joint_viterbi(np.zeros((4,3)),[1,2],0,2)
    except ValueError: pass
    else: raise AssertionError('Invalid split accepted')
