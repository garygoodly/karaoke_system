import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from karaoke_phase0.alignment.shadow_mode import run_shadow,build_shadow_command

def test_missing_inputs(tmp_path):
    assert run_shadow(tmp_path)['status']=='skipped_missing_inputs'

def test_shadow_success_does_not_change_timeline(tmp_path):
    g=tmp_path/'generated';g.mkdir();(g/'vocals.wav').write_bytes(b'fake')
    timeline=g/'lyrics_timeline.json';timeline.write_text('{"lines":[]}',encoding='utf-8')
    before=timeline.read_bytes()
    def fake_runner(cmd,check):
        assert check
        Path(cmd[cmd.index('--output')+1]).write_text('{"consensus":[]}',encoding='utf-8')
    assert run_shadow(tmp_path,runner=fake_runner)['status']=='completed'
    assert timeline.read_bytes()==before

def test_shadow_failure_nonfatal(tmp_path):
    g=tmp_path/'generated';g.mkdir();(g/'vocals.wav').write_bytes(b'fake')
    (g/'lyrics_timeline.json').write_text('{}',encoding='utf-8')
    def fail(cmd,check): raise RuntimeError('no model')
    assert run_shadow(tmp_path,runner=fail)['status']=='failed'
    assert (g/'ctc_shadow_status.json').is_file()
