from pathlib import Path
from unittest.mock import patch
import subprocess
from karaoke_phase0.mfa_g2p import generate_pronunciations, extend_dictionary


def test_g2p_output_parsed(tmp_path):
    def fake_run(cmd, **kwargs):
        assert cmd[1] == 'g2p'
        assert Path(cmd[2]).read_text(encoding='utf-8') == '泡沫\n'
        Path(cmd[4]).write_text('泡沫\tpʰ aw˥˩ m w o˥˩\n', encoding='utf-8')
        return subprocess.CompletedProcess(cmd, 0, '', '')
    with patch('karaoke_phase0.mfa_g2p.subprocess.run', side_effect=fake_run):
        assert generate_pronunciations(['泡沫'], 'mfa.exe')['泡沫'] == ('pʰ','aw˥˩','m','w','o˥˩')


def test_extend_compound_oov(tmp_path):
    base = tmp_path / 'base.dict'
    base.write_text('泡\t0.99\t0.25\t1.0\t1.0\tpʰ aw˥˩\n', encoding='utf-8')
    output = tmp_path / 'derived.dict'
    with patch('karaoke_phase0.mfa_g2p.generate_pronunciations', return_value={
        '泡沫': ('pʰ','aw˥˩','m','w','o˥˩'), '沫': ('m','w','o˥˩')
    }):
        report = extend_dictionary(base, output, ['泡沫'], 'mfa.exe', extra_oovs=['泡沫'])
    assert '泡沫' in report['added']
    assert '泡沫' in output.read_text(encoding='utf-8')
    assert '泡沫' not in base.read_text(encoding='utf-8')


def test_failure_does_not_write_dictionary(tmp_path):
    base = tmp_path / 'base.dict'
    base.write_text('泡 pʰ aw˥˩\n', encoding='utf-8')
    output = tmp_path / 'derived.dict'
    with patch('karaoke_phase0.mfa_g2p.subprocess.run', return_value=subprocess.CompletedProcess([],1,'','failed')):
        try:
            extend_dictionary(base, output, ['沫'], 'mfa.exe')
            assert False
        except RuntimeError:
            pass
    assert not output.exists()
