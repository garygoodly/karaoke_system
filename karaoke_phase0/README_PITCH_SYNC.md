# Reference smoothing + microphone timing adjustment

- Reference: centered 5-frame median, ON by default; no voiced interpolation through silence.
- Mic timing offset: -500 to +500 ms, default 0 ms. Positive values compare the current mic estimate with earlier reference audio. **Manual calibration only**; not automatic synchronization.
- Difference hidden for stale microphone estimates, missing reference pitch, or paused playback.
- Reference JSON does not need to be regenerated.
- Based on the previously verified timestamp-index fix. Apply only once on top of that patch.
- Run: `uv run --no-sync python -m pytest -q`
