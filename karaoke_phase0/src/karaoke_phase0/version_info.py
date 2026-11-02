"""Local build identity for troubleshooting cross-PC mismatches."""
from pathlib import Path
import subprocess


def git_version(project_root=None):
    root = Path(project_root or Path(__file__).resolve().parents[2])
    try:
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', '--short=8', 'HEAD'],
                                capture_output=True, text=True, timeout=3, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return 'unknown (Git metadata unavailable)'
