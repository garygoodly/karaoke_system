# Karaoke Studio

Windows karaoke application with song preparation, lyric display, microphone pitch tracking, and experimental singing scores.

## Quick start (Windows)

1. Install Git and make sure WinGet and an internet connection are available.
2. Clone the repository and run the setup script from the project folder:

```powershell
git clone https://github.com/garygoodly/karaoke_system.git
cd .\karaoke_system\karaoke_phase0
.\setup_uv.bat
.\run_gui_uv.ps1
```

Setup can download dependencies and MFA models; it may need user consent or a terminal restart. It does not guarantee all hardware or model workflows work on every Windows PC. See [installation](docs/installation.md).

## Use

Import your own audio and lyrics, select **Prepare Song / Retry**, then open **Karaoke Player**. Generated song data is local and should not be committed to Git. Pitch and note scoring remain experimental.

## Documentation

- [Windows setup and CI](docs/installation.md)
- [Architecture and workflow](docs/architecture.md)
- [Audio alignment and MFA](docs/audio_pipeline.md)
- [Pitch detection and scoring](docs/pitch_scoring.md)
- [Troubleshooting](docs/troubleshooting.md)

## Development

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run --no-sync python -m pytest .\tests -q
```

GitHub Actions provides a Windows clean-install smoke test, but actual GPU inference, microphone access and end-to-end song preparation require separate validation.
