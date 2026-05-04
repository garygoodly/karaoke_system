from __future__ import annotations

from pathlib import Path
import shutil


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def copy_file(src: str | Path, dst: str | Path) -> Path:
    source = Path(src)
    target = Path(dst)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def relpath(target: str | Path, base: str | Path) -> str:
    return str(Path(target).resolve().relative_to(Path(base).resolve()))
