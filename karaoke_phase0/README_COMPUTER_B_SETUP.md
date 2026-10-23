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
