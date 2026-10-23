import tempfile
import unittest
from pathlib import Path
from karaoke_phase0.lyrics_preview import render


class MicrophonePlayerTests(unittest.TestCase):
    def test_microphone_controls_in_player_mode(self):
        with tempfile.TemporaryDirectory() as d:
            page = Path(d) / 'qa.html'
            render({'lines': [], 'warnings': [], 'status': 'review_required'}, page, player_mode=True)
            html = page.read_text(encoding='utf-8')
            for marker in ('id="microphonePanel"', 'id="micDevice"', 'id="micLevel"',
                           'id="micGain"', 'id="micMute"', 'id="micMonitor"',
                           'getUserMedia', 'getFloatTimeDomainData', 'getAudioTracks',
                           'micMonitor.checked?1:0', 'pagehide'):
                self.assertIn(marker, html)

    def test_legacy_qa_keeps_microphone_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            page = Path(d) / 'qa.html'
            render({'lines': [], 'warnings': [], 'status': 'review_required'}, page)
            html = page.read_text(encoding='utf-8')
            self.assertIn('id="microphonePanel" class="mic-panel" hidden', html)
            self.assertIn('if(playerMode){listMicrophones()', html)


if __name__ == '__main__':
    unittest.main()
