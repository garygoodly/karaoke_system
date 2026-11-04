"""Interactive, non-destructive acoustic onset annotation for Karaoke Studio.

Windows: uses winsound for playback. Requires matplotlib, numpy, soundfile,
scipy (already part of the Karaoke project). Never edits source JSON or WAV.
"""
import argparse
import os
import csv
import json
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np


def load_lines(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    lines = data.get('lines')
    if not isinstance(lines, list):
        raise ValueError('Expected v7 JSON with a lines array')
    return {int(x['line_id']): x for x in lines}


def read_labels(path):
    if not Path(path).exists():
        return {}
    with open(path, newline='', encoding='utf-8-sig') as f:
        return {int(row['line_id']): float(row['onset_seconds']) for row in csv.DictReader(f)}


def save_labels(path, labels):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8', dir=path.parent,
                                     prefix='.onsets-', suffix='.tmp', delete=False) as tmp:
        writer = csv.DictWriter(tmp, fieldnames=['line_id', 'onset_seconds', 'source'])
        writer.writeheader()
        for line_id, onset in sorted(labels.items()):
            writer.writerow({'line_id': line_id, 'onset_seconds': f'{onset:.3f}', 'source': 'manual_listening'})
        name = tmp.name
    Path(name).replace(path)


def clip_pcm(samples, sr, start, end):
    start = max(0, int(start * sr))
    end = min(len(samples), int(end * sr))
    if end <= start:
        raise ValueError('Empty playback interval')
    y = np.asarray(samples[start:end], dtype=np.float64)
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767).astype('<i2').tobytes()



class WindowsWavPlayer:
    """Play short WAV clips asynchronously using a filename, not SND_MEMORY."""

    def __init__(self, winsound_module=None):
        if winsound_module is None:
            import winsound as winsound_module
        self.winsound = winsound_module
        self._path = None

    def stop(self):
        # Stop playback before unlinking a WAV still in use by Windows.
        self.winsound.PlaySound(None, 0)
        if self._path is not None:
            try:
                os.unlink(self._path)
            except OSError:
                pass
            self._path = None

    def play_pcm(self, pcm, sr):
        self.stop()
        with tempfile.NamedTemporaryFile(suffix='.wav', prefix='karaoke-onset-', delete=False) as tmp:
            path = tmp.name
        try:
            with wave.open(path, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(sr)
                wav.writeframes(pcm)
            self._path = path
            self.winsound.PlaySound(path, self.winsound.SND_FILENAME | self.winsound.SND_ASYNC)
        except Exception:
            self.stop()
            raise


def main():
    parser = argparse.ArgumentParser(description='Listen, inspect, and label real lyric onsets; source files remain unchanged.')
    parser.add_argument('--audio', required=True)
    parser.add_argument('--v7', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--line-ids', nargs='+', type=int, default=[2, 5, 24])
    parser.add_argument('--lookback', type=float, default=2.0)
    parser.add_argument('--lookahead', type=float, default=1.5)
    args = parser.parse_args()
    if args.lookback <= 0 or args.lookahead <= 0:
        parser.error('lookback/lookahead must be positive')
    import soundfile as sf
    from scipy.signal import spectrogram
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button, RadioButtons

    samples, sr = sf.read(args.audio, dtype='float32', always_2d=True)
    audio = samples.mean(axis=1)
    lines = load_lines(args.v7)
    missing = [i for i in args.line_ids if i not in lines]
    if missing:
        parser.error(f'Line IDs missing in v7 report: {missing}')
    labels = read_labels(args.output)
    index = [0]
    player = WindowsWavPlayer() if sys.platform == 'win32' else None
    fig, (ax_wave, ax_spec) = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                           gridspec_kw={'height_ratios': [1, 2]})
    plt.subplots_adjust(bottom=0.21, hspace=0.15)
    status = fig.text(0.05, 0.02, 'Click waveform or spectrogram to set onset; then Save CSV.', fontsize=10)
    def stop_audio():
        if player is not None:
            player.stop()

    def draw():
        line = lines[args.line_ids[index[0]]]
        peak = float(line['token_peak_seconds'])
        lo, hi = max(0, peak - args.lookback), min(len(audio) / sr, peak + args.lookahead)
        part = audio[int(lo * sr):int(hi * sr)]
        if len(part) < 256:
            raise ValueError('Audio window too short')
        t = lo + np.arange(len(part)) / sr
        ax_wave.clear(); ax_spec.clear()
        stride = max(1, len(part) // 12000)
        ax_wave.plot(t[::stride], part[::stride], linewidth=.6, color='steelblue')
        nperseg = min(1024, len(part))
        f, ts, power = spectrogram(part, fs=sr, nperseg=nperseg, noverlap=nperseg * 3 // 4)
        mask = f <= 4500
        ax_spec.pcolormesh(lo + ts, f[mask], 10 * np.log10(np.maximum(power[mask], 1e-12)),
                           shading='auto', cmap='magma')
        ax_spec.set_ylabel('Frequency (Hz)')
        ax_spec.set_xlabel('Song time (seconds)')
        ax_wave.set_ylabel('Amplitude')
        for ax in (ax_wave, ax_spec):
            ax.axvline(peak, color='red', linewidth=1.5, label='CTC peak')
            prev = line.get('previous_end_constraint_seconds')
            if prev is not None:
                ax.axvline(float(prev), color='gray', linestyle=':', label='Previous end')
            for cue in line.get('candidate_onsets', []):
                ax.axvline(float(cue['time_seconds']), color='orange', alpha=.45, linewidth=1)
            if args.line_ids[index[0]] in labels:
                ax.axvline(labels[args.line_ids[index[0]]], color='limegreen', linewidth=2, label='Manual onset')
            ax.set_xlim(lo, hi)
        ax_wave.legend(loc='upper right', fontsize=8)
        fig.suptitle(f"Line {args.line_ids[index[0]]} | CTC peak {peak:.3f}s | manual {labels.get(args.line_ids[index[0]], 'unset')}")
        fig.canvas.draw_idle()

    def click(event):
        if event.inaxes not in (ax_wave, ax_spec) or event.xdata is None:
            return
        t = float(event.xdata)
        line = lines[args.line_ids[index[0]]]
        previous = line.get('previous_end_constraint_seconds')
        if previous is not None and t < float(previous):
            status.set_text('Warning: selection precedes previous-line CTC end; verify by listening.')
        else:
            status.set_text(f'Selected {t:.3f}s. Play a short clip, then Save CSV.')
        labels[args.line_ids[index[0]]] = t
        draw()

    def play(_):
        if sys.platform != 'win32':
            status.set_text('Playback requires Windows winsound; annotation still works.')
            fig.canvas.draw_idle()
            return
        line = lines[args.line_ids[index[0]]]
        center = labels.get(args.line_ids[index[0]], float(line['token_peak_seconds']))
        pcm = clip_pcm(audio, sr, center - .8, center + 1.2)
        try:
            player.play_pcm(pcm, sr)
            status.set_text(f'Playing around {center:.3f}s')
        except (OSError, RuntimeError) as exc:
            status.set_text(f'Playback failed: {exc}')
        fig.canvas.draw_idle()

    def change(step):
        stop_audio()
        index[0] = (index[0] + step) % len(args.line_ids)
        draw()

    def save(_):
        save_labels(args.output, labels)
        status.set_text(f'Saved {len(labels)} manual labels to {args.output}')
        fig.canvas.draw_idle()

    controls = [('Previous', .08, lambda _: change(-1)),
                ('Next', .24, lambda _: change(1)),
                ('Play 2s', .40, play),
                ('Stop', .56, lambda _: stop_audio()),
                ('Save CSV', .72, save)]
    for title, x, callback in controls:
        axis = fig.add_axes([x, .08, .14, .065])
        button = Button(axis, title)
        button.on_clicked(callback)
        # Retain references so matplotlib does not garbage collect buttons.
        fig.__dict__.setdefault('_annotation_buttons', []).append(button)
    fig.canvas.mpl_connect('button_press_event', click)
    draw()
    try:
        plt.show()
    finally:
        stop_audio()


if __name__ == '__main__':
    main()
