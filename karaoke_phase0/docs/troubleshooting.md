# Troubleshooting quick reference

See [Windows installation](installation.md) for environment failures, [audio pipeline](audio_pipeline.md) for MFA/OOV alignment issues, and [pitch scoring](pitch_scoring.md) for detection and score diagnostics.

## Known Windows pitfall

MFA's Conda `Library\bin` may be required to load SoundFile, but adding it to the GUI process PATH can break FFmpeg DLL resolution. Keep MFA environment changes limited to the MFA subprocess.

## Diagnostics

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run --no-sync python -m pytest .\tests -q
```

The exact installation and model verification steps are in `setup_uv.ps1`.
