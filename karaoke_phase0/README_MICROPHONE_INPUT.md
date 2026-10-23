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
