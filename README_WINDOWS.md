# Windows Quick Start

This project now includes **Windows-first setup and launcher scripts**.

## What works with the Windows scripts

Base install:
- create a `.venv`
- install Python packages from `requirements-windows.txt`
- run environment diagnostics
- launch the player
- preprocess a song from PowerShell or batch wrappers

Optional install:
- install `FFmpeg` with `winget`
- install optional Python packages like `aubio` and `demucs`

## Recommended flow

### 1. Open PowerShell in the repo root

### 2. Run install

```powershell
.\scripts\windows\install_windows.ps1 -InstallFFmpeg
```

If you want optional Python packages too:

```powershell
.\scripts\windows\install_windows.ps1 -InstallFFmpeg -InstallOptionalPythonPackages
```

### 3. Verify the environment

```powershell
.\scripts\windows\doctor_windows.ps1
```

### 4. Launch the player

```powershell
.\scripts\windows\start_player.ps1 -SongDir .\songs\my_song
```

## One-click batch wrappers

You can also double-click these:

- `scripts\windows\install_windows.bat`
- `scripts\windows\doctor_windows.bat`
- `scripts\windows\start_player.bat`
- `scripts\windows\preprocess_song.bat`

## Notes

- `FFmpeg` is needed for preprocessing and for generating playback cache files.
- **Key shift** needs FFmpeg with the `rubberband` audio filter enabled.
- If `aubio` is missing, live microphone pitch still works through a built-in NumPy fallback.
- `WhisperX`, `MFA`, and `SpeexDSP` stay optional and are not installed automatically by the Windows base installer.
