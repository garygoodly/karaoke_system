import csv
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'annotate_acoustic_onsets.py'
spec = importlib.util.spec_from_file_location('annotate_acoustic_onsets', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_roundtrip_labels(tmp_path):
    output = tmp_path / 'onsets.csv'
    mod.save_labels(output, {24: 229.112, 2: 38.045})
    assert mod.read_labels(output) == {2: 38.045, 24: 229.112}
    assert [int(x['line_id']) for x in csv.DictReader(output.open())] == [2, 24]


def test_read_v7(tmp_path):
    path = tmp_path / 'report.json'
    path.write_text(json.dumps({'lines': [{'line_id': 2, 'token_peak_seconds': 39.0}]}))
    assert mod.load_lines(path)[2]['token_peak_seconds'] == 39.0


def test_clip_bounds():
    import numpy as np
    pcm = mod.clip_pcm(np.ones(100, dtype=float), 100, -.5, .2)
    assert len(pcm) == 40
