"""Build a per-child Windows DLL search environment without changing os.environ."""
import os
from pathlib import Path


def mfa_subprocess_env(command, environ=None):
    """Return an isolated env for direct MFA executable calls, or None otherwise.

    A conda-run command already manages activation; it must not be altered.
    """
    if os.name != 'nt' or not command:
        return None
    exe = Path(str(command[0]))
    if exe.name.lower() not in ('mfa.exe', 'mfa-script.py'):
        return None
    # Direct executable is normally <env>/Scripts/mfa.exe.
    if exe.parent.name.lower() != 'scripts':
        return None
    prefix = exe.parent.parent
    library_bin = prefix / 'Library' / 'bin'
    if not library_bin.is_dir():
        return None
    child = dict(os.environ if environ is None else environ)
    current = child.get('PATH', '')
    entries = [p for p in current.split(os.pathsep) if p]
    required = [str(library_bin), str(prefix / 'Scripts'), str(prefix)]
    lowered = {os.path.normcase(os.path.normpath(p)) for p in required}
    entries = [p for p in entries if os.path.normcase(os.path.normpath(p)) not in lowered]
    child['PATH'] = os.pathsep.join(required + entries)
    return child


def run_mfa_command(command, **kwargs):
    """Run MFA in a child environment; never prepend Conda DLLs globally."""
    import subprocess
    if 'env' not in kwargs:
        isolated = mfa_subprocess_env(command)
        if isolated is not None:
            kwargs['env'] = isolated
    return subprocess.run(command, **kwargs)
