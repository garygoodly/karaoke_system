# Windows song import rename retry

## Files
- MODIFY `src/karaoke_phase0/song_manager.py`
- ADD `tests/test_song_rename_retry.py`
- DELETE none

## Behavior
When staging a song import, retry directory rename up to five times **only** on Windows `WinError 5` or `WinError 32`, with delays of 0.1, 0.2, 0.3, 0.4 seconds. Never overwrite an existing destination; propagate persistent errors. The database INSERT occurs only after a successful rename. No changes to existing songs, databases, or MFA files.

## Install
Put ZIP in `patches/`, then run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_windows_rename_retry_patch.zip -RunTests
```

## Verification
Repeat song-manager tests if needed:

```powershell
1..20 | ForEach-Object { uv run --no-sync python -m pytest tests/test_song_manager.py -q; if ($LASTEXITCODE -ne 0) { break } }
```

This is mitigation for transient access-denied errors; the identity of the locking process has not been proven.
