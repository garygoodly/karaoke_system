import importlib.util
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/'tools'/'integrate_lyrics_review_controls.py'
spec=importlib.util.spec_from_file_location('review_controls',MODULE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_add_and_idempotent(tmp_path):
    p=tmp_path/'lyrics_preview.py'
    p.write_text('<style></style>\nconst playback=()=>playerMode?instrumental:audio;\n</script>',encoding='utf-8')
    assert mod.apply(p)=='applied'
    s=p.read_text(encoding='utf-8')
    assert "addButton('-2s',-2)" in s and "addButton('+2s',2)" in s
    assert 'controls.appendChild(lyric)' in s
    assert mod.apply(p)=='already_applied'

def test_reject_unknown_template_without_change(tmp_path):
    p=tmp_path/'lyrics_preview.py';p.write_text('unknown',encoding='utf-8')
    try:mod.apply(p)
    except RuntimeError:pass
    else:assert False
    assert p.read_text(encoding='utf-8')=='unknown'
