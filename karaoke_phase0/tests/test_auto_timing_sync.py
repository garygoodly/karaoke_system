from karaoke_phase0.lyrics_preview import render

def test_auto_sync_ui_and_guardrails(tmp_path):
    target=tmp_path/'test.html'
    render({'lines': []},target,player_mode=True,reference_pitch={'frames':[{'time':0,'hz':220}]})
    html=target.read_text(encoding='utf-8')
    for token in ('autoTimingSync','estimateAutomaticOffset','resetAutoSync','Need more pitch changes','Ambiguous timing','offsetTrusted','micTimingOffset.disabled=true'):
        assert token in html
    assert 'Math.round(t/hop)' not in html
