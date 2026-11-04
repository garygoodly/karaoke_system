import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[1] / 'tools' / 'benchmark_ctc_overlapping.py'
spec = importlib.util.spec_from_file_location('ctc_overlap', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_sliding_windows_cover_all():
    lines = [{'start': i * 3} for i in range(7)]
    groups = mod.make_overlapping_groups(lines, set(range(7)), 3, 2)
    assert groups == [[0, 1, 2], [2, 3, 4], [4, 5, 6]]


def test_unsupported_splits_runs():
    lines = [{'start': i * 3} for i in range(7)]
    assert mod.make_overlapping_groups(lines, {0, 1, 2, 4, 5, 6}) == [[0, 1, 2], [4, 5, 6]]


def test_tail_window():
    lines = [{'start': i * 3} for i in range(6)]
    assert mod.make_overlapping_groups(lines, set(range(6))) == [[0, 1, 2], [2, 3, 4], [3, 4, 5]]


def test_consensus_and_abstention():
    lines = [{'start': 10}, {'start': 20}, {'start': 30}]
    groups = [
        {'status': 'candidate_needs_review', 'lines': [{'line_id': 1, 'start_seconds': 20.1}]},
        {'status': 'candidate_needs_review', 'lines': [{'line_id': 1, 'start_seconds': 20.2}, {'line_id': 2, 'start_seconds': 31}]},
    ]
    result = mod.summarize_consensus(groups, lines)
    assert result[0]['status'] == 'no_candidate'
    assert result[1]['status'] == 'consistent_needs_review'
    assert result[1]['median_start'] == 20.15
    assert result[2]['status'] == 'single_observation_needs_review'


def test_disagreement():
    lines = [{'start': 10}]
    groups = [{'status': 'candidate_needs_review', 'lines': [{'line_id': 0, 'start_seconds': v}]} for v in [9, 11]]
    assert mod.summarize_consensus(groups, lines)[0]['status'] == 'disagreement_needs_review'


def test_invalid_stride():
    with pytest.raises(ValueError):
        mod.make_overlapping_groups([{'start': 0}], {0}, size=3, stride=3)
