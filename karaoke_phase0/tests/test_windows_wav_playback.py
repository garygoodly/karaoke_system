import importlib.util
from pathlib import Path
import wave

MODULE_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'annotate_acoustic_onsets.py'
spec = importlib.util.spec_from_file_location('onset_annotation_audio_fix', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeWinsound:
    SND_FILENAME = 0x20000
    SND_ASYNC = 1
    def __init__(self):
        self.calls = []
    def PlaySound(self, source, flags):
        self.calls.append((source, flags))


def test_async_playback_uses_file_and_cleans_on_stop():
    fake = FakeWinsound()
    player = module.WindowsWavPlayer(fake)
    player.play_pcm(b'\x00\x00' * 100, 16000)
    path, flags = fake.calls[-1]
    assert flags == fake.SND_FILENAME | fake.SND_ASYNC
    assert Path(path).exists()
    with wave.open(path, 'rb') as wav:
        assert wav.getframerate() == 16000
        assert wav.getnframes() == 100
    player.stop()
    assert fake.calls[-1] == (None, 0)
    assert not Path(path).exists()


def test_next_play_replaces_previous_temp_file():
    fake = FakeWinsound()
    player = module.WindowsWavPlayer(fake)
    player.play_pcm(b'\x00\x00', 8000)
    old = player._path
    player.play_pcm(b'\x00\x00', 8000)
    assert not Path(old).exists()
    assert Path(player._path).exists()
    player.stop()
