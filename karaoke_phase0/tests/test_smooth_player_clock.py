import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fix_smooth_player_clock', ROOT / 'tools' / 'fix_smooth_player_clock.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture_source():
    # Minimal compatible GUI source; no dependency on developer-local files.
    return (
        "const stamp=(t)=>String(t);\n"
        "const clock=document.getElementById('playerClock');\n"
        + module.OLD + "\n"
        "setInterval(()=>{if(!instrumental.paused)sync()},250);\n"
    )


def test_patch_is_idempotent(tmp_path):
    source = fixture_source()
    path = tmp_path / 'lyrics_preview.py'
    path.write_text(source, encoding='utf-8')
    assert module.apply(path) == 'applied'
    updated = path.read_text(encoding='utf-8')
    assert 'setInterval(renderPlayerClock,33)' in updated
    assert "instrumental.addEventListener('timeupdate'" in updated
    assert 'clock.textContent=stamp(position)' in updated
    assert 'setInterval(()=>{if(!instrumental.paused)sync()},250)' in updated
    assert module.apply(path) == 'already_applied'
    assert path.with_suffix('.py.before_smooth_clock.bak').read_text(encoding='utf-8') == source


def test_unknown_template_safe(tmp_path):
    path = tmp_path / 'lyrics_preview.py'
    path.write_text('unknown', encoding='utf-8')
    with pytest.raises(RuntimeError):
        module.apply(path)
    assert path.read_text(encoding='utf-8') == 'unknown'
    assert not path.with_suffix('.py.before_smooth_clock.bak').exists()
