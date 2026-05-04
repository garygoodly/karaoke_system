# Karaoke System Full Scaffold

This repository is a **desktop karaoke application scaffold** for **English, Japanese, and Chinese**.
It follows a **subtitle-first** pipeline:

1. start from known lyrics or subtitles (`.lrc`, `.srt`, `.ass`, `.txt`, or a direct URL),
2. normalize text by language,
3. align the known text to the song audio,
4. extract reference pitch from the vocal stem,
5. run the player with live pitch tracking and scoring.

The result is more stable than relying on raw speech-to-text timestamps alone.

## Features

### Microphone input
- live pitch detection with `aubio`
- AEC interface with optional **SpeexDSP** wrapper
- scoring against reference pitch contour per lyric unit

### Speaker output
- play song video (`mp4`) with subtitle overlay
- switch between **original** and **karaoke** (instrumental) audio
- key shift up / down with cached rendered variants
- store reference pitch per lyric unit for Japanese-karaoke-style scoring

## Language support strategy

- **English**: tokenize by word, optional reading fallback equals source text
- **Japanese**: tokenize as character / mora-like units by default, optional reading via `pykakasi`
- **Chinese**: tokenize as CJK characters, optional reading via `pypinyin`

## Folder structure

```text
karaoke_system_full/
  app.py
  requirements.txt
  pyproject.toml
  README.md
  karaoke_system/
    __init__.py
    config.py
    exceptions.py
    models.py
    utils/
      files.py
      jsonx.py
      text.py
      time.py
    lyrics/
      normalize.py
      tokenize.py
      reading.py
      parsers/
        lrc.py
        srt_parser.py
      providers/
        base.py
        local_provider.py
        online_provider.py
    alignment/
      base.py
      heuristic_aligner.py
      whisperx_aligner.py
      mfa_aligner.py
      merger.py
    audio/
      aec.py
      devices.py
      ffmpeg_tools.py
      keyshift.py
      separator.py
    pitch/
      live_pitch.py
      note_mapper.py
      reference_pitch.py
    scoring/
      judge.py
      metrics.py
      smoothing.py
    engine/
      manifest_builder.py
      session.py
      timeline.py
    pipeline/
      preprocess_song.py
    ui/
      main_window.py
      pitch_bar.py
      score_panel.py
      subtitle_overlay.py
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

System dependencies:

- **FFmpeg** in `PATH`
- optionally **Demucs** for stem separation
- optionally **SpeexDSP** shared library for echo cancellation
- optionally **WhisperX** or **Montreal Forced Aligner** for stronger alignment

## Preprocess a song

### Use local lyrics

```bash
python -m karaoke_system.pipeline.preprocess_song \
  --input /path/to/song.mp4 \
  --song-id my_song \
  --title "My Song" \
  --language ja \
  --lyrics-file /path/to/lyrics.lrc \
  --output-dir ./songs \
  --use-demucs \
  --aligner heuristic
```

### Use a subtitle URL

```bash
python -m karaoke_system.pipeline.preprocess_song \
  --input /path/to/song.mp4 \
  --song-id my_song \
  --title "My Song" \
  --language zh \
  --lyrics-url https://example.com/song.srt \
  --output-dir ./songs \
  --karaoke-audio /path/to/instrumental.m4a
```

### Use WhisperX alignment when available

```bash
python -m karaoke_system.pipeline.preprocess_song \
  --input /path/to/song.mp4 \
  --song-id my_song \
  --title "My Song" \
  --language en \
  --lyrics-file /path/to/lyrics.srt \
  --output-dir ./songs \
  --aligner whisperx \
  --whisperx-model large-v3
```

## Run the player

```bash
python app.py --song-dir ./songs/my_song
```

## Output layout

```text
songs/
  my_song/
    manifest.json
    lyrics.json
    video/
      video_only.mp4
    audio/
      original_+0.m4a
      karaoke_+0.m4a
    cache/
      playback_original_+0.mp4
      playback_karaoke_+2.mp4
    work/
      original.wav
      vocals.wav
      no_vocals.wav
      alignment/
```

## Important implementation notes

- `heuristic_aligner.py` is a **working fallback** that can split line timing across tokens even without WhisperX/MFA.
- `whisperx_aligner.py` and `mfa_aligner.py` are **integration adapters**. They are real code, but depend on external binaries/models.
- Reference pitch is stored as a **pitch curve**, not just one note per word.
- The UI is a **desktop scaffold**, not a finished commercial karaoke skin.
- Echo cancellation is designed as a replaceable stage; for production, keep it native-backed.


## Windows quick start

Windows launcher scripts are included under `scripts/windows/`. The easiest path is:

```powershell
.\scripts\windows\install_windows.ps1 -InstallFFmpeg
.\scripts\windows\doctor_windows.ps1
.\scripts\windows\start_player.ps1 -SongDir .\songs\my_song
```

There is also a dedicated guide in `README_WINDOWS.md`.

Important notes for Windows:

- The Windows installer uses `requirements-windows.txt` for a smoother setup.
- `aubio` is optional on Windows because the app now includes a NumPy-based live pitch fallback.
- `FFmpeg` is still required for preprocessing and cache generation.
- Key shift needs an FFmpeg build that includes the `rubberband` filter.


## Quick Start (Windows)

1. Open PowerShell in the repo root.
2. Install dependencies:

   .\scripts\windows\install_windows.ps1 -InstallFFmpeg

3. Check environment:

   .\scripts\windows\doctor_windows.ps1

4. Put your files here:

   - .\media\AAA.mp4
   - .\lyrics\AAA.lrc

5. Preprocess the song:

   .\scripts\windows\preprocess_song.ps1 `
     -Input .\media\AAA.mp4 `
     -SongId AAA `
     -Title "AAA" `
     -Language ja `
     -LyricsFile .\lyrics\AAA.lrc `
     -UseDemucs `
     -BuildCache

6. Launch the player:

   .\scripts\windows\start_player.ps1 -SongDir .\songs\AAA