import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.mfa_full_song import run_full_song


class ChineseOovRecoveryTests(unittest.TestCase):
    def test_unresolved_line_does_not_abort_other_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / 'song'
            gen = song / 'generated'
            gen.mkdir(parents=True)
            (song / 'lyrics.txt').write_text('陽光\n説甚麼你愛我\n泡沫\n', encoding='utf-8')
            with wave.open(str(gen / 'vocals.wav'), 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(1000)
                wav.writeframes(b'\x00\x00' * 6000)
            (gen / 'lyrics_timeline.json').write_text(json.dumps({
                'source_line_count': 3,
                'lines': [{'line_id': i, 'start': i + .2, 'end': i + .9} for i in range(3)]
            }), encoding='utf-8')
            calls = []
            def fake_scan(command, **kwargs):
                Path(command[-1]).mkdir(parents=True)
                return type('Result', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
            def fake_benchmark(corpus, output, *args, **kwargs):
                output.mkdir()
                calls.append(sorted(p.stem for p in corpus.glob('*.wav')))
                if len(calls) == 1:
                    (output / 'report.json').write_text(json.dumps({
                        'dictionary': {'unresolved': ['説甚麼你愛我']}
                    }), encoding='utf-8')
                    raise RuntimeError('Unresolved OOV: 説甚麼你愛我')
                for name in calls[-1]:
                    text = (corpus / (name + '.txt')).read_text(encoding='utf-8')
                    (output / (name + '_mfa_chars.json')).write_text(json.dumps({
                        'tokens': [{'text': c, 'start': i*.1, 'end': (i+1)*.1} for i,c in enumerate(text)],
                        'unresolved': []
                    }), encoding='utf-8')
                return {'dictionary': {'unresolved': []}, 'clips': {}}
            with patch('karaoke_phase0.mfa_full_song.subprocess.run', side_effect=fake_scan), \
                 patch('karaoke_phase0.mfa_full_song.run_benchmark', side_effect=fake_benchmark):
                result = run_full_song(song, gen / 'mfa' / 'test', 'dict', 'mfa', 'converter')
            self.assertEqual(result['processed_lines'], 2)
            self.assertEqual(result['failed_lines'], 1)
            self.assertIn('unresolved_pronunciation', result['lines'][1]['reason'])
            self.assertEqual(calls[1], ['line_000', 'line_002'])

if __name__ == '__main__':
    unittest.main()
