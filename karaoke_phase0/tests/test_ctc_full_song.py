import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('ctc_full', Path(__file__).resolve().parents[1] / 'tools' / 'benchmark_ctc_full_song.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def hit(start, end, score=-0.2):
    return {'start_seconds':start, 'end_seconds':end, 'mean_log_probability':score, 'total_log_probability':score*10}

def test_deduplication():
    assert len(mod.deduplicate([hit(2,3), hit(2.1,3.1), hit(7,8)])) == 2

def test_monotonic_order():
    lines = [{'candidates':[hit(10,11), hit(30,31)]}, {'candidates':[hit(5,6), hit(12,13)]}]
    result = mod.ordered_path(lines)
    assert result[0]['start_seconds'] == 10
    assert result[1]['start_seconds'] == 12

def test_missing_line_skipped():
    result = mod.ordered_path([{'candidates':[hit(2,3)]}, {'candidates':[]}, {'candidates':[hit(5,6)]}])
    assert result[1] is None

def test_no_reversed_alignment():
    result = mod.ordered_path([{'candidates':[hit(8,10)]}, {'candidates':[hit(6,7)]}])
    assert sum(x is not None for x in result) <= 1
