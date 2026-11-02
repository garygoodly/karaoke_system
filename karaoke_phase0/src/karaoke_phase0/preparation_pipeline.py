"""Resumable song preparation. No source audio or existing outputs are deleted."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STEPS = ('separation', 'alignment', 'reference_pitch')


def _valid(path):
    return path.is_file() and path.stat().st_size > 0


def _ready(folder, step):
    generated = folder / 'generated'
    if step == 'separation':
        return all(_valid(generated / name) for name in ('vocals.wav', 'instrumental.wav'))
    path = generated / ('lyrics_timeline.json' if step == 'alignment' else 'reference_pitch.json')
    if not _valid(path):
        return False
    try:
        obj = json.loads(path.read_text(encoding='utf-8'))
        return isinstance(obj, (dict, list)) and bool(obj)
    except (ValueError, UnicodeError, OSError):
        return False


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def prepare_song(folder, *, device='cpu', python=sys.executable, runner=None, on_progress=None):
    """Prepare a locally imported song, reusing validated outputs on reruns.

    runner(command) may be injected for tests. Failure is recorded and re-raised.
    Never overwrite valid artifacts, even if a previous checkpoint was lost.
    """
    folder = Path(folder).resolve()
    if device not in ('cpu', 'cuda'):
        raise ValueError('device must be cpu or cuda')
    if not _valid(folder / 'song.mp3'):
        raise FileNotFoundError(folder / 'song.mp3')
    if not any(_valid(folder / x) for x in ('lyrics.txt', 'lyrics.lrc')):
        raise FileNotFoundError('Missing lyrics.txt or lyrics.lrc')
    from .separation import demucs_command, publish_stems
    from .alignment_workflow import align_song
    from .reference_pitch import extract_reference
    report_path = folder / 'generated' / 'preparation_status.json'
    report = {'version': 1, 'device': device, 'steps': {}, 'status': 'running'}
    run = runner or (lambda cmd: subprocess.run(cmd, check=True))
    def update(step, status, detail=None):
        report['steps'][step] = {'status': status}
        if detail:
            report['steps'][step]['detail'] = str(detail)
        report['updated_at'] = datetime.now(timezone.utc).isoformat()
        _save(report_path, report)
        if on_progress:
            on_progress(step, status)
    for step in STEPS:
        if _ready(folder, step):
            update(step, 'skipped_existing')
            continue
        update(step, 'running')
        try:
            if step == 'separation':
                cmd = demucs_command(folder, python=python)
                cmd[cmd.index('-d') + 1] = device
                run(cmd)
                publish_stems(folder)
            elif step == 'alignment':
                align_song(folder, device=device)
            else:
                extract_reference(folder / 'generated' / 'vocals.wav',
                                  folder / 'generated' / 'reference_pitch.json', device=device)
            if not _ready(folder, step):
                raise RuntimeError(f'{step} did not produce a valid output')
            update(step, 'completed')
        except Exception as exc:
            update(step, 'failed', exc)
            report['status'] = 'review_required' if step == 'alignment' else 'failed'
            _save(report_path, report)
            raise
    report['status'] = 'ready'
    _save(report_path, report)
    return report
