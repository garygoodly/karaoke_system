import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from karaoke_phase0.mfa_full_song import run_full_song, unsupported_language_lines


class MixedLanguageRecoveryTests(unittest.TestCase):
    def test_classification(self):
        lines = [{'text':'陽光下的泡沫'}, {'text':'為甚麼難過? Oh-oh'},
                 {'text':'OH OH'}, {'text':'基於你還愛我'}]
        errors = unsupported_language_lines(lines)
        self.assertEqual(set(errors), {1, 2})
        self.assertIn('Oh-oh', errors[1])

    def test_skips_mixed_line_but_keeps_qa(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); song=root/'song'; gen=song/'generated'; gen.mkdir(parents=True)
            (song/'lyrics.txt').write_text('陽光\n為甚麼難過? Oh-oh\n泡沫\n',encoding='utf-8')
            with wave.open(str(gen/'vocals.wav'),'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(1000)
                w.writeframes(b'\0\0'*6000)
            baseline={'source_line_count':3,'lines':[
                {'line_id':i,'start':i*1.5+.2,'end':i*1.5+1.2} for i in range(3)]}
            (gen/'lyrics_timeline.json').write_text(json.dumps(baseline))
            def fake_scan(cmd,**kw):
                Path(cmd[-1]).mkdir(parents=True)
                return type('Result',(),{'returncode':0,'stdout':'','stderr':''})()
            def fake_benchmark(corpus, output, *args, **kw):
                output.mkdir()
                names=sorted(p.stem for p in corpus.glob('*.wav'))
                self.assertEqual(names,['line_000','line_002'])
                for name in names:
                    txt=(corpus/(name+'.txt')).read_text(encoding='utf-8')
                    (output/(name+'_mfa_chars.json')).write_text(json.dumps({
                        'tokens':[{'text':c,'start':i*.1,'end':(i+1)*.1} for i,c in enumerate(txt)],
                        'unresolved':[]}),encoding='utf-8')
                return {'dictionary':{'unresolved':[]}}
            with patch('karaoke_phase0.mfa_full_song.subprocess.run',side_effect=fake_scan),\
                 patch('karaoke_phase0.mfa_full_song.run_benchmark',side_effect=fake_benchmark):
                report=run_full_song(song,gen/'mfa'/'test','dict','mfa','converter')
            self.assertEqual(report['processed_lines'],2)
            self.assertEqual(report['failed_lines'],1)
            self.assertEqual(report['skipped_unsupported_language_lines'],[1])
            self.assertEqual(report['lines'][1]['tokens'],[])
            self.assertIn('unsupported_language',report['lines'][1]['reason'])
            self.assertEqual(report['status'],'review_required')
            self.assertEqual(json.loads((gen/'mfa'/'test'/'qa_report.json').read_text())['failed_line_ids'],[1])
            self.assertEqual(json.loads((gen/'lyrics_timeline.json').read_text()),baseline)

if __name__=='__main__': unittest.main()
