# Karaoke Studio — Phase 0 (experimental)

First Chinese-language test: G.E.M. 泡沫. The supplied MP3 and user-provided lyrics are included under `samples/` for local testing only; do not redistribute these assets without permission.

## Goals
- Verify decoding and input lyrics (TXT/LRC).
- Separate original vocals and instrumental with Demucs.
- Generate **experimental** Mandarin character alignment with WhisperX.
- Extract raw pitch with librosa pYIN.
- Inspect results in a local HTML pitch/lyrics preview.

**Not yet implemented:** automatic stable-note segmentation, validated confidence calibration, manual correction GUI, real-time scoring, Bluetooth audio, recording, and formal ground-truth evaluation. These remain later milestones. Do not treat preview output as a passing QA result.

## Windows setup
Install Python 3.11 and FFmpeg (`ffmpeg` and `ffprobe` on PATH). PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
# Install CUDA-compatible PyTorch using the official selector at https://pytorch.org/get-started/locally/
pip install demucs
# Optional alignment module (may need compatible torch/torchaudio versions):
pip install whisperx
python main.py inspect
```

GPU use requires a CUDA-compatible PyTorch build. The NVIDIA driver's CUDA 13.2 capability does not mean a CUDA 13.2 toolkit must be installed. WhisperX installation and Chinese alignment model availability must be validated; if unavailable, stop with an explicit error rather than inventing character timestamps.

## Run each stage separately
```powershell
python main.py inspect
python main.py separate --device cuda
python main.py pitch --vocals "output/stems/htdemucs/song/vocals.wav" --start 30 --duration 30
python main.py align --vocals "output/stems/htdemucs/song/vocals.wav" --language zh --device cuda
python main.py preview --audio "output/stems/htdemucs/song/vocals.wav"
```

For a full-song pitch extraction, omit `--start` and `--duration`. The pitch output uses `output/pitch.npz` by default. The preview reads `output/lyrics_timeline.json`. If using the preview, run a local HTTP server from the project directory (`python -m http.server 8000`) and open `http://localhost:8000/output/preview.html`.

**Important:** WhisperX alignment in this prototype estimates lyric-line anchors by matching Whisper transcription to supplied lyrics. A poor match is flagged for manual review; a matching line is still *provisional*, not ground truth. Chinese character timestamps require empirical verification, and some WhisperX versions/models may not support the requested alignment configuration.

## Acceptance gates (not yet measured)
- Mandarin character onset within 150 ms: >=90% on independently hand-labeled samples.
- Octave-invariant pitch accuracy within 50 cents: >=85% on trusted vocal frames.
- Scorable coverage: >=80% of independently annotated expected vocal duration.
- Full audio alignment and no truncated stems; play/pause/seek synchronized in the preview.

## Tests
```powershell
pytest -q
```
