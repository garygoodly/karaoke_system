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
