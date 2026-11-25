# Boundary Conflict Validation — diagnostic only

This patch adds read-only analysis of the Line 18 -> 19 boundary.

- Retains CTC group provenance and detects repeated boundary characters (e.g. 燒).
- Uses 50-ms RMS windows to identify *unverified* low-energy cues; these are not syllable identification.
- Always sets `auto_adopt=false`; never modifies lyrics_timeline.json or GUI playback.
- Writes `generated/ctc_boundary_conflict_18_19.json` during hybrid preparation.
- Handles unavailable/unsupported WAV by recording an explicit status.

## Install

Place ZIP under patches and use `apply_patch.ps1 ... -RunTests`.
Then run:

`uv run --no-sync python .\tools\integrate_boundary_conflict.py`

The integration tool backs up `hybrid_pipeline.py` and only inserts code if the expected anchor matches.
Run the existing `prepare_song.py --ctc-hybrid-preview` command to produce the report.

## Scope

Diagnostic-only. No threshold changes, automatic adoption, or forced lyric timing corrections.
