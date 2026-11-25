"""Regression: shadow diagnostics must be independent of timeline review status."""
import json
import pytest
from karaoke_phase0.preparation_pipeline import prepare_song


def make_song(tmp_path, timeline):
    folder = tmp_path / "song"
    folder.mkdir()
    (folder / "song.mp3").write_bytes(b"mp3")
    (folder / "lyrics.txt").write_text("Hello", encoding="utf-8")
    generated = folder / "generated"
    generated.mkdir()
    (generated / "vocals.wav").write_bytes(b"audio")
    (generated / "instrumental.wav").write_bytes(b"audio")
    (generated / "reference_pitch.json").write_text('{"frames":[1]}')
    (generated / "lyrics_timeline.json").write_text(json.dumps(timeline))
    return folder


@pytest.mark.parametrize("timeline", [
    {"status": "review_required", "lines": [{"text": "Hello", "needs_review": True}]},
    {"lines": [{"text": "Hello", "needs_review": True}]},
])
def test_review_timeline_remains_review_required_but_shadow_runs(tmp_path, monkeypatch, timeline):
    folder = make_song(tmp_path, timeline)
    from karaoke_phase0.alignment import shadow_mode
    calls = []
    monkeypatch.setattr(shadow_mode, 'run_shadow', lambda *a, **k: (calls.append(1) or {'status': 'completed'}))
    result = prepare_song(folder, ctc_shadow=True, runner=lambda cmd: pytest.fail('unexpected process'))
    assert calls == [1]
    assert result['status'] == 'review_required'
    assert result['ctc_shadow']['status'] == 'completed'
    saved = json.loads((folder / 'generated' / 'preparation_status.json').read_text())
    assert saved['status'] == 'review_required'
    assert saved['ctc_shadow']['status'] == 'completed'


def test_shadow_failure_does_not_override_review_required(tmp_path, monkeypatch):
    folder = make_song(tmp_path, {"status": "review_required", "lines": [{"text": "Hello"}]})
    from karaoke_phase0.alignment import shadow_mode
    def fail(*args, **kwargs):
        raise RuntimeError('simulated model failure')
    monkeypatch.setattr(shadow_mode, 'run_shadow', fail)
    result = prepare_song(folder, ctc_shadow=True)
    assert result['status'] == 'review_required'
    assert result['ctc_shadow']['status'] == 'failed'


def test_shadow_default_off(tmp_path, monkeypatch):
    folder = make_song(tmp_path, {"status": "review_required", "lines": [{"text": "Hello"}]})
    from karaoke_phase0.alignment import shadow_mode
    monkeypatch.setattr(shadow_mode, 'run_shadow', lambda *a, **k: pytest.fail('must not run'))
    result = prepare_song(folder)
    assert result['status'] == 'review_required'
    assert 'ctc_shadow' not in result
