# Architecture and user workflow

## Core flow

`Import Song → Prepare Song / Retry → Karaoke Player → Pitch Capture → Experimental Scoring`

Preparation is resumable: separation creates `vocals.wav` and `instrumental.wav`, known-lyrics alignment creates `lyrics_timeline.json`, and pitch extraction creates `reference_pitch.json`. The status is recorded in `preparation_status.json`. The current line-based mode does not require experimental MFA word alignment.

The GUI is a frontend over processing modules; it should not permanently modify the environment used by unrelated subprocesses. Git commit display helps identify which source version is running on each computer.

## Archived patch notes (verbatim from supplied ZIP snapshot)

The following historical notes are preserved for technical context. They may contain superseded setup commands; use the current project scripts as the authority.

---

### Historical source: README_KARAOKE_PLAYER_MVP.md

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


---

### Historical source: README_DUAL_DISPLAY_LATEST.md

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


---

### Historical source: README_GUI_PREPARATION.md

# GUI Song Preparation

Select an imported song in Song Library and click **Prepare Song / Retry**. The app selects CUDA if available, otherwise CPU, and runs the existing `tools/prepare_song.py` pipeline in a background QProcess. The progress bar shows 0/3 to 3/3 completed steps and logs appear in the existing log pane. Click **Cancel Analysis** to stop the process; completed artifacts are reused on retry. When ready, click **Karaoke Player / Lyrics QA**.

This patch modifies only `src/karaoke_phase0/gui.py` and adds one regression test. It does not change the existing pipeline, song data, or import behavior. New-song end-to-end preparation still needs validation on Windows.


---

### Historical source: README_GUI_SIMPLIFIED.md

# Simplified Song Library GUI

- Keep **Prepare Song / Retry** and **Karaoke Player / Lyrics QA** as the main actions.
- Hide legacy **Analyze Selected** and **Align Lyrics** buttons. The underlying methods remain for future diagnostics.
- Display **Ready** only when vocals, instrumental, lyrics timeline, and reference pitch files are present and nonempty, with valid JSON; failed/running checkpoints are not presented as Ready.
- Database status remains unchanged (e.g. `separated`), preserving compatibility with the current song-manager schema.
- No source audio, song database, or generated outputs are modified.

Apply using `./apply_patch.ps1` from PowerShell, then run pytest and restart the GUI.


---

### Historical source: README_PREPARATION_PIPELINE.md

# Resumable Song Preparation (Phase 1.0, backend)

This patch adds a **CLI orchestrator**, not yet the GUI button. It uses the existing Demucs, known-lyrics alignment, and torchcrepe reference extractor. It does **not** invoke the experimental MFA word-alignment pipeline; line-based playback remains the priority.

From `karaoke_phase0` (with dependencies installed):

```powershell
uv run --no-sync python .\tools\prepare_song.py --song-folder .\songs\song-3decb6500f5d --device cuda
```

For machines without supported NVIDIA CUDA, choose `--device cpu` (CPU processing can be slow).

Outputs in `generated/`: `vocals.wav`, `instrumental.wav`, `lyrics_timeline.json`, `reference_pitch.json`, and `preparation_status.json`.

- Valid existing outputs are skipped; failures are recorded to `preparation_status.json` and rerunning retries missing steps.
- Source MP3 and lyrics are never deleted by this pipeline. Existing valid generated outputs are not overwritten.
- A failed alignment stops the pipeline with `review_required`; it does not fabricate lyric timings. An existing valid timeline can still be used on rerun.
- Progress is step-level, not percentage; model downloads and inference may take time.
- GUI integration, automatic model/environment installation, and true cross-platform clean install verification are **not** included in this patch.
