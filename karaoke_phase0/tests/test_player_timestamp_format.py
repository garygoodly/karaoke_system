import importlib.util
from pathlib import Path
import pytest

SCRIPT=Path(__file__).resolve().parents[1]/'tools'/'fix_player_timestamp_format.py'
spec=importlib.util.spec_from_file_location('timestamp_fix',SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    return ('<span id="playerClock">0:00</span>\n'+mod.OLD_STAMP+'\n'
            "clock.textContent=stamp(instrumental.currentTime)+' / '+stamp(instrumental.duration||0);\n"
            +mod.OLD_JUMP+'\n'+mod.OLD_SONG_TIME)

def test_patch_and_idempotence(tmp_path):
    p=tmp_path/'lyrics_preview.py';p.write_text(fixture(),encoding='utf-8')
    assert mod.apply(p)=='applied'
    assert mod.apply(p)=='already_applied'
    s=p.read_text(encoding='utf-8')
    assert mod.NEW_STAMP in s and mod.NEW_JUMP in s and mod.NEW_SONG_TIME in s
    assert '0:00.00' in s
    assert p.with_suffix('.py.before_timestamp_format.bak').read_text(encoding='utf-8')==fixture()

def test_unknown_layout_does_not_write(tmp_path):
    p=tmp_path/'lyrics_preview.py';p.write_text('unexpected',encoding='utf-8')
    with pytest.raises(RuntimeError):mod.apply(p)
    assert p.read_text(encoding='utf-8')=='unexpected'
