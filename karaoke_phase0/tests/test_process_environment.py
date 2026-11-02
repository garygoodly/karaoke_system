from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.process_environment import mfa_subprocess_env


def test_direct_mfa_gets_isolated_path(tmp_path):
    prefix = tmp_path / 'karaoke-mfa'
    (prefix / 'Library' / 'bin').mkdir(parents=True)
    (prefix / 'Scripts').mkdir()
    cmd = [str(prefix / 'Scripts' / 'mfa.exe'), 'version']
    with patch('karaoke_phase0.process_environment.os.name', 'nt'):
        child = mfa_subprocess_env(cmd, {'PATH': 'C:/ffmpeg'})
    assert child['PATH'].startswith(str(prefix / 'Library' / 'bin'))
    assert 'C:/ffmpeg' in child['PATH']
    assert mfa_subprocess_env(['ffmpeg', '-version']) is None
