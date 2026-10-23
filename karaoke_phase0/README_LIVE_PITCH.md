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
