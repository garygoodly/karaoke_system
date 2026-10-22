from pathlib import Path
import pytest
from karaoke_phase0.separation import demucs_command, expected_stems, publish_stems
from karaoke_phase0.song_manager import import_song, get_song, set_song_status


def test_command_uses_current_python_and_song_folder(tmp_path):
    folder = tmp_path / 'song'
    folder.mkdir()
    (folder / 'song.mp3').write_bytes(b'mock')
    command = demucs_command(folder)
    assert command[1:4] == ['-u', '-m', 'demucs']
    assert '-d' in command and command[command.index('-d') + 1] == 'cuda'
    assert str(folder / 'song.mp3') == command[-1]


def test_missing_song(tmp_path):
    with pytest.raises(FileNotFoundError):
        demucs_command(tmp_path)


def test_publish_requires_both_stems(tmp_path):
    vocals, instrumental = expected_stems(tmp_path)
    vocals.parent.mkdir(parents=True)
    vocals.write_bytes(b'0' * 64)
    with pytest.raises(RuntimeError):
        publish_stems(tmp_path)
    assert not (tmp_path / 'generated' / 'vocals.wav').exists()
    instrumental.write_bytes(b'1' * 64)
    a, b = publish_stems(tmp_path)
    assert a.read_bytes() == b'0' * 64
    assert b.read_bytes() == b'1' * 64
    assert (tmp_path / 'generated' / 'separation.json').is_file()


def test_status_persistence(tmp_path):
    source = tmp_path / 'input.mp3'
    source.write_bytes(b'test-audio')
    result = import_song(tmp_path / 'songs', source, 'Test', lyrics_text='hello', confirm_move=True)
    set_song_status(tmp_path / 'songs', result['id'], 'analyzing')
    assert get_song(tmp_path / 'songs', result['id'])['status'] == 'analyzing'
    set_song_status(tmp_path / 'songs', result['id'], 'separated')
    assert get_song(tmp_path / 'songs', result['id'])['status'] == 'separated'
