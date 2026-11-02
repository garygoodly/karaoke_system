import re
import shutil
import subprocess
from pathlib import Path
import pytest
from karaoke_phase0.lyrics_preview import render


def test_smoothing_ui_and_mode_isolation(tmp_path):
    output = tmp_path / 'player.html'
    render({'lines': []}, output, player_mode=True)
    html = output.read_text(encoding='utf-8')
    assert 'id="crepeSmoothing"' in html
    assert 'medianPitchFrame(rawHz,crepeSmoothing.checked)' in html
    assert 'const yinHz=detectPitch(samples,micContext.sampleRate,pitchMinimumRms());' in html
    assert 'showPitch(yinHz);' in html
    assert 'recordPitchSample(yinHz,null);' in html
    assert 'function resetPitch(){' in html
    assert 'resetAutoSync();' in html
    assert 'crepePitchWindow.length=0;' in html


def test_causal_median_and_unvoiced_reset():
    if not shutil.which('node'):
        pytest.skip('Node.js not available for JS function test')
    source = (Path(__file__).resolve().parents[1] / 'src/karaoke_phase0/lyrics_preview.py').read_text(encoding='utf-8')
    fn = re.search(r'function medianPitchFrame\(hz, enabled\)\{.*?\n\}', source, re.S)
    assert fn
    js = ('const crepePitchWindow=[];\n' + fn.group() + '''
const assert=require('node:assert/strict');
const seq=[220,221,440,219,220];
const result=seq.map(x=>medianPitchFrame(x,true));
assert.equal(result[4],220);
assert.equal(medianPitchFrame(null,true),null);
assert.equal(medianPitchFrame(330,true),330);
assert.equal(medianPitchFrame(440,false),440);
assert.equal(medianPitchFrame(220,true),330);
''')
    subprocess.run(['node','-e',js], check=True, capture_output=True, text=True)
