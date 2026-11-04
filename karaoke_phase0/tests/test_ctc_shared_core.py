"""Regression contracts for extracted CTC core functions."""
import sys
from pathlib import Path
import importlib.util
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from karaoke_phase0.alignment import ctc_core as core

def legacy(name):
    path = ROOT / 'tools' / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_legacy_functions_are_shared():
    assert legacy('benchmark_ctc_joint_lines.py').joint_viterbi is core.joint_viterbi
    assert legacy('benchmark_direct_ctc.py').ctc_subsequence_viterbi is core.ctc_subsequence_viterbi
    assert legacy('benchmark_ctc_grouped.py').boundaries is core.boundaries
    assert legacy('benchmark_ctc_sliding_v4.py').make_sliding_groups is core.make_sliding_groups

def test_joint_traceback_and_boundaries():
    # blank=0, token sequence 1 then 2, with blank between
    ids = [1, 2]
    lp = np.full((6, 3), -20.0)
    lp[0,0]=0;lp[1,1]=0;lp[2,0]=0;lp[3,2]=0;lp[4:,0]=0
    result = core.joint_viterbi(lp, ids, 0, 1)
    assert result is not None
    assert len(result['token_spans']) == 2
    b = core.boundaries(result['token_spans'], [1,1], lambda f: f * 0.02)
    assert b[0]['start_seconds'] < b[1]['start_seconds']

def test_invalid_group_size():
    with pytest.raises(ValueError):
        core.make_sliding_groups([{'start':0}], {0}, size=5)

def test_single_observation_not_consistent():
    r = core.summarize_consensus([{'line_ids':[0], 'status':'candidate_needs_review', 'lines':[{'line_id':0,'start_seconds':10.2}]}], [{'start':10}])
    assert r[0]['spread_seconds'] is None
    assert r[0]['status'] == 'single_observation_needs_review'
