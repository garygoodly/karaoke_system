# Live torchcrepe detector (experimental)

This patch adds a selectable neural pitch backend while retaining YIN as default.

## Install

```powershell
.\apply_patch.ps1 .\patches\karaoke_live_torchcrepe_patch.zip -RunTests
uv pip install --python .\.venv-uv\Scripts\python.exe torchcrepe websockets
```

## Start local pitch service (second PowerShell terminal)

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu
```

Then launch the GUI, enable microphone, and select **torchcrepe (local Python)** from the Detector dropdown. YIN remains available without a backend. The backend listens only on 127.0.0.1:8766 and receives raw microphone snapshots. It does not save recordings. Stop it with Ctrl+C.

## Limitations

- Prototype transports overlapping analyser snapshots via WebSocket, not an AudioWorklet stream. CPU inference may lag or skip samples. For production, use an AudioWorklet with a ring buffer, sample-rate conversion and timestamps.
- Mic level sensitivity slider currently applies to YIN only. Torchcrepe uses `--min-rms` and `--min-periodicity` CLI flags.
- First torchcrepe inference may be slow. Latency and vowel robustness must be measured on the target Windows PC.
- Local WebSocket has no authentication. Use only on a trusted machine; do not expose the port outside loopback.
