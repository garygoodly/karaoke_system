import json
import tempfile
import unittest
from pathlib import Path
from karaoke_phase0.lyrics_display_data import load_word_timings
from karaoke_phase0.lyrics_preview import render


class DualDisplayTests(unittest.TestCase):
    def test_missing_mfa_defaults_to_line(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_word_timings(td), {})
            page = render({'lines': [], 'warnings': [], 'status': 'review_required'}, Path(td) / 'page.html')
            html = page.read_text(encoding='utf-8')
            self.assertIn('Line Mode', html)
            self.assertIn('Word Mode', html)
            self.assertIn("displayMode='line'", html)

    def test_latest_run_and_partial_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'generated' / 'mfa'
            for run, valid in ((7, True), (8, False)):
                folder = root / f'full_song_run_{run:02d}'
                folder.mkdir(parents=True)
                tokens = [{'text': '泡', 'start': 1.0, 'end': 1.2},
                          {'text': '沫', 'start': 1.2, 'end': 1.5}]
                data = {'lines': [{'line_id': 0, 'text': '泡沫', 'tokens': tokens,
                                   'warnings': [] if valid else [{'reason': 'unknown_or_missing_phones'}]}]}
                (folder / 'lyrics_timeline_mfa.json').write_text(json.dumps(data), encoding='utf-8')
            # Latest run is authoritative; don't silently use stale timings.
            self.assertEqual(load_word_timings(td), {})

    def test_valid_latest_run(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / 'generated' / 'mfa' / 'full_song_run_08'
            folder.mkdir(parents=True)
            data = {'lines': [{'line_id': 3, 'text': '泡沫', 'tokens': [
                {'text': '泡', 'start': 11.0, 'end': 11.3},
                {'text': '沫', 'start': 11.3, 'end': 11.9}], 'warnings': []}]}
            (folder / 'lyrics_timeline_mfa.json').write_text(json.dumps(data), encoding='utf-8')
            self.assertEqual(len(load_word_timings(td)[3]), 2)
