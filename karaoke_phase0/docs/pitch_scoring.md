# Pitch detection and experimental scoring

## Pipeline

Microphone pitch (YIN or torchcrepe) and reference pitch are aligned using playback timestamps and experimental auto timing sync. Capture CSV stores pitch, periodicity and time offsets. Reference F0 and the vocal-activity mask are separate concepts.

The score UI includes frame-based pitch accuracy, singing coverage, note-based v2 accuracy and note coverage. These are experimental metrics, **not** calibrated commercial karaoke scores. Note-based v2 scores only successfully matched candidate notes; missing candidates should not automatically be treated as bad singing.

For diagnostics, compare identical captures, inspect low-confidence F0, octave errors and sync offsets, and preserve the original frame baseline.

## Archived patch notes (verbatim from supplied ZIP snapshot)

The following historical notes are preserved for technical context. They may contain superseded setup commands; use the current project scripts as the authority.

---

### Historical source: README_AUTO_TIMING_SYNC.md

# Automatic timing synchronization (experimental)

Apply with `apply_patch.ps1 <zip> -RunTests` from karaoke_phase0.

Auto timing sync is enabled by default. It gathers a rolling 14-second history of microphone F0 and compares pitch-change patterns against the reference at offsets from -400 to +400 ms in 25 ms steps. Calibration needs enough pitch changes and a clear best match; otherwise it uses 0 ms or holds the last trusted estimate. The manual slider becomes available when Auto timing sync is unchecked.

This estimates combined performance and system latency, not hardware latency alone. It does not correct wrong harmonics, melody differences, or source separation artifacts. It is an experimental comparison aid, not a scoring-grade alignment algorithm. Re-evaluate during playback; check the displayed status. Existing reference JSON is reused.


---

### Historical source: README_CREPE_SMOOTHING.md

# Live torchcrepe 5-frame Median Smoothing

Adds an **OFF-by-default** checkbox to the Karaoke Player's live pitch panel.

- Applies a causal 5-frame median to **torchcrepe only**; YIN is unchanged.
- The filter uses the latest five *received* voiced predictions. With the current backend's update interval (~85 ms), this is **not** the same as the offline 5 x 10 ms experiment. A causal five-result median may lag a genuine note change by roughly two updates (~170 ms), plus existing inference latency.
- Unvoiced input clears the filter; no fabricated voiced result.
- Switching detectors, disabling the microphone, or toggling smoothing clears filter history.
- Does not change MFA, player audio or the lyric timeline.

## Install

Place ZIP in `patches/`, then:

```powershell
.\apply_patch.ps1 .\patches\karaoke_crepe_median_smoothing_patch.zip -RunTests
```

Start the existing torchcrepe server and Karaoke GUI as before. In the Live Pitch panel, select `torchcrepe (local Python)` and toggle **torchcrepe smoothing (5 frames)** to compare. Test a held vowel and a quick pitch transition; smoothing can hide genuine fast transitions.

## Changes

- MODIFY `src/karaoke_phase0/lyrics_preview.py`
- ADD `tests/test_crepe_smoothing.py`
- ADD `README_CREPE_SMOOTHING.md`
- DELETE none


---

### Historical source: README_LIVE_PITCH.md

# Karaoke Live Pitch Detection

## Patch contents
- MODIFY `src/karaoke_phase0/lyrics_preview.py`
- ADD `tests/test_live_pitch.py`
- ADD this README
- DELETE none

## Features
- F0 estimation (YIN-style difference function) from the existing microphone analyser, 75–900 Hz.
- Frequency in Hz, nearest equal-tempered note (A4=440 Hz), and recent pitch trace.
- Low-level or unvoiced frames show `Unvoiced`, with gaps in the plot.
- Microphone off resets the display. No recording or uploads.

## Limitations
- No scoring, reference pitch, or smoothing. Octave errors and background-music leakage remain possible.
- Tested on synthetic tones; real vocal input requires Windows/browser validation.
- Uses a 4096-sample analyser buffer, which can increase response latency.

## Install
Place ZIP in `patches/`, then run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_live_pitch_detection_patch.zip -RunTests
```

Start GUI using `.\run_gui_uv.ps1`, open Karaoke Player, Enable Mic, and sing a sustained note with headphones.


---

### Historical source: README_LIVE_TORCHCREPE.md

# Live torchcrepe detector (experimental)

This patch adds a selectable neural pitch backend while retaining YIN as default.

## Install

```powershell
.\apply_patch.ps1 .\patches\karaoke_live_torchcrepe_patch.zip -RunTests
uv pip install --python .\.venv-uv\Scripts\python.exe torchcrepe websockets
```

## Start local pitch service (second PowerShell terminal)

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu
```

Then launch the GUI, enable microphone, and select **torchcrepe (local Python)** from the Detector dropdown. YIN remains available without a backend. The backend listens only on 127.0.0.1:8766 and receives raw microphone snapshots. It does not save recordings. Stop it with Ctrl+C.

## Limitations

- Prototype transports overlapping analyser snapshots via WebSocket, not an AudioWorklet stream. CPU inference may lag or skip samples. For production, use an AudioWorklet with a ring buffer, sample-rate conversion and timestamps.
- Mic level sensitivity slider currently applies to YIN only. Torchcrepe uses `--min-rms` and `--min-periodicity` CLI flags.
- First torchcrepe inference may be slow. Latency and vowel robustness must be measured on the target Windows PC.
- Local WebSocket has no authentication. Use only on a trusted machine; do not expose the port outside loopback.


---

### Historical source: README_MICROPHONE_INPUT.md

# Karaoke Microphone Input + Live Level Meter

## Installation

Put `karaoke_microphone_input_patch.zip` in `patches/` and run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_microphone_input_patch.zip -RunTests
```

Then start the GUI with `./run_gui_uv.ps1`, open the Karaoke Player / Lyrics QA, and press **Enable Mic**. The browser will ask permission. Select a microphone, adjust Gain or Mute, and watch the input level meter.

## Safety and behavior

- Monitoring defaults to OFF to avoid acoustic feedback. Use headphones before enabling Monitoring.
- No microphone audio is recorded, uploaded, or stored. The input is processed locally in the browser.
- Disabling the microphone stops the audio tracks and closes the Web Audio context. Closing the page also stops tracks.
- Browsers generally require `localhost` or HTTPS for microphone permission. This app serves on `127.0.0.1`.
- Meter displays approximate raw microphone RMS in dBFS, before Mic Gain and Mute. Gain affects optional monitoring only; it does not alter recorded audio (there is no recording feature).
- Echo cancellation and noise suppression are requested from the browser. Latency varies by device and browser.
- This does not implement pitch detection or scoring.

## Patch inventory

- MODIFY `src/karaoke_phase0/lyrics_preview.py`
- ADD `tests/test_microphone_player.py`
- ADD `README_MICROPHONE_INPUT.md`
- DELETE none

## Validation

Regression test run against latest available Project ZIP plus Karaoke Player MVP patch: `67 passed` on Linux. JavaScript syntax verified with Node.js. Windows browser microphone permission and audio monitoring still require real-device testing.


---

### Historical source: README_PITCH_AB.md

# Pitch A/B Benchmark: YIN vs torchcrepe

This is an **offline diagnostic** on the same audio segment, not a validated singing-accuracy test. It does **not** change the Karaoke Player, its microphone capture, or the current YIN implementation.

## Setup (PowerShell, from `karaoke_phase0`)

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-uv'
uv pip install --python .\.venv-uv\Scripts\python.exe torchcrepe
```

`torchcrepe` may download model weights on first use. `torch`, `numpy`, `scipy`, `soundfile`, and `matplotlib` are also required. If missing, install them into `.venv-uv`. The above command intentionally does not change `uv.lock`; this is an experimental dependency.

## Compare on existing separated vocals

```powershell
uv run --no-sync python .\tools\compare_pitch_yin_crepe.py --wav .\songs\song-3decb6500f5d\generated\vocals.wav --start 20 --duration 30 --device cpu --output .\benchmarks\pitch_ab\run_01
```

Optional `--device cuda` if the PyTorch environment supports it. The default is CPU and the small `tiny` model.

Outputs: `pitch_comparison.csv`, `pitch_comparison.png`, `summary.json`.

## Interpreting results

- `unvoiced_fraction`: how often the detector does not return an F0; smaller is not automatically better (noise can produce false positives).
- `octave_sized_jumps_over_900_cents`: large adjacent voiced-frame changes; not proof of an octave error without reference F0.
- Inspect plot during held vowels and consonant transitions.
- For actual **microphone** performance, record a short sample of your voice; separated studio vocals may not represent your headset mic conditions.
- This Python YIN reference approximates the method, not a byte-for-byte reproduction of browser YIN.

## Run targeted tests

```powershell
uv run --no-sync python -m pytest tests/test_pitch_ab_benchmark.py -q
```


---

### Historical source: README_PITCH_SENSITIVITY.md

# Adjustable pitch sensitivity

## Changes
- MODIFY `src/karaoke_phase0/lyrics_preview.py`: adds a `Pitch sensitivity` slider, -60 to -20 dBFS, default -38 dBFS. The slider changes the RMS gate used by pitch detection in real time. Lower values detect quieter input.
- MODIFY `tests/test_live_pitch.py`: update assertion to match configurable gate.
- ADD `tests/test_pitch_threshold.py`: verifies UI wiring.
- DELETE none.

## Install
Put the ZIP into `patches/` and run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_pitch_sensitivity_patch.zip -RunTests
```

## Usage
Enable Mic, then adjust Pitch sensitivity while singing. Try -45 dBFS if quieter notes show Unvoiced; return toward -38 dBFS if background noise is detected. This changes the input loudness gate, not the YIN periodicity confidence cutoff (0.15). The microphone level meter still shows pre-gain signal. Headphones recommended.

## QA
3 focused tests passed locally, including synthetic tones. Full Windows suite and actual mic behavior need verification. No source songs or MFA files changed.


---

### Historical source: README_PITCH_SYNC.md

# Reference smoothing + microphone timing adjustment

- Reference: centered 5-frame median, ON by default; no voiced interpolation through silence.
- Mic timing offset: -500 to +500 ms, default 0 ms. Positive values compare the current mic estimate with earlier reference audio. **Manual calibration only**; not automatic synchronization.
- Difference hidden for stale microphone estimates, missing reference pitch, or paused playback.
- Reference JSON does not need to be regenerated.
- Based on the previously verified timestamp-index fix. Apply only once on top of that patch.
- Run: `uv run --no-sync python -m pytest -q`


---

### Historical source: README_REFERENCE_PITCH.md

# Reference Pitch + Live Comparison (experimental)

- Offline extract reference F0 from `generated/vocals.wav` with torchcrepe (tiny, 20 ms hops).
- In Karaoke Player, display Reference Hz and user-minus-reference cents using the instrumental playback clock.
- Defaults to torchcrepe and smoothing ON; YIN remains selectable.
- No score and no changes to MFA or lyrics timeline.
- **Caution:** playback output latency, microphone latency and Demucs artifacts are not calibrated. Displayed cents are diagnostic, **not an accuracy grade**. Silence and low-periodicity frames remain unvoiced.

## Windows commands

```powershell
uv run --no-sync python .\tools\extract_reference_pitch.py --song-folder .\songs\song-3decb6500f5d --device cpu
uv run --no-sync python -m pytest -q
uv run --no-sync python .\tools\run_live_torchcrepe.py --device cpu
```

Open a second terminal and run `./run_gui_uv.ps1`, then open Karaoke Player. `reference_pitch.json` is an experimental generated artifact; do not commit it to Git by default. If the extraction already exists, the CLI refuses to overwrite it.

## Patch manifest

- MODIFY `src/karaoke_phase0/gui.py`
- MODIFY `src/karaoke_phase0/lyrics_preview.py`
- ADD `src/karaoke_phase0/reference_pitch.py`
- ADD `tools/extract_reference_pitch.py`
- ADD `tests/test_reference_pitch.py`
- ADD this README
- DELETE none


---

### Historical source: README_GUI_NOTE_V2.md

# GUI Note-Based v2 Scoring

Adds three experimental post-capture indicators alongside the existing Frame-Based Pitch Accuracy and Singing Coverage:
- Note-Based v2 Accuracy (scored candidate notes only)
- Note Coverage (scored / candidate notes within capture time window)
- Unscored Notes

Uses the same v2 reference segmentation thresholds and user median-F0 scoring as the offline benchmark. Uses capture `time_s` which is already auto-sync aligned; no second offset is applied. Does not replace or modify the existing frame scoring. Reference candidates are not validated melody notes, so scores must not be compared directly with commercial karaoke scores.

Install from `karaoke_phase0`:

```powershell
.\apply_patch.ps1 .\patches\karaoke_gui_note_scoring_v2_patch.zip -RunTests
```

Restart the GUI and local torchcrepe server. In the player, enable mic, Start pitch capture, sing, then Stop & download CSV. The score panel shows both methods.


---

### Historical source: README_GUI_SINGING_SCORE.md

# Phase 1.1 - Experimental GUI Singing Results

Apply using `./apply_patch.ps1 ./patches/karaoke_gui_singing_score_patch.zip -RunTests` in PowerShell.

Changes `src/karaoke_phase0/lyrics_preview.py` and `src/karaoke_phase0/gui.py` only; adds `tests/test_gui_singing_score.py`.

Generate the vocal activity mask once per song (if not already present):

`uv run --no-sync python .\tools\build_vocal_activity.py --song-folder .\songs\song-3decb6500f5d`

Start the torchcrepe backend and GUI as usual. Open player, Enable Mic, press Start pitch capture, sing during playback, then Stop & download CSV. Results show immediately below capture controls, and CSV download is retained.

Pitch Accuracy is the mean score for valid F0 pairs with 50 cents full-credit tolerance and 300 cents zero-score threshold. Singing Coverage is the ratio of valid user F0 frames inside the vocal activity mask. Both use already-aligned `time_s`, not playback_time_s, and never apply offset twice. No overall score. The browser score is diagnostic and does not replace the offline CLI. A missing mask displays `Mask missing` instead of fabricating coverage.

Known limits: Browser score uses raw captured F0, not the smoothed displayed pitch; changing auto-sync mid-song can distort alignment. Low-confidence and missing user pitch is excluded from pitch accuracy but reduces singing coverage. Mask is heuristic and is not proof of singing. No clean Windows GUI run has been performed here.


---

### Historical source: README_NOTE_SCORING_AB.md

# Note-Based Pitch Scoring A/B Benchmark

Experimental offline-only scoring; **does not replace GUI scoring**.

## Install

Place ZIP in `patches/` and run:

```powershell
.\apply_patch.ps1 .\patches\karaoke_note_scoring_ab_patch.zip -RunTests
```

## Run

```powershell
uv run --no-sync python .\tools\benchmark_note_scoring.py --reference .\songs\song-3decb6500f5d\generated\reference_pitch.json --user-csv .\karaoke_pitch_capture.csv --output .\benchmarks\note_scoring\run_01
```

Produces `note_scoring_summary.json` and `note_scoring_details.csv`.

- `frame_baseline_score` reproduces the original frame-level heuristic from the same reference and capture (subject to floating-point rounding).
- `note_score` averages **one median-F0 score per scored candidate note**; it is not directly comparable to commercial karaoke scoring.
- `note_coverage` is the fraction of reference candidate notes with enough valid user pitch observations. Missing notes are not assigned a score of zero.
- Reference note boundaries are inferred from F0 jumps (85 cents), with minimum 160 ms duration. Sustained slides, vibrato, and imperfect F0 may create or split notes incorrectly.
- Both sides use 0.35 periodicity threshold. Trim 60 ms at each candidate-note edge to avoid note transitions.
- Capture `time_s` is already auto-sync adjusted; **do not apply offset again**.
- Optional `--octave-invariant` scores an octave transposition as correct, for an A/B sensitivity check.

**Interpretation:** A higher note score alone does not prove better accuracy. Inspect low-scoring rows and validate note boundaries against the actual melody before changing the GUI algorithm.


---

### Historical source: README_NOTE_SCORING_V2.md

# Reference Note Segmentation v2 (experimental)

This patch adds a separate v2 benchmark; it does not change the GUI scorer or existing v1 benchmark.

## Run

```powershell
uv run --no-sync python .\tools\benchmark_note_scoring_v2.py --reference .\songs\song-3decb6500f5d\generated\reference_pitch.json --user-csv .\karaoke_pitch_capture.csv --output .\benchmarks\note_scoring\v2
```

Requires the prior `tools/benchmark_note_scoring.py` (Phase 1.3 patch).

v2 uses local log-frequency median smoothing, bridges brief voiced gaps, merges similar-pitch fragments, and restricts segmentation to the capture time span. `v1_window` is recalculated over the same time span for a fairer comparison. It does not require or re-run Demucs/MFA.

Interpretation: `note_coverage` counts *scored candidate notes / candidate notes within the recording interval*. A high score at low coverage may reflect selection bias. Note segmentation is not a verified transcription of the melody.


---

### Historical source: README_PITCH_CAPTURE.md

# Phase 1.1 — Browser pitch capture for offline scoring

This adds Start pitch capture / Stop & download CSV to the player. The CSV includes aligned `time_s`, raw `crepe_hz`, `crepe_periodicity`, playback timestamp, applied offset, offset-trusted flag, and detector. The existing scoring CLI can read the CSV.

Only capture during playback. Stop before seeking; a seek stops capture to avoid a discontinuous time axis. Auto-sync estimates can change mid-recording, so interpret results as diagnostic, not a calibrated singing grade. For consistent scoring, turn off Auto Sync and calibrate offset first, or examine the offset column.

Run: `uv run --no-sync python .\tools\score_pitch_offline.py --reference .\songs\song-3decb6500f5d\generated\reference_pitch.json --user-csv .\karaoke_pitch_capture.csv --output .\benchmarks\pitch_score\run_01`

The browser downloads the CSV to its configured Downloads folder. Move it into the project directory or use its absolute path. No audio is recorded, only F0 metadata. No database changes.


---

### Historical source: README_PITCH_DIAGNOSTICS.md

# Pitch Scoring Diagnostics (experimental)

This is a read-only analysis tool. It does not modify the Karaoke GUI, song data, scoring rules, or existing CSV.

Run from `karaoke_phase0`:

```powershell
uv run --no-sync python .\tools\diagnose_pitch_score.py --reference .\songs\song-3decb6500f5d\generated\reference_pitch.json --user-csv .\karaoke_pitch_capture.csv --output .\benchmarks\pitch_score\diagnostics_01
```

Outputs: `diagnostics_summary.json` and `diagnostics_frames.csv`.

- Baseline uses the existing 50-cent tolerance, 300-cent zero score, and 0.35 confidence threshold.
- Sensitivity compares user periodicity thresholds 0.2, 0.35, 0.5, and 0.65.
- `playback_time_without_auto_offset` is a diagnostic counterfactual, **not** proof that Auto Sync is wrong.
- Low-confidence and missing F0 are counted separately. Error bins identify large differences; they do not prove detector errors.
- `time_s` already incorporates the captured Auto Sync offset; do not apply offset a second time.
- No ground truth; score remains experimental and is not comparable to commercial Karaoke ratings.


---

### Historical source: README_PITCH_SCORING.md

# Phase 1.1: Offline Pitch Scoring MVP

This is an **experimental diagnostic**, not a calibrated singing score. It does not alter the GUI or playback. It compares reference pitch JSON with a user-pitch CSV on the **same song timeline**. `human_test.wav` from an unrelated recording is **not** aligned to the song and must not be scored against it.

The existing A/B CSV format (`time_s,crepe_hz,crepe_periodicity`) is accepted, but it is only suitable if its times correspond to the song playback times. To evaluate a singer, a future feature must capture microphone F0 together with song playback timestamps and auto-sync offset.

## Test

```powershell
uv run --no-sync python -m pytest -q tests/test_pitch_scoring.py
```

## Example (only when the CSV shares the reference song timeline)

```powershell
uv run --no-sync python .\tools\score_pitch_offline.py --reference .\songs\song-3decb6500f5d\generated\reference_pitch.json --user-csv .\benchmarks\pitch_ab\aligned_singer.csv --output .\benchmarks\pitch_score\run_01
```

Optional `--offset-ms -150` selects the reference 150 ms earlier; `--octave-invariant` treats octave-shifted singing as equivalent. Outputs are `score_summary.json` and `score_frames.csv`.

## Metric

Each valid matched frame receives 100 points for absolute pitch error <= 50 cents, decreasing linearly to 0 at 300 cents. Missing or low-confidence frames are **excluded** and counted separately as coverage, not silently treated as 0 or 100. The result is the mean of comparable frames, not a full-song performance score. No rhythm, lyrics, dynamics, pitch-reference accuracy, or latency calibration is assessed.


---

### Historical source: README_VOCAL_ACTIVITY.md

# Vocal Activity Mask / Singing Coverage

Adds separate singing coverage based on **separated vocals audio energy constrained to lyrics timing**. Does not overwrite the existing scoring formula, GUI, or reference pitch.

## Generate mask

```powershell
uv run --no-sync python .\tools\build_vocal_activity.py --song-folder .\songs\song-3decb6500f5d
```

Creates `generated/vocal_activity.json`. Uses existing `generated/vocals.wav`, `generated/lyrics_timeline.json` and `generated/reference_pitch.json`; no MFA or Demucs rerun.

## Compare with user pitch CSV

```powershell
uv run --no-sync python .\tools\score_singing_coverage.py --song-folder .\songs\song-3decb6500f5d --user-csv .\karaoke_pitch_capture.csv --output .\benchmarks\pitch_score\coverage_run_01
```

Produces `singing_coverage_summary.json` containing `pitch_score` (unchanged), `singing_coverage`, and frame counts. The CSV's `time_s` is already auto-sync adjusted; no extra offset is applied.

## Caveats

- Energy in separated vocals may include instrumental leakage, breaths or effects. Lyrics time windows are an additional guard, not verified ground truth.
- Coverage means detected user F0 during expected singing windows; it cannot fully distinguish missing singing from failed F0 detection.
- Does not create an overall score or impose missing-singing penalties.
