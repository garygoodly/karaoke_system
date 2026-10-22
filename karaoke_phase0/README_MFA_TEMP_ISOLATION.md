# MFA Temporary Directory Isolation Patch

## Changes
- MODIFY `src/karaoke_phase0/mfa_workflow.py`: pass a unique `output/mfa_temp` working directory to MFA with `--temporary_directory` and `--clean`.
- ADD `tests/test_mfa_temp_isolation.py`: verifies the MFA CLI arguments.
- ADD this README.
- DELETE none.

The patch does not modify the shared `Documents/MFA` cache, any song, or the original timeline.

## Install
Put the ZIP in `patches/`, then run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_mfa_temp_isolation_patch.zip -RunTests
```

## Full song (new run only)
```powershell
uv run --no-sync python .\tools\run_mfa_full_song.py --song-folder .\songs\song-3decb6500f5d --dictionary "$dict" --mfa-exe "$mfa" --output .\songs\song-3decb6500f5d\generated\mfa\full_song_run_07
```

Review the `qa_report.json` and the `mfa_run_retry_*/mfa.log`. A successful CLI invocation does not guarantee valid per-line TextGrid output.
