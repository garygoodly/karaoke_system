import json
import pytest
from karaoke_phase0.preparation_pipeline import prepare_song


def song(tmp_path):
    folder = tmp_path / 'song'
    folder.mkdir()
    (folder / 'song.mp3').write_bytes(b'mp3')
    (folder / 'lyrics.txt').write_text('Hello', encoding='utf-8')
    return folder


def artifacts(folder):
    g = folder / 'generated'
    g.mkdir(exist_ok=True)
    for name in ('vocals.wav', 'instrumental.wav'):
        (g / name).write_bytes(b'valid-audio')
    (g / 'lyrics_timeline.json').write_text('{"lines": [1]}')
    (g / 'reference_pitch.json').write_text('{"frames": [1]}')


def test_existing_outputs_are_reused(tmp_path):
    folder = song(tmp_path)
    artifacts(folder)
    result = prepare_song(folder, runner=lambda cmd: pytest.fail('unexpected process'))
    assert result['status'] == 'ready'
    assert all(x['status'] == 'skipped_existing' for x in result['steps'].values())


def test_missing_input_does_not_create_checkpoint(tmp_path):
    folder = tmp_path / 'song'
    folder.mkdir()
    with pytest.raises(FileNotFoundError):
        prepare_song(folder)
    assert not (folder / 'generated').exists()


def test_failure_checkpoint_and_retry(tmp_path, monkeypatch):
    folder = song(tmp_path)
    from karaoke_phase0 import separation
    def fake_publish(path):
        g = path / 'generated'
        g.mkdir(exist_ok=True)
        (g / 'vocals.wav').write_bytes(b'vocals')
        (g / 'instrumental.wav').write_bytes(b'music')
    monkeypatch.setattr(separation, 'publish_stems', fake_publish)
    with pytest.raises(RuntimeError, match='demucs failed'):
        prepare_song(folder, runner=lambda cmd: (_ for _ in ()).throw(RuntimeError('demucs failed')))
    state = json.loads((folder / 'generated' / 'preparation_status.json').read_text())
    assert state['steps']['separation']['status'] == 'failed'
    calls = []
    def run(cmd):
        calls.append(cmd)
        fake_publish(folder)
    from karaoke_phase0 import alignment_workflow, reference_pitch
    def align(path, device):
        (path / 'generated' / 'lyrics_timeline.json').write_text('{"lines": [1]}')
    def extract(wav, out, device):
        out.write_text('{"frames": [1]}')
    monkeypatch.setattr(alignment_workflow, 'align_song', align)
    monkeypatch.setattr(reference_pitch, 'extract_reference', extract)
    result = prepare_song(folder, runner=run)
    assert result['status'] == 'ready'
    assert len(calls) == 1
    assert result['steps']['separation']['status'] == 'completed'
    result = prepare_song(folder, runner=lambda cmd: pytest.fail('should skip'))
    assert result['status'] == 'ready'
