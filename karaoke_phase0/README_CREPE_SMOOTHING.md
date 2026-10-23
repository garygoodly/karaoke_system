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
