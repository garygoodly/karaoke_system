# Dual Lyrics Display — Latest Source Patch

This patch was built against the latest uploaded `karaoke.zip` (144 archive entries).

## Changes

- MODIFY `src/karaoke_phase0/gui.py` — load optional MFA timings when opening Preview Lyrics QA.
- MODIFY `src/karaoke_phase0/lyrics_preview.py` — Line Mode (default) and Word Mode toggle.
- ADD `src/karaoke_phase0/lyrics_display_data.py` — read latest numeric `full_song_run_XX`, reject incomplete/warned tokens.
- ADD `tests/test_dual_display.py` — three regression tests.
- DELETE none.

## Behavior

- Line Mode uses `generated/lyrics_timeline.json` and does not require MFA.
- Word Mode uses `generated/mfa/full_song_run_XX/lyrics_timeline_mfa.json` if present.
- Missing, warned, incomplete or inconsistent token sequences display the full line instead of fabricated per-character timings.
- The latest run is authoritative; older runs are not used silently.
- No song data or original timelines are modified.

## Install / Verify

Place ZIP in `patches/`, then run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_dual_display_latest_patch.zip -RunTests
```

Open the GUI, select a song, then click `Preview Lyrics QA`.

Local Linux verification: **65 passed**. Re-run on Windows before committing.
