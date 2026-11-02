from karaoke_phase0.lyrics_preview import render


def test_score_ui_and_data(tmp_path):
    out = tmp_path / 'player.html'
    render({'lines': []}, out, player_mode=True,
           reference_pitch={'frames': [{'time': 1.0, 'hz': 220, 'periodicity': 0.9}]},
           vocal_activity={'frames': [{'time': 1.0, 'active': True}]})
    html = out.read_text(encoding='utf-8')
    for token in ('id="singingScorePanel"', 'id="scoreAccuracy"', 'id="scoreCoverage"',
                  'function scoreCapturedFrames(', 'showCaptureScore();',
                  '"vocal_activity"', '"reference_pitch"', 'offset_ms'):
        assert token in html


def test_empty_mask_is_graceful(tmp_path):
    out = tmp_path / 'player.html'
    render({'lines': []}, out, player_mode=True)
    assert 'Mask missing' in out.read_text(encoding='utf-8')
