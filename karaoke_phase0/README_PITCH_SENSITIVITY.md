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
