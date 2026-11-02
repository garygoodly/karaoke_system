from pathlib import Path


def test_primary_buttons_and_hidden_legacy_actions():
    source = (Path(__file__).resolve().parents[1] / 'src/karaoke_phase0/gui.py').read_text(encoding='utf-8')
    assert "buttons.addWidget(self.prepare_btn)" in source
    assert "buttons.addWidget(self.lyrics_preview_btn)" in source
    assert "buttons.addWidget(self.analyze_btn)" not in source
    assert "buttons.addWidget(self.align_btn)" not in source
    assert 'self.analyze_btn.hide()' in source
    assert 'self.align_btn.hide()' in source


def test_ready_requires_all_outputs(tmp_path):
    from karaoke_phase0.gui import SongLibrary
    generated = tmp_path / 'generated'
    generated.mkdir()
    assert SongLibrary.display_song_status(tmp_path, 'imported') == 'imported'
    for name in ('vocals.wav', 'instrumental.wav'):
        (generated / name).write_bytes(b'audio')
    assert SongLibrary.display_song_status(tmp_path, 'separated') != 'Ready'
    for name in ('lyrics_timeline.json', 'reference_pitch.json'):
        (generated / name).write_text('{"data": [1]}', encoding='utf-8')
    assert SongLibrary.display_song_status(tmp_path, 'separated') == 'Ready'
    (generated / 'preparation_status.json').write_text('{"status":"failed"}', encoding='utf-8')
    assert SongLibrary.display_song_status(tmp_path, 'separated') == 'Needs review'
    (generated / 'preparation_status.json').write_text('{"status":"ready"}', encoding='utf-8')
    assert SongLibrary.display_song_status(tmp_path, 'separated') == 'Ready'
