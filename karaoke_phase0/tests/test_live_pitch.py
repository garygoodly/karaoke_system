import tempfile
import shutil
import subprocess
import unittest
from pathlib import Path
from karaoke_phase0.lyrics_preview import render


class LivePitchTests(unittest.TestCase):
    def test_pitch_ui_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as td:
            path = render({'lines': []}, Path(td) / 'preview.html', player_mode=True)
            html = Path(path).read_text(encoding='utf-8')
        self.assertIn('id="pitchHz"', html)
        self.assertIn('id="pitchNote"', html)
        self.assertIn('id="pitchCanvas"', html)
        self.assertIn('resetPitch();micLevel.value=0', html)
        self.assertIn('micAnalyser.fftSize=4096', html)
        self.assertIn('if(rms<minRms)return null', html)
        self.assertIn('id="pitchThreshold"', html)

    @unittest.skipUnless(shutil.which('node'), 'Node.js not installed')
    def test_synthetic_tones_and_silence(self):
        with tempfile.TemporaryDirectory() as td:
            path = render({'lines': []}, Path(td) / 'preview.html', player_mode=True)
            html = Path(path).read_text(encoding='utf-8')
        js = html.split('function detectPitch(', 1)[1].split('function drawPitch(', 1)[0]
        code = 'function detectPitch(' + js
        script = code + '''
const sr=44100, n=4096;
const wave=f=>Float32Array.from({length:n},(_,i)=>0.25*Math.sin(2*Math.PI*f*i/sr));
const a=detectPitch(wave(440),sr), c=detectPitch(wave(261.6256),sr);
const silent=detectPitch(new Float32Array(n),sr);
if(Math.abs(a-440)>6 || Math.abs(c-261.6256)>6 || silent!==null || pitchToNote(a)!=='A4' || pitchToNote(c)!=='C4'){
  console.error({a,c,silent});process.exit(1);
}
'''
        subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
