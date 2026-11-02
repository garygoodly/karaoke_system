# Audio pipeline and MFA troubleshooting

## Line mode versus experimental word mode

The primary playback path uses known-lyrics alignment and a line timeline. MFA word/character alignment remains experimental and should not overwrite validated `lyrics_timeline.json` without review. OOV handling, Chinese character fallbacks, and mixed-language processing have separate failure modes.

For MFA on Windows, prefer Conda activation (`conda run`) or subprocess-only DLL PATH configuration. Do not change the global PATH for FFmpeg or the GUI.

## Archived patch notes (verbatim from supplied ZIP snapshot)

The following historical notes are preserved for technical context. They may contain superseded setup commands; use the current project scripts as the authority.

---

### Historical source: README_CHINESE_CHARACTER_FALLBACK.md

# Chinese Text Normalization + Character G2P Fallback

## Scope

This patch is incremental on the existing 56-test Windows project. It changes only `mfa_full_song.py`, adds `chinese_fallback.py`, and adds six tests. No existing lyrics, timelines, model caches, or song data are modified.

When first-pass MFA G2P fails on a Mandarin lyric line, the existing workflow isolates that line. This patch then retries only those isolated lines, each in a separate MFA corpus, after:

1. One-to-one variant normalization (`説` -> `說`, `着` -> `著`, `剎` -> `刹`).
2. Separating Han characters with spaces to avoid whole-sentence OOV tokens.
3. Converting MFA output back to original displayed characters only when the full character sequence matches exactly.

A fallback line is still `review_required` and receives `character_g2p_fallback_needs_review`. If G2P or alignment fails, the line stays `unresolved_pronunciation`. The mixed-language `Oh-oh` line is still unsupported. This is a conservative experiment, not a verified pronunciation/accuracy solution; variant mapping and polyphonic characters require QA.

## Files

- MODIFY `src/karaoke_phase0/mfa_full_song.py`
- ADD `src/karaoke_phase0/chinese_fallback.py`
- ADD `tests/test_chinese_fallback.py`
- ADD `README_CHINESE_CHARACTER_FALLBACK.md`
- DELETE none

## Install

Place ZIP under `patches/` and run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_chinese_character_fallback_patch.zip -RunTests
```

## Run a new full-song experiment

```powershell
$dict = "$env:USERPROFILE\Documents\MFA\pretrained_models\dictionary\mandarin_taiwan_mfa.dict"
$mfa = "$env:LOCALAPPDATA\miniforge3\envs\karaoke-mfa\Scripts\mfa.exe"
uv run --no-sync python .\tools\run_mfa_full_song.py --song-folder .\songs\song-3decb6500f5d --dictionary "$dict" --mfa-exe "$mfa" --output .\songs\song-3decb6500f5d\generated\mfa\full_song_run_08
```

Inspect `full_song_run_08/qa_report.json` and `full_song_run_08/mfa_character_fallback/` for per-line results.

## Validation

On the older uploaded ZIP with this patch applied, 47 tests pass (41 original tests plus six new tests). The user's current Windows tree includes later patches and 56 tests, so the expected count is 62 if all six tests are discovered. The complete current Windows environment and MFA end-to-end execution have not been verified here.


---

### Historical source: README_CHINESE_OOV_RECOVERY.md

# Chinese OOV isolation patch

- MODIFY `src/karaoke_phase0/mfa_full_song.py`
- ADD `tests/test_chinese_oov_recovery.py`
- DELETE none.

If MFA G2P cannot resolve some Chinese words, the full-song runner records the affected lines as `unresolved_pronunciation`, removes only those clips from the next MFA attempt, and continues with remaining lines. Failed attempts are preserved in `mfa_run/report.json` and successful retries in `mfa_run_retry_XX/`.

This patch does **not** implement robust normalization or segmentation, and does not guarantee all 35 lines align. It intentionally preserves original lyrics and does not overwrite `lyrics_timeline.json`.

Run tests: `uv run --no-sync python -m pytest -q`.

Run full song with a NEW output directory, such as `full_song_run_06`.


---

### Historical source: README_MFA_RECOVERY_INSTALLER.md

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


---

### Historical source: README_MFA_TEMP_ISOLATION.md

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


---

### Historical source: README_MIXED_LANGUAGE_RECOVERY.md

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


---

### Historical source: README_RENAME_RETRY.md

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
