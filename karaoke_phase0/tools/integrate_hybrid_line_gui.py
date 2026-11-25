"""Apply minimal, idempotent GUI edits to local files with atomic rollback.

The standard apply_patch.ps1 copies files; it cannot safely merge a full GUI
snapshot into a newer local GUI. Run this after installing the ZIP.
"""
from pathlib import Path
import ast
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / 'src/karaoke_phase0/gui.py'
PREVIEW = ROOT / 'src/karaoke_phase0/lyrics_preview.py'

PATCHES = {
    GUI: [
        ('from .alignment_workflow import read_timeline',
         'from .alignment_workflow import read_timeline\nfrom .line_timing_overlay import line_start_overrides'),
        ('            timeline = read_timeline(folder)',
         '            timeline = read_timeline(folder)\n            timeline = dict(timeline)\n            timeline["line_start_overrides"] = line_start_overrides(folder, timeline)'),
    ],
    PREVIEW: [
        ('const lines=DATA.lines||[],warnings=DATA.warnings||[];',
         """const lines=DATA.lines||[],warnings=DATA.warnings||[];
const lineStartOverrides=DATA.line_start_overrides||{};
const lineModeLines=lines.map(l=>{
  const override=lineStartOverrides[String(l.line_id)];
  return override!==null && override!==undefined && Number.isFinite(Number(override))
    ? {...l,start:Number(override)} : l;
});"""),
        ('const l=lines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);',
         """const activeLines=displayMode==='line'?lineModeLines:lines;
const l=activeLines.find(x=>Number.isFinite(x.start)&&Number.isFinite(x.end)&&t>=x.start&&t<=x.end);"""),
    ],
}

def build_changes(files):
    changes={}
    for path, replacements in PATCHES.items():
        content=files[path]
        for before, after in replacements:
            if after in content:
                continue
            if content.count(before)!=1:
                raise RuntimeError(f'Unsupported GUI version: expected one anchor in {path.name}: {before[:65]}')
            content=content.replace(before,after,1)
        if path.suffix=='.py':
            ast.parse(content)
        changes[path]=content
    return changes

def main():
    files={p:p.read_text(encoding='utf-8') for p in PATCHES}
    changes=build_changes(files)  # validate all before modifying anything
    changed=[p for p in PATCHES if changes[p]!=files[p]]
    if not changed:
        print('Already integrated; no changes needed.')
        return
    backups={p:p.with_suffix(p.suffix+'.before_line_overlay.bak') for p in changed}
    for p,b in backups.items():
        if b.exists():
            raise RuntimeError(f'Backup already exists; refusing overwrite: {b}')
    try:
        for p,b in backups.items():
            shutil.copy2(p,b)
        for p in changed:
            p.write_text(changes[p],encoding='utf-8')
    except BaseException:
        for p,b in backups.items():
            if b.exists():
                shutil.copy2(b,p)
        raise
    print('Integrated line-only overlay into: '+', '.join(p.name for p in changed))
    print('Backups retained: '+', '.join(str(b) for b in backups.values()))

if __name__=='__main__':
    main()
