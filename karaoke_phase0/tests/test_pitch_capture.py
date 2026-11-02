from pathlib import Path
from karaoke_phase0.lyrics_preview import render

def test_pitch_capture_ui(tmp_path):
    p=tmp_path/'p.html'
    render({'lines': []},p,player_mode=True)
    h=p.read_text(encoding='utf-8')
    for fragment in ('id="startPitchCapture"','id="stopPitchCapture"','function recordPitchSample(hz,periodicity)', 'recordPitchSample(rawHz,Number(data.periodicity))', 'playback_time_s', 'offset_trusted'):
        assert fragment in h
