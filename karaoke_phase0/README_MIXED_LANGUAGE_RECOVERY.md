# Karaoke Phase 0.5 — Mixed-Language OOV Recovery

## Changes

- MODIFY `src/karaoke_phase0/mfa_full_song.py`
- ADD `tests/test_mixed_language_recovery.py`
- ADD `README_MIXED_LANGUAGE_RECOVERY.md`
- DELETE nothing

## Behavior

The Mandarin-only MFA stage now excludes an entire line containing Latin words (for example `為甚麼難過? Oh-oh`) from the Mandarin batch. That line remains in the final report as `review_required` with `unsupported_language`, empty tokens, and a failed-line entry. Other Chinese lines continue to align. The original lyrics, original WhisperX timeline, song audio, and prior MFA runs are untouched.

This is a conservative fallback: it does **not** align the Chinese portion of a mixed line, and does not implement English or Japanese alignment. Manual correction (or a future multilingual aligner) is required before Karaoke Ready.

## Apply

Unzip into the `karaoke_phase0` project root, preserving relative paths. Alternatively use your `apply_patch.ps1` script. Keep the original song data and generated results.

## Verify

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run --no-sync python -m pytest -q
```

On the tested snapshot, 47 tests passed (45 original plus 2 new tests). Windows real-MFA integration remains to be tested.

## Run full song

Use a **new** output directory, since the workflow refuses to overwrite non-empty results:

```powershell
$dict = "$env:USERPROFILE\Documents\MFA\pretrained_models\dictionary\mandarin_taiwan_mfa.dict"
$mfa = "$env:LOCALAPPDATA\miniforge3\envs\karaoke-mfa\Scripts\mfa.exe"
uv run --no-sync python .\tools\run_mfa_full_song.py --song-folder .\songs\song-3decb6500f5d --dictionary "$dict" --mfa-exe "$mfa" --output .\songs\song-3decb6500f5d\generated\mfa\full_song_run_02
```

Check `qa_report.json` and `lyrics_timeline_mfa.json` in the new output folder. A line with `Oh-oh` should be marked `unsupported_language`, not passed to Mandarin G2P. Other errors, if any, still require diagnosis.
