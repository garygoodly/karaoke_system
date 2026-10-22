# MFA Missing TextGrid Recovery + Patch Installer

## Changes
- `mfa_workflow.py`: a missing TextGrid for one clip is reported as `missing_textgrid`, not raised as a fatal exception. Nonzero MFA process exit remains fatal; check `mfa.log`.
- `mfa_full_song.py`: missing clip outputs are preserved as failed lines in `qa_report.json`, with empty tokens. Song remains `review_required`.
- `apply_patch.ps1`: no APPLY prompt. Temporary rollback copies are removed at the end. Git tracked dirty state and existing untracked target files block the patch unless `-Force` is explicitly used.

## Important
This is fault isolation, not a fix for the underlying missing TextGrid. Inspect `mfa_run/mfa.log` and the affected line's transcript after the run. Existing `full_song_run_02` must not be overwritten; use a new output directory.

## Run
```powershell
.\apply_patch.ps1 .\patches\karaoke_mfa_missing_textgrid_recovery_patch.zip -RunTests
```

Then rerun full-song CLI with a fresh `full_song_run_03` output directory.
