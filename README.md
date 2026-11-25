# Karaoke Phase 0 — Windows development

## Supported setup: uv

Use the project root (the directory containing `main.py` and `pyproject.toml`). The supported Python environment is `.venv-uv`. Do **not** install project packages into the `karaoke-mfa` Conda environment.

### New PC

1. Install uv: `winget install --id astral-sh.uv -e`.
2. Install FFmpeg: `winget install --id Gyan.FFmpeg -e`.
3. Open a fresh PowerShell in the project root and run `./setup_uv.bat` (or `./setup_uv.ps1`).
4. Launch the GUI: `./run_gui_uv.ps1`.

The setup uses `pyproject.toml` and the committed `uv.lock` to reproduce the Python dependencies, including CUDA-enabled PyTorch. A compatible NVIDIA GPU and driver are needed for the CUDA checks. See `README_UV.md` for detailed troubleshooting.

### Everyday commands

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python main.py gui
uv run --no-sync pytest -q
uv run --no-sync python -c "import sys,torch; print(sys.executable); print(torch.__version__,torch.cuda.is_available())"
```

**Environment check:** In PyCharm, set the project interpreter to `.venv-uv/Scripts/python.exe`. When using MFA, run `mfa` from the separate `karaoke-mfa` Conda environment. If PowerShell shows both `(karaoke-mfa)` and `(karaoke-phase0)`, verify `sys.executable` before installing packages.

## Project directories

- `src/karaoke_phase0/`: production application code (keep the `src` layout).
- `tools/`: developer-only diagnostics and converters.
- `tests/`: regression tests.
- `benchmarks/paomo/`: MFA vs WhisperX evaluation material; preserve original and custom TextGrid outputs.
- `songs/`: private, local song data and generated outputs; excluded from Git.

## Cleanup and migration

The legacy `setup_windows.bat`, `setup_windows.ps1`, and `requirements.txt` are **not** used by `setup_uv.bat`. Keep them until the uv setup and test suite are verified on your PC; then they can be removed in a separate cleanup commit. Do not delete `.venv/` until no workflow uses it. Never delete `songs/` or benchmark results as part of routine cleanup.

`main.py` still has CLI defaults referencing `samples/`, although the library-based workflow now uses `songs/`. Use the GUI or explicit `--song` / `--lyrics` arguments for those CLI commands until a separate compatibility patch fixes the defaults. Do not recreate `samples/` just to hide the issue.

### Git hygiene

Commit `pyproject.toml`, `uv.lock`, source, tests, documentation, and reusable benchmark metadata. Do not commit local environments or user songs. If a file was tracked before `.gitignore` changed, Git will continue tracking it until explicitly untracked; **do not run broad `git rm` commands on song or benchmark directories**.

## Validation before removing legacy setup

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv sync --locked
uv run --no-sync pytest -q
uv run --no-sync python -c "import torch,whisperx,demucs; assert torch.cuda.is_available(); print('CUDA OK')"
```

A successful unit test run does not by itself prove the complete Demucs + WhisperX + MFA workflow. Preserve the last working setup until the GUI and one real-song run are verified.
