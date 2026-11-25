"""Idempotently fix overlapping line selection without replacing GUI files."""
from pathlib import Path
import argparse
import shutil

OLD = "const l=activeLines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);"
NEW = "const l=displayMode==='line' ? activeLines.filter(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end).reduce((best,x)=>!best||x.start>best.start?x:best,null) : activeLines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);"

def apply(path: Path):
    content = path.read_text(encoding='utf-8')
    if NEW in content:
        return 'already_applied'
    if content.count(OLD) != 1:
        raise RuntimeError('Unsupported lyrics_preview.py version: expected activeLines.find exactly once. No changes made.')
    updated = content.replace(OLD, NEW, 1)
    backup = path.with_suffix(path.suffix + '.before_overlap_priority.bak')
    if backup.exists():
        raise RuntimeError(f'Backup exists: {backup}. No changes made.')
    shutil.copy2(path, backup)
    try:
        path.write_text(updated, encoding='utf-8')
    except BaseException:
        shutil.copy2(backup, path)
        raise
    return 'applied'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--file', type=Path, default=Path(__file__).resolve().parents[1]/'src/karaoke_phase0/lyrics_preview.py')
    args=p.parse_args()
    print(apply(args.file))

if __name__=='__main__': main()
