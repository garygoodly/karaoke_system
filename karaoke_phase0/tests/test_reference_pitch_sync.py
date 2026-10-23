from pathlib import Path
from karaoke_phase0.lyrics_preview import render

def test_reference_controls_and_timestamp_lookup(tmp_path):
    page=tmp_path/'page.html'
    render({'lines':[]},page,player_mode=True,reference_pitch={'frames':[{'time':0,'hz':220}]})
    html=page.read_text(encoding='utf-8')
    for expected in ('referenceSmoothing','micTimingOffset','referenceFrames[mid].time<t','lastMicMeasurementAt','values.sort((a,b)=>a-b)'):
        assert expected in html
    assert 'Math.round(t/hop)' not in html
