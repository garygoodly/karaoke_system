import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'tools' / 'diagnose_ctc_character_boundaries.py'
spec = importlib.util.spec_from_file_location('ctc_character_diagnostics', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_partition_spans():
    spans = [{'start_frame': i * 2, 'end_frame': i * 2 + 1} for i in range(4)]
    out = mod.partition_tokens([23, 24], [[1, 2], [3, 4]], spans, lambda t: t * 0.1)
    assert out[0]['end_seconds'] == 0.3
    assert out[1]['start_seconds'] == 0.4


def test_partition_rejects_wrong_count():
    import pytest
    with pytest.raises(ValueError):
        mod.partition_tokens([1], [[1, 2]], [{'start_frame': 0, 'end_frame': 1}], float)


def test_boundary_summary_with_previous():
    rows = [{'line_ids': [23, 24], 'status': 'candidate_needs_review', 'lines': [
        {'line_id': 23, 'tokens': [{'start_seconds': 222., 'end_seconds': 228.4}]},
        {'line_id': 24, 'tokens': [{'start_seconds': 229.1, 'end_seconds': 229.3}]}]}]
    result = mod.boundary_summary(rows, 24)
    assert result[0]['gap_seconds'] == 0.7
    assert mod.boundary_summary(rows, 23)[0]['previous_last_end'] is None


def test_boundary_summary_skips_failed_groups():
    assert mod.boundary_summary([{'line_ids': [23, 24], 'status': 'no_path'}], 24) == []
