# Karaoke Studio — Alignment Engineering History

**Last updated:** 2026-11-03  
**Scope:** Windows setup lessons relevant to alignment, Mandarin known-lyrics alignment, and CTC experiments through Overlapping Joint CTC v3.  
**Status:** Research / offline diagnostics. **No CTC benchmark is approved to overwrite the production `lyrics_timeline.json`.**

> This is a decision and incident log, not a claim of production readiness. Numbers are taken from project test outputs and the user's approximate listening annotations. Where the root cause is not proven, it is labeled as a hypothesis.

## 1. Why this work began

In **〈年輪說〉** (song folder `songs/song-075151e6a644/`), Line Mode sometimes displayed lyrics **2–3 seconds late**, while other lines appeared correct. A global negative offset would damage correctly timed lines. We therefore investigated **per-line alignment**, first using existing ASR/forced-alignment diagnostics, then direct known-text CTC acoustic search and joint alignment.

**Reference song:** 〈泡沫〉 is the existing regression case. Improvements to 〈年輪說〉 must not silently degrade it.

## 2. Current production pipeline (important distinction)

1. Demucs separates the original song into `vocals.wav` and instrumental audio.
2. For timestamp-free lyrics, `faster_whisper` transcribes the vocal audio into ASR segments with approximate timestamps.
3. `global_match_lines()` matches the **supplied known lyrics** to an ordered sequence of ASR segments. It **already supports joining multiple adjacent ASR segments**; it uses normalized text, `SequenceMatcher` similarity, a segment-span penalty, and global dynamic programming.
4. A candidate audio window is created from the matched ASR segment range (including small padding).
5. `whisperx.align(..., return_char_alignments=True)` forced-aligns the **original supplied lyrics**, not ASR's possibly incorrect words, inside that window. Relative timestamps are converted back to song time.
6. Quality checks flag missing characters, implausibly short/long character durations, and overlaps. The result can be marked `review_required`.

**Critical distinction:** The later *ASR-guided diagnostic tool* used single ASR segments as candidates. Its limitation is **not** proof that the production `global_match_lines()` lacks multi-segment matching.

## 3. Failure investigation: initial line and character timing

| Observation | Evidence | Meaning / response |
|---|---|---|
| Some lines 2–3 s late | User listening to 〈年輪說〉 | Local timing problem; do not apply a global offset. |
| First character can absorb many seconds | Examples: Line 2 `這` 7.585 s; Line 5 `計` 7.831 s | Forced alignment can produce a technically valid but acoustically implausible path. |
| Many characters compressed to ~20 ms | Initial timeline diagnostics: 151/282 at or below 25 ms; 36 characters >=2 s | Add quality gating rather than treating completion as accuracy. |
| Many lines require review | 27/28 lines flagged in initial diagnostic | Alignment output is provisional. |
| `preparation_status.json` may say `ready` while timeline says `review_required` | Diagnostic comparison | Correct preparation-status propagation; a completed pipeline is not automatically a verified alignment. |
| ASR may transcribe homophones incorrectly | `這圈是我` recognized as `這全是我` | Use known lyrics as the alignment authority; consider phonetic similarity only after measuring current matcher. |

**Quality-gate patch:** Added/strengthened anomaly detection and preparation-status handling. This patch **does not itself repair line boundaries**. The reported local test count was 7 for that patch; full regression status should be verified separately for each applied version.

## 4. Diagnostic experiments that did not solve the problem

### 4.1 Pitch-onset diagnostics

Used reference-pitch/F0 onsets as potential lyric starts. **Only 3/28 lines** had a single candidate; the other 25 were ambiguous or lacked a usable onset. F0 onsets can indicate note changes, re-articulation, or instrumental residuals rather than the first lyric character. **Decision:** Do not automatically modify line timestamps from pitch onset alone.

### 4.2 Single-segment ASR-guided diagnostics

Also produced **3/28 unique candidates**. Detailed examination revealed that a single lyric line often spans multiple ASR segments:

- Line 1: `切開我身體` (32–35 s) + `研究我的風雨` (35–38 s).
- Line 2: `這全是我` (38–42 s) + `那全是你` (42–45 s) + `開過心的開心` (45–53 s).
- Line 5: `計算著我` (64–68 s) + `計算著你` (68–71 s) + `活不去的過去` (71–77 s).

The diagnostic sometimes chose the *middle* segment, creating an apparent 3–4 s delay. **Lesson:** Inspect candidate generation and rejection reasons before tuning thresholds. Production global matching already allows multi-segment spans, so investigate its actual decisions separately.

## 5. Direct known-text CTC: model and tokenizer selection

**Hypothesis:** Instead of requiring an ASR transcript match, use known lyric text to search CTC frame-level acoustic probabilities directly (subsequence Viterbi), then recover candidate time intervals.

The first CTC search patch passed synthetic unit tests but did not initially prove Mandarin singing accuracy. We deliberately kept it **offline and non-destructive**.

| Model | Text normalization | Unknown tokens for 〈年輪說〉 | Coverage on 308 tested tokens |
|---|---|---:|---:|
| `jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn` | OpenCC traditional → simplified | 6 | 98.05% |
| `wbbbbb/wav2vec2-large-chinese-zh-cn` | OpenCC traditional → simplified | 1 (`烬`, Line 18) | 99.68% |

For the first model, unknown characters included `篆`, `啼` (twice), `冉` (twice), and `烬`. A single traditional lyric `切開我身體` had unknown tokens; converting to `切开我身体` eliminated unknown tokens for that phrase. **Tokenizer coverage is not model accuracy.** Keep original traditional lyrics for UI and maintain an explicit model-text mapping. Never silently replace unknown characters with guessed homophones.

**Environment lesson:** Keep experimental `transformers`/OpenCC dependencies separate using `uv run --no-sync --with ...`; do not disturb the locked production CUDA/PyTorch environment. A complex `python -c` one-liner failed in PowerShell because of nested quoting; use a standalone Python script or here-string for reproducible diagnostics.

## 6. Independent CTC and five-line A/B benchmark

The direct CTC model located `切开我身体` at **32.462–34.104 s**, consistent with the approximate ASR 32–35 s window. Two near-identical top hits came from overlapping search chunks, **not independent evidence**. Deduplicate overlapping chunk hits and avoid interpreting uncalibrated total log likelihood as a probability of correctness.

Five-line comparison (CTC minus ASR diagnostic start):

| Line | ASR diagnostic start | Independent CTC start | Difference |
|---:|---:|---:|---:|
| 0 | 27.000 | 27.633 | +0.633 s |
| 1 | 32.000 | 32.462 | +0.462 s |
| 2 | 42.000 | 38.989 | -3.011 s |
| 3 | 53.000 | 53.589 | +0.589 s |
| 5 | 68.000 | 64.925 | -3.075 s |

Line 2 and 5 earlier starts matched the user's observation that the display was late. However, the ASR values above are from the **diagnostic**, not necessarily the production global-matcher output.

## 7. Full-song independent CTC + ordered dynamic programming

Applied candidate deduplication and a global chronological constraint to 28 lines. **25/28** lines received selected times; Lines **15, 18, 24** had no final selected time. Line 15 and 18 lacked candidates because of tokenizer compatibility in this experiment; Line 24 had **20 candidates** but was skipped by the global optimizer.

Notable original-to-CTC changes:

| Line | Original | Independent CTC | Delta |
|---:|---:|---:|---:|
| 2 | 41.500 | 38.989 | -2.511 s |
| 5 | 67.500 | 64.925 | -2.575 s |
| 16 | 167.500 | 165.060 | -2.440 s |
| 19 | 192.500 | 190.571 | -1.929 s |
| 17 | 177.500 | 179.274 | +1.774 s |

**Coverage (25/28) is not accuracy.** Total CTC log probabilities vary with duration and cannot be compared naively across different lyric lengths. DP skip penalties and confidence scores remain uncalibrated.

## 8. Why Line 24 exposed the weakness of independent CTC

| Line | Selected/candidate interval | Notes |
|---:|---|---|
| 23 | 222.713–228.398 s | `時間暫停 再繼續` selected |
| 24 | 227.603–234.449 s | `十是寂寞夜裡 百是懷了疑` candidate, **not selected** |
| 25 | 234.429–240.936 s | Next line selected |

Line 24 candidate overlaps Line 23 by **0.795 s** and Line 25 by **0.020 s**. Its start was also earlier than the user's approximate manual **229 s** onset. A plausible hypothesis was that the acoustic sound of the previous line's final `續` was confused with the next line's initial `十`; this exact phonetic confusion was **not independently proven**.

**Decision:** Do not simply relax overlap rules or force every line to have a CTC candidate. Instead, jointly align adjacent lyrics in a shared CTC path so each character is constrained by preceding and following characters.

## 9. Joint CTC v1: the key breakthrough

For Lines 23 and 24, concatenate the **model-normalized lyric text** and perform one CTC Viterbi alignment over a shared audio interval. Backtrack token timings to derive line boundaries. This makes the token order explicit and prevents independently aligning two lyric lines to the same sound region.

**Observed results:**

- Line 23 final token ends **228.390 s**.
- Line 24 first token starts **229.111 s**.
- Boundary gap **0.721 s**.
- User's approximate Line 24 onset: **~229 s**.

Independent CTC's Line 24 start was 227.603 s; joint CTC was much closer to the approximate listening annotation. The CTC ordering constraint does **not** prove that the underlying character identification is correct.

## 10. Grouped Joint CTC v2: scale to the song

Joint-align adjacent groups of 2–4 lines (tested with group size 3) and recover per-line start/end times. Grouping reduces individual optimization size but **does not impose cross-group constraints**. Unsupported-character lines may be isolated; some groups return `no_path`.

**Results:** 9 groups `candidate_needs_review`, 1 group `no_path` (Line 14), and skipped/isolated Lines 15 and 18 in the displayed run.

| Line | Original | Grouped v2 start | User approximate onset |
|---:|---:|---:|---:|
| 2 | 41.500 | 39.010 | ~38 s |
| 5 | 67.500 | 64.930 | ~65 s |
| 24 | 229.500 | 229.112 | ~229 s |

Line 24 was nearly unchanged relative to two-line Joint v1 (229.111 vs 229.112 s). This demonstrates **stability under one grouping change**, not millisecond accuracy.

## 11. Overlapping Group Joint CTC v3

Use overlapping windows (e.g., `[0,1,2]`, `[2,3,4]`) and compare repeated estimates for the same line. Report median, spread, observation count, and review status. In the actual run: **13 groups**, **12 candidate groups**, **1 `no_path`** (Line 14).

| Line | Observations | Median | Spread | Status |
|---:|---|---:|---:|---|
| 2 | 38.981, 39.010 | 38.995 s | 0.029 s | `consistent_needs_review` |
| 5 | 64.947 | 64.947 s | 0.000 s | `single_observation_needs_review` |
| 24 | 229.508 | 229.508 s | 0.000 s | `single_observation_needs_review` |

**Critical lesson:** Spread = 0 with **one observation** provides **no evidence of cross-group consistency**. Line 24 v3 (229.508 s, group `[23,24,25]`) differs from v2 (229.112 s, group `[22,23,24]`), showing context dependence. Both are plausibly close to the approximate human 229 s estimate, but neither is validated to millisecond precision.

## 12. Ground truth and accuracy limitations

The user listened to three lines and supplied **approximate** onset times:

| Line | Human estimate | Original start | Independent CTC | Grouped v2 | Overlapping v3 |
|---:|---:|---:|---:|---:|---:|
| 2 | ~38 s | 41.500 | 38.989 | 39.010 | 38.995 |
| 5 | ~65 s | 67.500 | 64.925 | 64.930 | 64.947 |
| 24 | ~229 s | 229.500 | 227.603 | 229.112 | 229.508 |

These estimates support qualitative improvements in selected cases, but **do not support 75 ms, 111 ms, or other fine-grained accuracy claims**. The three lines were chosen because they were informative, so this is **not** an unbiased full-song accuracy estimate.

## 13. Windows and engineering workflow incidents

These are adjacent setup/deployment lessons that affected our ability to reproduce alignment experiments across PCs:

| Incident | Cause / evidence | Working resolution / prevention |
|---|---|---|
| MFA raw executable failed: `libsndfile.dll` / error `0x7e` | Conda `libsndfile` installed `sndfile.dll`; directly launched MFA lacked the Conda DLL search environment | Launch via `conda run -n karaoke-mfa mfa ...`, or set `Library\\bin` **only for the MFA subprocess**. Do not rename DLLs. |
| FFmpeg / WhisperX audio load failed after DLL PATH workaround | Suspected inherited Conda DLL path conflict; exact dependency conflict not conclusively proven | Isolate MFA subprocess PATH from GUI/FFmpeg; restore parent PATH after MFA. |
| `uv` / `conda` command missing on Computer B despite installation | WinGet path or terminal environment not refreshed; Miniforge location differed from README assumption | Detect executable locations, use actual Miniforge install directory, restart parent terminal/IDE when required. |
| Patch `-RunTests` pytest `import file mismatch` | Tests under `patches/env_isolation_unpacked/tests/` duplicated production `tests/` module names | Configure `[tool.pytest.ini_options]` with `testpaths=["tests"]` and `norecursedirs` including `patches`; change was committed and pushed. |
| Patch READMEs, generated files, archives cluttered Git | Unclear source-vs-generated-data conventions | Keep authoritative docs in `docs/`; patch-only notes in ignored `patches/`; ignore `.venv-uv/`, recordings, backups, local archives; stop tracking obsolete root `README_*.md`. |
| `apply_patch.ps1` test failure despite successful file copy | Patch application and test execution are distinct phases | Use standardized validate → backup → apply → test; inspect the first failing phase and do not claim rollback unless it occurred. |

**Operational rule:** A passing local pytest or GitHub CI confirms only the tests actually executed. It does not guarantee every Windows GPU, audio driver, model cache, or GUI configuration works on another PC.

## 14. Design decisions retained

1. **Non-destructive by default:** all CTC benchmark results go into separate diagnostic JSON files; never overwrite the production timeline without review.
2. **Known lyrics are authoritative:** ASR transcriptions are approximate localization evidence, not replacements for supplied text.
3. **Prefer joint character ordering to independent line-level overlap relaxation:** the Line 23/24 experiment supports this direction.
4. **Preserve confidence distinctions:** `candidate_needs_review`, `single_observation_needs_review`, `no_path`, `review_required` are not synonyms for `ready`.
5. **Keep dependencies and deployment reproducible:** isolated experiments, locked main environment, tests, versioned formal docs, and standard patch installation.

## 15. Open challenges and next experiment

- **Sliding-window v4:** ensure important lines (especially 5 and 24) have at least two *valid* observations, not merely zero spread from one observation.
- **Cross-group boundary consistency:** prevent overlapping groups from producing contradictory line times; quantify context sensitivity.
- **Unknown characters:** test a more suitable singing/phoneme CTC model or an explicit validated G2P path rather than silently changing lyrics. Lines 15/18 remain problematic in the tested character model.
- **`no_path` debugging:** inspect why Line 14 fails even when its model text is potentially representable; avoid conflating vocabulary failures with alignment failures.
- **Score calibration:** CTC log likelihood, duration effects, candidate margins, and DP skip penalties are not calibrated confidence probabilities.
- **Ground truth:** create higher-precision, reproducible manual annotations for more lines across 〈年輪說〉 and 〈泡沫〉; compare median absolute onset error, tail errors, coverage, and regression cases.
- **Production integration gate:** only promote an algorithm after demonstrating real-song accuracy and no regression. Keep a manual correction path for ambiguous lines.

## 16. Useful project files and commands

**Song:** `songs/song-075151e6a644/generated/`  
**Inputs:** `vocals.wav`, `lyrics_timeline.json`, `asr_segments.json`, `reference_pitch.json`  
**Experiment outputs:** `direct_ctc_benchmark.json`, `ctc_ab_five_lines.json`, `ctc_full_song_diagnostics.json`, `ctc_joint_23_24.json`, `ctc_grouped_diagnostics.json`, `ctc_overlapping_v3.json`.

**Testing (from `karaoke_phase0`):**

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
uv run --no-sync python -m pytest .\tests -q
```

**Standard patch installation:**

```powershell
.\apply_patch.ps1 .\patches\<patch-name>.zip -RunTests
```

**Git discipline:** stage specific source, test, and documentation files; run `git diff --cached --check`; commit and push only after review. Do not stage songs, generated WAV/CSV/JSON, model caches, ZIP archives, or backup copies by accident.

## 17. How to extend this document

For every new alignment experiment, append a dated entry with:

- **Problem / hypothesis** — what failed and why the new method might help.
- **Code version and parameters** — patch/commit, model ID, group size/stride, audio range, input files.
- **Evidence** — test counts, exact candidate timestamps, error messages, and manual ground truth precision.
- **Outcome** — improvement, regression, inconclusive, or blocked; separate coverage, consistency, and accuracy.
- **Decision / next step** — what to keep, revert, or test next.

**Next planned entry:** Sliding-Window Joint CTC v4 evaluation; not yet implemented or verified in this record.
