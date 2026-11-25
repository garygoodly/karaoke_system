from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fix_overlap', ROOT/'tools/fix_line_overlap_priority.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class OverlapPatchTests(unittest.TestCase):
    def test_install_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'lyrics_preview.py'
            p.write_text(mod.OLD,encoding='utf-8')
            self.assertEqual(mod.apply(p),'applied')
            self.assertIn(mod.NEW,p.read_text(encoding='utf-8'))
            self.assertEqual(mod.apply(p),'already_applied')
            self.assertEqual(p.with_suffix('.py.before_overlap_priority.bak').read_text(),mod.OLD)
    def test_unsupported_fails_without_changes(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'lyrics_preview.py';p.write_text('different')
            with self.assertRaises(RuntimeError):mod.apply(p)
            self.assertEqual(p.read_text(),'different')
    def test_overlap_selection_policy(self):
        lines=[{'id':7,'start':83.5,'end':91.52},{'id':8,'start':90.5,'end':97.52}]
        def select(t):
            eligible=[l for l in lines if l['start']<=t<=l['end']]
            return max(eligible,key=lambda l:l['start'])['id'] if eligible else None
        self.assertEqual(select(90.4),7)
        self.assertEqual(select(90.8),8)
        self.assertEqual(select(91.6),8)

if __name__=='__main__':unittest.main()
