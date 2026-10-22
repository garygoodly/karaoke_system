# Karaoke Player MVP Patch

## What changed

- MODIFY `src/karaoke_phase0/gui.py`: opens the existing Lyrics QA page in player mode.
- MODIFY `src/karaoke_phase0/lyrics_preview.py`: adds Play/Pause, Restart, Seek, and separate instrumental/vocal volume controls. Line Mode remains the default; Word Mode still uses only available MFA data.
- MODIFY `src/karaoke_phase0/lyrics_qa_server.py`: serves `instrumental.wav` through a strict allowlist and supports byte-range requests.
- ADD `tests/test_karaoke_player.py`: player markup and HTTP route tests.
- DELETE none.

## Requirements

The selected song must already contain `generated/vocals.wav`, `generated/instrumental.wav`, and `generated/lyrics_timeline.json`.

## Install

Copy this ZIP to `patches/`, then run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_player_mvp_patch.zip -RunTests
.\run_gui_uv.ps1
```

Select the song and click **Karaoke Player / Lyrics QA**.

## Limitations

This is a browser-based player. Vocal and instrumental use separate HTML audio elements; a drift correction mechanism keeps them near the instrumental clock, but this is not sample-accurate mixing. Test audible synchronization on Windows. Microphone monitoring, pitch tracking, and scoring are not implemented in this patch. Original timeline and audio files are not modified.

## Cleanup

No project files should be deleted. Keep `songs/` and MFA benchmark data locally.
