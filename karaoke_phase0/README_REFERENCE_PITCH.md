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
