import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'prepare_song_with_ctc_shadow.py'
spec = importlib.util.spec_from_file_location('shadow_entrypoint_under_test', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def song(tmp_path):
    g = tmp_path / 'generated'
    g.mkdir()
    (g / 'vocals.wav').write_bytes(b'RIFFfake')
    (g / 'lyrics_timeline.json').write_text(json.dumps({'lines': [{'text': 'hello'}]}), encoding='utf-8')
    return tmp_path


def test_existing_artifacts_skip_full_preparation(tmp_path):
    folder = song(tmp_path)
    with patch.object(module, 'run_shadow', return_value={'status': 'completed'}) as runner:
        result = module.execute(folder)
    assert result['preparation'] == 'reused_existing'
    assert result['shadow']['status'] == 'completed'
    runner.assert_called_once()


def test_missing_artifacts_do_not_trigger_expensive_preparation(tmp_path):
    with patch.object(module, 'run_shadow') as runner:
        result = module.execute(tmp_path)
    assert result['shadow']['status'] == 'skipped_missing_inputs'
    runner.assert_not_called()


def test_invalid_timeline_rejected(tmp_path):
    folder = song(tmp_path)
    (folder / 'generated' / 'lyrics_timeline.json').write_text('{bad', encoding='utf-8')
    assert module.execute(folder)['shadow']['status'] == 'skipped_missing_inputs'
