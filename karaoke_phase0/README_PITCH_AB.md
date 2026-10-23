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
