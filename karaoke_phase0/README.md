# Karaoke Studio — Windows setup and development

This is the **single setup README** for a new Windows PC. It replaces `README_UV.md`. Run commands in **PowerShell** unless stated otherwise.

## 0. What to copy from the old PC

- The latest project source (Git clone or a verified project ZIP), including `pyproject.toml`, `uv.lock`, `setup_uv.bat`, `setup_uv.ps1`, and `run_gui_uv.ps1`.
- Separately back up `songs/` (including `songs.db`, MP3, lyrics, and generated results). It is normally excluded from Git.
- Optionally keep `benchmarks/` and any custom pronunciation dictionaries. Large model caches and virtual environments can be downloaded/rebuilt.
- Do **not** copy `.venv-uv/`, `.venv/`, or Conda `envs/` between PCs.

## 1. Install Windows prerequisites (one time)

Open a normal PowerShell terminal:

```powershell
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
winget install --id astral-sh.uv -e --accept-package-agreements --accept-source-agreements
winget install --id CondaForge.Miniforge3 -e --accept-package-agreements --accept-source-agreements
winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements
```

Close and reopen PowerShell, then check:

```powershell
git --version
uv --version
ffmpeg -version
nvidia-smi
```

**GPU requirement:** A compatible NVIDIA GPU and driver are needed for CUDA inference. `nvidia-smi` should work before setting up PyTorch. A separate full CUDA Toolkit is generally not required for the CUDA-enabled PyTorch wheel used here. CPU-only machines will not pass the current `setup_uv.ps1` CUDA assertion.

If `uv` was installed but not found, restart the terminal first; then locate `uv.exe` under `$env:LOCALAPPDATA\Microsoft\WinGet\Packages` and fix PATH rather than reinstalling repeatedly.

## 2. Get the project and open its root

If the project is hosted in Git, substitute your **actual** repository URL:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\Desktop\Project\P0_Learning" | Out-Null
Set-Location "$env:USERPROFILE\Desktop\Project\P0_Learning"
git clone <YOUR_KARAOKE_REPOSITORY_URL> karaoke_system_windows_ready
```

Then change to the folder **containing `pyproject.toml`**. Depending on the repo structure, this might be:

```powershell
Set-Location .\karaoke_system_windows_ready\karaoke_phase0
```

If you used a ZIP instead, extract it and open the folder containing `pyproject.toml`; do not assume the ZIP's outer folder name matches the old PC.

Check:

```powershell
Test-Path .\pyproject.toml
Test-Path .\uv.lock
```

Both should return `True` for a reproducible install.

## 3. Install Karaoke's uv / CUDA environment

The project uses **Python 3.11**, **uv**, **PyTorch 2.8.0 CUDA 12.8**, **Demucs**, and **WhisperX**. Its virtual environment is `.venv-uv` (not the default `.venv`).

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
.\setup_uv.bat
```

The batch file invokes `setup_uv.ps1`, which checks FFmpeg, synchronizes dependencies using `uv.lock`, and verifies CUDA. If Windows warns about a downloaded script, inspect it before choosing Run once or using `Unblock-File`.

Verify explicitly:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python -c "import sys,torch,numpy,whisperx; print('Python:',sys.executable); print('Torch:',torch.__version__); print('NumPy:',numpy.__version__); print('CUDA:',torch.cuda.is_available()); print('GPU:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

Expected: the Python path is inside `.venv-uv` and `CUDA: True` on a supported NVIDIA GPU. **Do not install `torch` again with a generic pip command**; that can replace the CUDA build.

## 4. Install separate MFA environment (Chinese forced alignment)

MFA is **not installed into `.venv-uv`**. It runs in a separate Conda environment named `karaoke-mfa`.

Initialize Conda (this modifies the PowerShell profile):

```powershell
& "$env:LOCALAPPDATA\miniforge3\Scripts\conda.exe" init powershell
```

Close and reopen PowerShell. Then:

```powershell
conda create -n karaoke-mfa python=3.11 pip -y
conda install -n karaoke-mfa -c conda-forge montreal-forced-aligner=3.4.3 -y
```

Install the Chinese text-processing extras **using the MFA environment's exact interpreter**. This avoids the previously observed conflict where PyCharm activated `.venv-uv` at the same time as Conda:

```powershell
$mfaPython = "$env:LOCALAPPDATA\miniforge3\envs\karaoke-mfa\python.exe"
& $mfaPython -m pip install spacy-pkuseg dragonmapper hanziconv
& $mfaPython -c "import spacy_pkuseg,dragonmapper,hanziconv; print('Chinese tokenizer: OK')"
```

**Note:** Installing pip packages inside a Conda environment can change dependencies; keep this environment separate from the main Karaoke uv environment.

## 5. Download Mandarin MFA models

```powershell
$mfa = "$env:LOCALAPPDATA\miniforge3\envs\karaoke-mfa\Scripts\mfa.exe"
& $mfa model download acoustic mandarin_mfa --version v3.0.0
& $mfa model download dictionary mandarin_taiwan_mfa --version v3.0.0
& $mfa model download g2p mandarin_taiwan_mfa --version v3.0.0
```

Check:

```powershell
& $mfa version
& $mfa model list acoustic
& $mfa model list dictionary
& $mfa model list g2p
```

Expected MFA version: `3.4.3`; each list should include the model just downloaded. The models are kept in MFA's user model directory, not in the project's Python environment.

## 6. Restore songs and run tests

Restore your backed-up `songs/` directory to the **project root**, preserving `songs.db`, each song folder, original lyrics, and generated results. Do not overwrite existing data without checking which copy is newer.

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run --no-sync python -m pytest -q
```

The last verified baseline before full-song integration was **41 passing tests**; the later full-song patch adds tests. The actual number depends on the project revision. Any failing test should be investigated rather than assuming a fixed count.

Start the GUI:

```powershell
.\run_gui_uv.ps1
```

PyCharm interpreter: `<project-root>\.venv-uv\Scripts\python.exe`. Avoid simultaneously activating the uv environment and Conda MFA in the same terminal; call MFA by its full executable path when needed.

## 7. Full-song MFA CLI (if the integration patch is installed)

Run from the project root; adjust the song ID if needed:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
$env:PYTHONPATH = (Resolve-Path .\src).Path
$dict = "$env:USERPROFILE\Documents\MFA\pretrained_models\dictionary\mandarin_taiwan_mfa.dict"
$mfa = "$env:LOCALAPPDATA\miniforge3\envs\karaoke-mfa\Scripts\mfa.exe"
uv run --no-sync python .\tools\run_mfa_full_song.py --song-folder .\songs\song-3decb6500f5d --dictionary "$dict" --mfa-exe "$mfa"
```

This workflow is experimental. Its outputs belong under `songs/<song_id>/generated/mfa/` and **must not overwrite** the existing `lyrics_timeline.json` until the timing QA is validated.

## 8. Apply future patch ZIPs

If `apply_patch.ps1` is installed at the project root, put a trusted patch ZIP in `patches/` and run:

```powershell
.\apply_patch.ps1 .\patches\PATCH_FILENAME.zip -RunTests
```

Review the file list and confirm `APPLY` only after checking the patch's README. Keep `patches/` and `backups/` out of Git. The installer backs up overwritten files; a failed test does **not** automatically roll back the patch.

## 9. Troubleshooting

| Symptom | Check / fix |
|---|---|
| `uv` / `conda` / `ffmpeg` not recognized | Restart terminal; check the executable's actual location and PATH. |
| `CUDA: False` | Run `nvidia-smi`; confirm `.venv-uv` Python and CUDA PyTorch wheel. |
| `No module named karaoke_phase0` | Run from project root; set `$env:PYTHONPATH = (Resolve-Path .\src).Path`. |
| `(karaoke-mfa) (karaoke-phase0)` both displayed | Two environments may be active; use explicit MFA and uv interpreter paths. |
| MFA Chinese tokenizer ImportError | Install `spacy-pkuseg dragonmapper hanziconv` into `karaoke-mfa` Python. |
| MFA reports OOV / `spn` | Check G2P and dictionary extension; do not edit downloaded pretrained dictionaries in place. |
| Windows `WinError 32` on `songs.db` | Confirm latest `song_manager.py` uses explicit SQLite connection closing. |

## 10. Git and cleanup rules

**Commit:** source code, tests, setup scripts, `pyproject.toml`, `uv.lock`, and this README.

**Keep local / exclude from Git:** `.venv-uv/`, `.venv/`, `songs/`, `patches/`, `backups/`, Python caches, large generated audio, and disposable MFA run outputs. Preserve important Benchmark references separately if they are not in Git.

`README_UV.md` may be removed **after this README is committed and verified**. Old `setup_windows.bat`, `setup_windows.ps1`, and `requirements.txt` should only be deleted after checking they are no longer referenced. Never delete user songs or `songs.db` as part of environment cleanup.
