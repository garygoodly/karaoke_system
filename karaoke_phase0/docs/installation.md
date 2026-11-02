# Windows installation and CI

## Quick install

Prerequisites: Windows, Git, internet access and working WinGet. Clone the repository and run setup from `karaoke_phase0`:

```powershell
git clone https://github.com/garygoodly/karaoke_system.git
cd .\karaoke_system\karaoke_phase0
.\setup_uv.bat
.\run_gui_uv.ps1
```

`setup_uv.bat` calls `setup_uv.ps1`, which sets up the uv Python 3.11 environment, checks FFmpeg, and configures a separate Conda MFA environment. Some tools require a terminal restart after installation. The current lockfile includes CUDA 12.8 wheels even on CPU-only systems; CPU inference may be possible but true CPU-only installation has not been qualified.

**Windows MFA DLL isolation:** Launch MFA with `conda run -n karaoke-mfa mfa ...`, or set `Library\bin` in the environment of only the MFA subprocess. Do not prepend MFA DLL directories to the parent GUI/FFmpeg process PATH.

**Validation:** GitHub Actions Windows clean-install and pytest smoke tests have passed in the reported run. They do not prove GPU inference, actual microphone behavior, model downloads in all modes, or end-to-end song processing.

## Troubleshooting priorities

- `uv` not found after WinGet: fully restart the terminal or IDE; inspect PATH.
- `soundfile` / `libsndfile.dll` error: verify MFA through `conda run`; do not rename `sndfile.dll`.
- FFmpeg exit failure after MFA PATH changes: restart with a clean PATH and isolate MFA subprocess environment.
- Python import error in tests: set `PYTHONPATH=src` and run pytest against `tests/`.

## Archived patch notes (verbatim from supplied ZIP snapshot)

The following historical notes are preserved for technical context. They may contain superseded setup commands; use the current project scripts as the authority.

---

### Historical source: README_WINDOWS_ONE_CLICK.md

# Karaoke Windows one-command setup

From a fresh Windows computer, clone/pull the Git repository and run **`setup_uv.bat` from the `karaoke_phase0` folder**. The batch file invokes `setup_uv.ps1` to install/check uv, FFmpeg, the locked Python 3.11 environment, Miniforge/MFA 3.4.3, Chinese tokenizer packages, and Mandarin acoustic/dictionary/G2P models.

## Requirements

- Windows PowerShell 5.1+, working `winget`, internet access, Git repository already cloned. Some installations may require user consent, restart of the terminal, or administrator permissions.
- The project must contain `pyproject.toml` and committed `uv.lock` including torchcrepe and websockets.
- Model downloads are large and depend on external servers. They may fail due to network access.
- Current lockfile installs CUDA 12.8 PyTorch wheels, even on CPU-only computers. CUDA inference also requires a compatible NVIDIA driver. The script uses CPU when CUDA is unavailable but cannot guarantee every CUDA wheel works on all Windows configurations.
- **No automatic deletion** of `.venv-uv`, `songs/`, or existing `karaoke-mfa` environments. The script may install/update dependencies via `uv sync`, and pip-install tokenizer packages inside MFA if missing.

## Run

```powershell
cd D:\Git\karaoke_system\karaoke_phase0
.\setup_uv.bat
```

If a WinGet installation succeeds but the command is not yet visible, close the **entire** Terminal/IDE and run the batch file again. The setup is restartable. It searches common user Miniforge directories and WinGet uv locations instead of assuming `%LOCALAPPDATA%\miniforge3`.

The MFA checks **always use `conda run -n karaoke-mfa mfa ...`**, not the raw `mfa.exe`, to ensure Windows DLL lookup is initialized. The script verifies `soundfile` and `mfa version` *before* model downloads.

## Options

```powershell
.\setup_uv.bat -SkipMfaModels
.\setup_uv.bat -SkipMfa
.\setup_uv.bat -SkipFFmpegCheck
```

Options are for debugging/partial setup only. Default is full setup. Models can be downloaded later by rerunning default setup.

## Verify and launch

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python -m pytest -q
.\run_gui_uv.ps1
```

For real-time torchcrepe, in another PowerShell terminal:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu
```

## What setup cannot do

It cannot transfer copyrighted song files from another PC or create them from Git. Download/import your own MP3/WAV and lyrics on each computer; use GUI `Prepare Song / Retry` to generate per-song analysis outputs. A first full song processing run can take substantial time and may require model downloads. MFA full-song alignment is optional for the current Line Mode pipeline.

If `conda run` passes but direct `mfa.exe` fails with `libsndfile.dll` error `0x7e`, **do not rename `sndfile.dll`**. Use `conda run`. Other tools invoking raw MFA executable must be updated separately to use Conda activation.

## Validation scope

Script syntax and patch contents can be inspected without Windows; **full clean-install verification requires a separate Windows machine**. A passing setup only proves dependency imports and MFA startup, not that every AI model or song workflow succeeds. Run the GUI and a fresh song preparation as final end-to-end checks.


---

### Historical source: README_COMPUTER_B_SETUP.md

# Computer B - clean Windows installation

This document supplements the existing README. Computer B downloads its own legally available song audio and lyrics. **Do not commit songs, model caches, virtual environments, or exported song ZIPs to Git.**

## 1. Prerequisites

Open PowerShell and install Git, Python 3.11, uv, FFmpeg and Miniforge (for optional MFA):

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.11 -e
winget install --id astral-sh.uv -e
winget install --id Gyan.FFmpeg -e
winget install --id CondaForge.Miniforge3 -e
```

Reopen PowerShell; verify `git --version`, `uv --version`, `ffmpeg -version`, and `ffprobe -version`. No NVIDIA GPU is required for basic playback or CPU inference.

## 2. Clone and install

Clone your actual repository, then navigate to the directory containing `pyproject.toml`, `uv.lock`, and `setup_uv.ps1`.

```powershell
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_REPOSITORY_FOLDER>\karaoke_phase0
.\setup_uv.ps1
```

If the repository has a different layout, use the actual directory containing `pyproject.toml`. The script uses the **committed** `uv.lock` and checks `torchcrepe` and `websockets`. This lock currently references **CUDA 12.8 PyTorch wheels**. These may run CPU inference without an NVIDIA GPU, but are large downloads; a genuine CPU-only lock is **not** implemented by this patch. If package installation fails on a CPU-only PC, stop and record the first error rather than modifying the lock ad hoc.

## 3. Run the GUI and live pitch

Start the local pitch service in one PowerShell window:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu
```

Leave it running. In another window:

```powershell
.\run_gui_uv.ps1
```

Choose a song and enable microphone permission in the player. CUDA acceleration is optional: use `--device cuda` only after confirming `torch.cuda.is_available()` is true.

## 4. Prepare songs locally

Computer B must obtain its own audio and lyrics. Import audio/lyrics through the GUI. For advanced forced alignment, follow the **existing README MFA/Conda section**, install the Mandarin models/dictionary there, and run the existing song-processing commands. Do not assume one-click song preparation is implemented; some processing remains manual. If using a WAV source and the import UI requires MP3, convert with FFmpeg first.

The following generated data may be needed for full player functionality: separated instrumental/vocals, lyrics timeline, and `generated/reference_pitch.json`. A Git pull alone cannot create them.

## 5. Verify

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python -m pytest -q
uv run --no-sync python -c "import torch,torchcrepe,websockets; print(torch.__version__, torch.cuda.is_available())"
```

Full end-to-end clean-install validation must be performed on Computer B when available. Do not assume Windows execution or MFA configuration has been verified by this patch alone.


---

### Historical source: README_WINDOWS_CI.md

# Windows clean-install CI

This patch addresses the Windows PowerShell 5.1 `NativeCommandError` raised by an optional Conda import check, even when `mfa version` prints 3.4.3. The optional check now uses the native process exit code and does not redirect stderr. Genuine nonzero exit codes still fail required steps.

## Install

1. Put `karaoke_windows_ci_setup_fix.zip` in `karaoke_phase0/patches/`.
2. Run `./apply_patch.ps1 ./patches/karaoke_windows_ci_setup_fix.zip -RunTests` from PowerShell.
3. Extract the **separate** `karaoke_windows_ci_workflow.zip` into the Git repository root (parent of `karaoke_phase0`). This is separate because the patch installer intentionally rejects `.github/` paths.
4. Commit `karaoke_phase0/setup_uv.ps1` and `.github/workflows/windows-clean-install.yml` and push.

## What CI validates

- Fresh Windows hosted runner with uv and Miniforge
- Locked project Python packages (including CUDA 12.8 PyTorch wheels, with CPU inference when GPU absent)
- MFA Conda environment and `soundfile`/DLL loading via `conda run`
- Mandarin tokenizer imports
- pytest regression suite

By default, MFA model downloads are skipped to keep normal CI reasonably fast. In GitHub Actions, manually run **Windows clean install** with `download_mfa_models=true` for the full network/model installation test.

## Limitations

- GitHub-hosted Windows runners do not validate NVIDIA CUDA inference, actual microphones, GUI rendering, or GPU VRAM constraints.
- Third-party download/network availability can still fail independently of the setup code.
- The workflow assumes the repository contains `karaoke_phase0/` at its root. If the Git layout differs, adjust `working-directory` and path filters.
- This patch fixes the stderr issue observed on Computer A, but has not yet run on a fresh Windows runner.
- For real end-to-end coverage, add a separate integration test using a licensed short audio fixture after the installer passes.
