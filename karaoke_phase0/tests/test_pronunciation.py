from pathlib import Path
import tempfile
import unittest
from karaoke_phase0.pronunciation import read_dictionary, segment, build_dictionary

class PronunciationTests(unittest.TestCase):
    def test_dictionary_and_segmentation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'base.dict'
            p.write_text('陽光\t0.99\t0.25\t1.0\t1.0\ty ang\n泡\t0.99\t0.25\t1.0\t1.0\tp aw\n', encoding='utf-8')
            lex = read_dictionary(p)
            self.assertEqual(segment('陽光泡沫', lex), ['陽光','泡','沫'])

    def test_unresolved_not_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            base, out = Path(d)/'base.dict', Path(d)/'out.dict'
            base.write_text('泡\t0.99\t0.25\t1.0\t1.0\tp aw\n', encoding='utf-8')
            report = build_dictionary(base, out, ['泡沫'])
            self.assertEqual(report['unresolved'], ['沫'])
            self.assertNotIn('沫\t', out.read_text(encoding='utf-8'))

    def test_verified_g2p(self):
        with tempfile.TemporaryDirectory() as d:
            base, out = Path(d)/'base.dict', Path(d)/'out.dict'
            base.write_text('泡\t0.99\t0.25\t1.0\t1.0\tp aw\n', encoding='utf-8')
            report = build_dictionary(base, out, ['泡沫'], g2p=lambda w: ['m','o'] if w=='沫' else None,
                                      valid_phones={'p','aw','m','o'})
            self.assertEqual(report['added'], ['沫'])
            self.assertEqual(report['unresolved'], [])
            self.assertIn('沫\t0.99', out.read_text(encoding='utf-8'))

if __name__ == '__main__': unittest.main()
