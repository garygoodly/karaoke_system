import importlib.util
from pathlib import Path
import pytest

path = Path(__file__).resolve().parents[1] / 'tools' / 'benchmark_ctc_grouped.py'
spec = importlib.util.spec_from_file_location('grouped_ctc', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_grouping_skips_unknown_and_splits_long_gaps():
    lines = [{'start': v} for v in [0, 3, 6, 9, 30, 33, 36]]
    assert mod.make_groups(lines, {0, 1, 2, 4, 5, 6}, size=3) == [[0, 1, 2], [4, 5, 6]]


def test_grouping_remainder_and_max_size():
    lines = [{'start': i*3} for i in range(5)]
    assert mod.make_groups(lines, set(range(5)), size=3) == [[0, 1, 2], [3, 4]]
    with pytest.raises(ValueError):
        mod.make_groups(lines, set(range(5)), size=5)


def test_token_boundaries():
    spans = [{'start_frame': i*5, 'end_frame': i*5+2} for i in range(5)]
    got = mod.boundaries(spans, [2, 3], lambda f: 100 + f*0.02)
    assert got == [{'start_seconds': 100.0, 'end_seconds': 100.14},
                   {'start_seconds': 100.2, 'end_seconds': 100.44}]


def test_invalid_partition():
    with pytest.raises(ValueError):
        mod.boundaries([{'start_frame':0,'end_frame':1}], [2], float)
