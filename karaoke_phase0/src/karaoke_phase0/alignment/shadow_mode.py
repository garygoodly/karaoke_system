"""Opt-in CTC shadow runner. Never writes the authoritative lyrics timeline."""
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = 'wbbbbb/wav2vec2-large-chinese-zh-cn'

def shadow_paths(song):
    generated = Path(song) / 'generated'
    return generated / 'vocals.wav', generated / 'lyrics_timeline.json', generated / 'ctc_shadow_diagnostics.json'

def build_shadow_command(song, *, python=sys.executable, model=DEFAULT_MODEL, device='cuda', benchmark=None):
    audio, timeline, output = shadow_paths(song)
    benchmark = Path(benchmark) if benchmark else Path(__file__).resolve().parents[3] / 'tools' / 'benchmark_ctc_sliding_v4.py'
    return [str(python), str(benchmark), '--audio', str(audio), '--timeline', str(timeline),
            '--model', model, '--device', device, '--group-size', '3', '--output', str(output)]

def run_shadow(song, *, python=sys.executable, model=DEFAULT_MODEL, device='cuda', benchmark=None, runner=None):
    """Execute shadow benchmark after existing preparation. On failure, record it; never fail preparation."""
    audio, timeline, output = shadow_paths(song)
    if not audio.is_file() or not timeline.is_file():
        return {'status': 'skipped_missing_inputs', 'output': str(output)}
    command = build_shadow_command(song, python=python, model=model, device=device, benchmark=benchmark)
    try:
        result = (runner or subprocess.run)(command, check=True)
        if not output.is_file():
            raise RuntimeError('Benchmark returned without producing diagnostics')
        obj = json.loads(output.read_text(encoding='utf-8'))
        if not isinstance(obj, dict) or 'consensus' not in obj:
            raise ValueError('Invalid shadow report')
        return {'status': 'completed', 'output': str(output)}
    except Exception as exc:
        # Do not overwrite existing valid diagnostics on error.
        failure = output.with_name('ctc_shadow_status.json')
        failure.parent.mkdir(parents=True,exist_ok=True)
        failure.write_text(json.dumps({'status':'failed', 'reason':str(exc)},indent=2),encoding='utf-8')
        return {'status': 'failed', 'reason':str(exc), 'output':str(output)}
