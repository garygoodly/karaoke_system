import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from karaoke_phase0.lyrics_qa_server import start_preview_server
from karaoke_phase0.lyrics_preview import render


class TestLyricsQA(unittest.TestCase):
    def test_preview_and_allowlisted_audio(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            page = render({'lines':[{'line_id': 0,'text':'測試','start':1.,'end':2.,'tokens':[]}],
                           'warnings':[{'line_id':0,'reason':'review'}], 'status':'review_required'}, root/'lyrics_qa.html')
            vocals = root/'vocals.wav'
            vocals.write_bytes(b'RIFF' + bytes(range(100)))
            server, url = start_preview_server(page, vocals)
            try:
                with urlopen(url) as response:
                    html = response.read().decode('utf-8')
                    self.assertIn('src="/vocals.wav"', html)
                    self.assertIn('similarity', html)
                    self.assertNotIn('type="file"', html)
                req = Request(url+'vocals.wav', headers={'Range':'bytes=4-9'})
                with urlopen(req) as response:
                    self.assertEqual(response.status,206)
                    self.assertEqual(response.read(),bytes(range(6)))
                with self.assertRaises(HTTPError) as ctx:
                    urlopen(url+'../secret')
                self.assertEqual(ctx.exception.code,404)
            finally:
                server.shutdown()
                server.server_close()

    def test_missing_audio(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'page.html').write_text('hi')
            with self.assertRaises(FileNotFoundError):
                start_preview_server(root/'page.html', root/'vocals.wav')

if __name__ == '__main__':
    unittest.main()
