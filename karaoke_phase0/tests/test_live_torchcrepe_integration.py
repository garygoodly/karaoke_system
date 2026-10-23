from pathlib import Path
from karaoke_phase0.lyrics_preview import render


def test_detector_switch_and_websocket(tmp_path):
    out = tmp_path / 'preview.html'
    render({'lines': []}, out, player_mode=True)
    html = out.read_text(encoding='utf-8')
    assert 'id="pitchDetector"' in html
    assert 'ws://127.0.0.1:8766' in html
    assert 'closePitchSocket()' in html
    assert "pitchDetector.value==='yin'" in html


def test_backend_loopback_only():
    src = (Path(__file__).resolve().parents[1] / 'tools' / 'run_live_torchcrepe.py').read_text(encoding='utf-8')
    assert "'127.0.0.1'" in src
    assert 'return_periodicity=True' in src
