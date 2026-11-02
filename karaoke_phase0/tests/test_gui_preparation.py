from pathlib import Path


def test_gui_preparation_wiring():
    source = (Path(__file__).resolve().parents[1] / 'src' / 'karaoke_phase0' / 'gui.py').read_text(encoding='utf-8')
    assert "QPushButton('Prepare Song / Retry')" in source
    assert "self.process.start(sys.executable, [str(script), '--song-folder', str(folder), '--device', device])" in source
    assert 'self.prepare_timer.start(500)' in source
    assert "if task == 'preparation':" in source
    assert 'self.prepare_timer.stop()' in source
    assert 'self.prepare_btn.setEnabled(True)' in source
