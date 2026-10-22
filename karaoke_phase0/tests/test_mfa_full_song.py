import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from karaoke_phase0.mfa_full_song import plan_lines, write_corpus, run_full_song


class FullSongTests(unittest.TestCase):
    def test_windows_and_missing_lines(self):
        lines=[{'text':'陽光'},{'text':'泡沫'},{'text':'彩色'}]
        timeline={'lines':[{'line_id':0,'start':1,'end':2},{'line_id':1,'start':3,'end':4}]}
        windows, errors=plan_lines(lines,timeline,10)
        self.assertEqual(set(windows),{0,1})
        self.assertEqual(errors[2],'missing_or_invalid_line_timing')
        self.assertLessEqual(windows[0][1],windows[1][0])

    def test_overlapping_clip_windows_are_allowed(self):
        lines = [{'text':'陽光'}, {'text':'泡沫'}, {'text':'彩色'}]
        timeline = {'lines': [
            {'line_id':0,'start':1.0,'end':3.0},
            {'line_id':1,'start':2.7,'end':4.0},
            {'line_id':2,'start':3.9,'end':5.0},
        ]}
        windows, errors = plan_lines(lines, timeline, 10)
        self.assertEqual(set(windows), {0,1,2})
        self.assertEqual(errors, {})
        self.assertGreater(windows[0][1], windows[1][0])

    def test_actual_token_overlap_is_warning_only(self):
        from karaoke_phase0.mfa_full_song import flag_token_overlaps
        lines = [
            {'line_id':0,'tokens':[{'text':'陽','start':1.0,'end':2.0}], 'warnings':[]},
            {'line_id':1,'tokens':[{'text':'光','start':1.9,'end':2.5}], 'warnings':[]},
            {'line_id':2,'tokens':[{'text':'泡','start':2.6,'end':3.0}], 'warnings':[]},
        ]
        flag_token_overlaps(lines)
        self.assertEqual(lines[0]['warnings'][0]['reason'],'overlapping_character_times')
        self.assertEqual(lines[1]['warnings'][0]['other_line_id'],0)
        self.assertEqual(lines[2]['warnings'],[])

    def test_overlapping_clip_windows_are_allowed(self):
        lines = [{'text':'陽光'}, {'text':'泡沫'}, {'text':'彩色'}]
        timeline = {'lines': [
            {'line_id':0,'start':1.0,'end':3.0},
            {'line_id':1,'start':2.7,'end':4.0},
            {'line_id':2,'start':3.9,'end':5.0},
        ]}
        windows, errors = plan_lines(lines, timeline, 10)
        self.assertEqual(set(windows), {0,1,2})
        self.assertEqual(errors, {})
        self.assertGreater(windows[0][1], windows[1][0])

    def test_actual_token_overlap_is_warning_only(self):
        from karaoke_phase0.mfa_full_song import flag_token_overlaps
        lines = [
            {'line_id':0,'tokens':[{'text':'陽','start':1.0,'end':2.0}], 'warnings':[]},
            {'line_id':1,'tokens':[{'text':'光','start':1.9,'end':2.5}], 'warnings':[]},
            {'line_id':2,'tokens':[{'text':'泡','start':2.6,'end':3.0}], 'warnings':[]},
        ]
        flag_token_overlaps(lines)
        self.assertEqual(lines[0]['warnings'][0]['reason'],'overlapping_character_times')
        self.assertEqual(lines[1]['warnings'][0]['other_line_id'],0)
        self.assertEqual(lines[2]['warnings'],[])

    def test_write_corpus_pcm(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); src=root/'vocals.wav'; corpus=root/'corpus';corpus.mkdir()
            with wave.open(str(src),'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(1000)
                wav.writeframes(b'\0\0'*3000)
            offsets=write_corpus(src,[{'text':'泡沫'}],{0:(1.0,2.0)},corpus)
            self.assertEqual(offsets['line_000'],1.0)
            with wave.open(str(corpus/'line_000.wav'),'rb') as wav:
                self.assertEqual(wav.getnframes(),1000)
            self.assertEqual((corpus/'line_000.txt').read_text(encoding='utf-8'),'泡沫')

    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);song=root/'song';gen=song/'generated';gen.mkdir(parents=True)
            (gen/'vocals.wav').write_bytes(b'dummy')
            (gen/'lyrics_timeline.json').write_text('{}')
            out=gen/'mfa';out.mkdir();(out/'keep').write_text('safe')
            with self.assertRaises(FileExistsError):
                run_full_song(song,out,'base.dict','mfa','converter.py')

    def test_end_to_end_with_mock_mfa(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);song=root/'song';gen=song/'generated';gen.mkdir(parents=True)
            (song/'lyrics.txt').write_text('陽光\n泡沫\n',encoding='utf-8')
            with wave.open(str(gen/'vocals.wav'),'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(1000)
                wav.writeframes(b'\0\0'*5000)
            (gen/'lyrics_timeline.json').write_text(json.dumps({'source_line_count':2,'lines':[
                {'line_id':0,'start':.5,'end':1.5},{'line_id':1,'start':2.5,'end':3.5}]}))
            def fake_run(corpus,output,*args,**kwargs):
                output.mkdir()
                for name in ('line_000','line_001'):
                    chars=list((corpus/(name+'.txt')).read_text(encoding='utf-8'))
                    data={'tokens':[{'text':c,'start':i*.2,'end':(i+1)*.2} for i,c in enumerate(chars)],'unresolved':[]}
                    (output/(name+'_mfa_chars.json')).write_text(json.dumps(data),encoding='utf-8')
                return {'dictionary':{'unresolved':[]}}
            def fake_scan(command, **kwargs):
                out=Path(command[-1]);out.mkdir(parents=True)
                (out/'oovs_found_mandarin.txt').write_text('泡沫\n',encoding='utf-8')
                return type('Completed',(),{'returncode':0,'stdout':'','stderr':''})()
            with patch('karaoke_phase0.mfa_full_song.subprocess.run',side_effect=fake_scan), \
                 patch('karaoke_phase0.mfa_full_song.run_benchmark',side_effect=fake_run) as benchmark:
                result=run_full_song(song,gen/'mfa'/'run1','dict','mfa','converter')
            self.assertIn('泡沫',benchmark.call_args.kwargs['extra_oovs'])
            self.assertEqual(result['processed_lines'],2)
            self.assertEqual(result['lines'][0]['tokens'][0]['text'],'陽')
            self.assertGreater(result['lines'][0]['tokens'][0]['start'],.3)
            self.assertEqual(json.loads((gen/'lyrics_timeline.json').read_text())['source_line_count'],2)
            self.assertTrue((gen/'mfa'/'run1'/'qa_report.json').exists())

if __name__=='__main__':unittest.main()
