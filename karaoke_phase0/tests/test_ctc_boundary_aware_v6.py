import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'tools' / 'diagnose_ctc_boundary_aware_v6.py'
spec = importlib.util.spec_from_file_location('ctc_boundary_aware_v6', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def group(ids, starts, ends):
    return {'status': 'candidate_needs_review', 'line_ids': ids, 'lines': [
        {'line_id': i, 'start_seconds': s, 'end_seconds': e}
        for i, s, e in zip(ids, starts, ends)]}


def test_previous_context_excludes_early_unanchored_candidate():
    groups = [group([22, 23, 24], [216, 223, 229.112], [222, 228.412, 234]),
              group([23, 24, 25], [223, 229.508, 235], [228.407, 234, 241]),
              group([24, 25, 26], [228.382, 235, 242], [234, 241, 248])]
    r = mod.select_boundary_candidates([{'line_id': 24, 'original_start': 229.5}], groups)[0]
    assert r['anchored_count'] == 2
    assert r['unanchored_count'] == 1
    assert r['token_peak_median'] == 229.31
    assert r['estimated_acoustic_onset'] is None
    assert r['status'] == 'consistent_boundary_candidate_needs_review'


def test_overlapping_previous_end_is_rejected():
    r = mod.select_boundary_candidates([{'line_id': 2}], [group([1, 2], [31, 35], [36, 39])])[0]
    assert r['anchored_count'] == 0
    assert r['order_rejected_count'] == 1
    assert r['status'] == 'no_boundary_anchored_candidate'


def test_disagreement_is_not_averaged_into_confidence():
    groups = [group([1, 2], [31, 39], [37, 43]), group([1, 2, 3], [31, 40], [37, 44])]
    r = mod.select_boundary_candidates([{'line_id': 2}], groups)[0]
    assert r['token_peak_spread_seconds'] == 1.0
    assert r['status'] == 'boundary_disagreement_needs_review'


def test_single_observation_spread_is_null():
    r = mod.select_boundary_candidates([{'line_id': 2}], [group([1, 2], [31, 39], [37, 43])])[0]
    assert r['token_peak_spread_seconds'] is None
    assert r['status'] == 'single_boundary_candidate_needs_review'


def test_invalid_threshold():
    import pytest
    with pytest.raises(ValueError):
        mod.select_boundary_candidates([], [], tolerance=-1)
