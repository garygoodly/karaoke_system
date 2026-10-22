import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.mfa_workflow import run_benchmark

class WorkflowTests(unittest.TestCase):
    def test_missing_corpus(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                run_benchmark(Path(d)/'missing',Path(d)/'out',Path(d)/'missing.dict','mfa','converter.py')

    def test_no_pairs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'corpus').mkdir();(root/'base.dict').write_text('泡 p aw',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'No WAV/TXT'):
                run_benchmark(root/'corpus',root/'out',root/'base.dict','mfa','converter.py')
