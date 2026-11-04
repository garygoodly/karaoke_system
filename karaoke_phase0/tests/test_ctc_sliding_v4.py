import importlib.util
from pathlib import Path
import pytest

p = Path(__file__).resolve().parents[1] / 'tools' / 'benchmark_ctc_sliding_v4.py'
spec = importlib.util.spec_from_file_location('ctc_sliding_v4', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_full_run_has_two_distinct_contexts():
    lines = [{'start': i * 3} for i in range(8)]
    groups = m.make_sliding_groups(lines, set(range(8)))
    assert len(groups) == len(set(tuple(g) for g in groups))
    assert all(sum(i in g for g in groups) >= 2 for i in range(8))
    assert [0, 1] in groups and [6, 7] in groups


def test_unknown_splits_runs_and_no_fake_replicates():
    lines = [{'start': i * 3} for i in range(7)]
    groups = m.make_sliding_groups(lines, {0, 1, 2, 4, 5, 6})
    assert all(3 not in g for g in groups)
    assert all(not (2 in g and 4 in g) for g in groups)
    assert sum(0 in g for g in groups) == 2


def test_short_run_reports_single_context():
    lines = [{'start': i * 3} for i in range(2)]
    assert m.make_sliding_groups(lines, {0, 1}) == [[0, 1]]


def test_consensus_counts_failures_and_does_not_infer_stability_from_one():
    lines = [{'start': 10}, {'start': 20}]
    groups = [
        {'line_ids': [0, 1], 'status': 'candidate_needs_review', 'lines': [{'line_id': 0, 'start_seconds': 10.1}, {'line_id': 1, 'start_seconds': 20.1}]},
        {'line_ids': [0, 1], 'status': 'no_path'},
    ]
    result = m.summarize_consensus(groups, lines)
    assert result[0]['planned_observations'] == 2
    assert result[0]['observation_count'] == 1
    assert result[0]['spread_seconds'] is None
    assert result[0]['failed_group_statuses'] == ['no_path']
    assert result[0]['status'] == 'single_observation_needs_review'


def test_consensus_two_observations():
    lines = [{'start': 10}]
    groups = [{'line_ids': [0], 'status': 'candidate_needs_review', 'lines': [{'line_id': 0, 'start_seconds': t}]} for t in (10.1, 10.2)]
    r = m.summarize_consensus(groups, lines)[0]
    assert r['status'] == 'consistent_needs_review'
    assert r['spread_seconds'] == 0.1


def test_invalid_group_size():
    with pytest.raises(ValueError):
        m.make_sliding_groups([{'start': 0}], {0}, size=5)
