import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from karaoke_phase0.lyrics_preview import render
from karaoke_phase0.lyrics_qa_server import start_preview_server


class KaraokePlayerTests(unittest.TestCase):
    def test_player_controls_and_line_mode_default(self):
        with tempfile.TemporaryDirectory() as td:
            page = render({'lines': [], 'warnings': [], 'status': 'review_required'},
                          Path(td)/'qa.html', player_mode=True)
            html = page.read_text(encoding='utf-8')
            for control in ('instrumentalVolume', 'vocalVolume', 'togglePlay', 'restart', 'seek'):
                self.assertIn(control, html)
            self.assertIn("displayMode='line'", html)
            self.assertIn('const playback=()', html)

    def test_instrumental_route_and_range(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            page=render({'lines': [], 'warnings': []}, root/'qa.html', player_mode=True)
            vocals=root/'vocals.wav'; vocals.write_bytes(b'vocaldata')
            instrumental=root/'instrumental.wav'; instrumental.write_bytes(b'instrumentaldata')
            server,url=start_preview_server(page,vocals,instrumental)
            try:
                with urlopen(url+'instrumental.wav') as response:
                    self.assertEqual(response.read(),b'instrumentaldata')
                with self.assertRaises(HTTPError) as error:
                    urlopen(url+'song.mp3')
                self.assertEqual(error.exception.code,404)
            finally:
                server.shutdown();server.server_close()

    def test_missing_instrumental_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'qa.html').write_text('page');(root/'vocals.wav').write_bytes(b'v')
            with self.assertRaises(FileNotFoundError):
                start_preview_server(root/'qa.html',root/'vocals.wav',root/'missing.wav')
