import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.mfa_workflow import run_benchmark


def test_missing_textgrid_is_reported_not_fatal():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        corpus = root / 'corpus'; corpus.mkdir()
        (corpus / 'line_020.wav').write_bytes(b'fake')
        (corpus / 'line_020.txt').write_text('測試', encoding='utf-8')
        (root / 'base.dict').write_text('測試  t', encoding='utf-8')
        (root / 'converter.py').write_text('', encoding='utf-8')
        with patch('karaoke_phase0.mfa_workflow.extend_dictionary', return_value={'unresolved': []}), \
             patch('karaoke_phase0.mfa_workflow.subprocess.run') as proc:
            proc.return_value.returncode = 0
            proc.return_value.stdout = ''
            proc.return_value.stderr = ''
            result = run_benchmark(corpus, root/'out', root/'base.dict', 'mfa', root/'converter.py')
        assert result['failed_clips'] == ['line_020']
        assert result['clips']['line_020']['reason'] == 'missing_textgrid'
        assert json.loads((root/'out'/'report.json').read_text())['failed_clips'] == ['line_020']
