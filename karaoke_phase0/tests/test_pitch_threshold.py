import tempfile
import unittest
from pathlib import Path
from karaoke_phase0.lyrics_preview import render

class PitchThresholdTests(unittest.TestCase):
    def test_adjustable_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            html=Path(render({'lines': []}, Path(td)/'preview.html', player_mode=True)).read_text(encoding='utf-8')
        self.assertIn('id="pitchThreshold"', html)
        self.assertIn('pitchMinimumRms()', html)
        self.assertIn('function detectPitch(samples,sampleRate,minRms=0.012)', html)
        self.assertIn('pitchThreshold.addEventListener', html)
