import json
from pathlib import Path
from karaoke_phase0.preparation_pipeline import prepare_song


def _song(tmp_path):
    folder = tmp_path / 'song'
    generated = folder / 'generated'
    generated.mkdir(parents=True)
    (folder / 'song.mp3').write_bytes(b'example')
    (folder / 'lyrics.txt').write_text('hello', encoding='utf-8')
    for name in ('vocals.wav', 'instrumental.wav'):
        (generated / name).write_bytes(b'example')
    (generated / 'lyrics_timeline.json').write_text('{"lines":[{"text":"hello"}]}')
    (generated / 'reference_pitch.json').write_text('{"frames":[1]}')
    return folder


def test_disabled_does_not_run_shadow(tmp_path, monkeypatch):
    folder = _song(tmp_path)
    from karaoke_phase0.alignment import shadow_mode
    monkeypatch.setattr(shadow_mode, 'run_shadow', lambda *a, **k: (_ for _ in ()).throw(AssertionError('called')))
    result = prepare_song(folder, runner=lambda cmd: (_ for _ in ()).throw(AssertionError('preparation reran')))
    assert result['status'] == 'ready'
    assert 'ctc_shadow' not in result


def test_opt_in_runs_once_and_preserves_timeline(tmp_path, monkeypatch):
    folder = _song(tmp_path)
    from karaoke_phase0.alignment import shadow_mode
    before = (folder / 'generated' / 'lyrics_timeline.json').read_bytes()
    calls = []
    def fake_run(song, **kwargs):
        calls.append((song, kwargs))
        return {'status': 'completed', 'output': 'shadow.json'}
    monkeypatch.setattr(shadow_mode, 'run_shadow', fake_run)
    result = prepare_song(folder, ctc_shadow=True, ctc_shadow_python='custom-python')
    assert result['status'] == 'ready'
    assert result['ctc_shadow']['status'] == 'completed'
    assert calls[0][1]['python'] == 'custom-python'
    assert len(calls) == 1
    assert (folder / 'generated' / 'lyrics_timeline.json').read_bytes() == before
    saved = json.loads((folder / 'generated' / 'preparation_status.json').read_text())
    assert saved['ctc_shadow']['status'] == 'completed'


def test_shadow_failure_is_isolated(tmp_path, monkeypatch):
    folder = _song(tmp_path)
    from karaoke_phase0.alignment import shadow_mode
    monkeypatch.setattr(shadow_mode, 'run_shadow', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('GPU unavailable')))
    result = prepare_song(folder, ctc_shadow=True)
    assert result['status'] == 'ready'
    assert result['ctc_shadow']['status'] == 'failed'
    assert 'GPU unavailable' in result['ctc_shadow']['reason']
    assert json.loads((folder / 'generated' / 'preparation_status.json').read_text())['status'] == 'ready'
