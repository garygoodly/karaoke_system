"""Idempotently add read-only boundary conflict diagnostics to hybrid_pipeline.py."""
from pathlib import Path
import ast
import shutil


def integrate(path):
    path = Path(path)
    source = path.read_text(encoding='utf-8')
    marker = "_write_atomic(generated / 'ctc_boundary_conflict_18_19.json', conflict)"
    if marker in source:
        return 'already_applied'
    anchor = "    _write_atomic(generated / 'ctc_context_fallback_diagnostics.json', context_report)"
    if source.count(anchor) != 1:
        raise ValueError('Expected context fallback insertion point not found exactly once; no files changed')
    addition = '''\n    # Diagnostic only: repeated lyric tokens and vocal RMS cannot authorize adoption.\n    from .boundary_conflict import diagnose_boundary\n    if len(timeline.get('lines', [])) > 19:\n        audio_path = generated / 'vocals.wav'\n        conflict = diagnose_boundary(shadow, timeline, previous_line_id=18,\n                                     audio_path=audio_path if audio_path.is_file() else None)\n        _write_atomic(generated / 'ctc_boundary_conflict_18_19.json', conflict)'''
    modified = source.replace(anchor, anchor + addition)
    ast.parse(modified)
    backup = path.with_suffix(path.suffix + '.before_boundary_conflict.bak')
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(modified, encoding='utf-8')
    return 'applied'


if __name__ == '__main__':
    target = Path('src/karaoke_phase0/alignment/hybrid_pipeline.py')
    print(integrate(target))
