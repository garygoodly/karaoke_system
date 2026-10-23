import math
import tempfile
import unittest
from pathlib import Path
from karaoke_phase0.reference_pitch import note_cents, nearest_reference
from karaoke_phase0.lyrics_preview import render


class ReferencePitchTests(unittest.TestCase):
    def test_cents(self):
        self.assertAlmostEqual(note_cents(440, 440), 0)
        self.assertAlmostEqual(note_cents(440, 880), 1200)
        self.assertIsNone(note_cents(None, 440))

    def test_nearest(self):
        frames = [{'time': 0, 'hz': 220}, {'time': .02, 'hz': None}, {'time': .04, 'hz': 230}]
        self.assertEqual(nearest_reference(frames, .04)['hz'], 230)
        self.assertIsNone(nearest_reference(frames, 1))

    def test_ui_embeds_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'qa.html'
            render({'lines': []}, target, player_mode=True,
                   reference_pitch={'frames': [{'time': 0, 'hz': 220}], 'hop_seconds': .02})
            page = target.read_text(encoding='utf-8')
            self.assertIn('referenceHz', page)
            self.assertIn('pitchDifference', page)
            self.assertIn('torchcrepe (local Python)', page)
            self.assertIn('crepeSmoothing" type="checkbox" checked', page)


def test_reference_lookup_uses_timestamps_not_frame_index():
    from karaoke_phase0.lyrics_preview import render
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / 'qa.html'
        render({'lines': []}, out, reference_pitch={'frames': []})
        html = out.read_text(encoding='utf-8')
        assert 'referenceFrames[mid].time<t' in html
        assert 'Math.round(t/hop)' not in html
