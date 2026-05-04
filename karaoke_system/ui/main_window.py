from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from karaoke_system.audio.keyshift import AudioVariantCache
from karaoke_system.config import DEFAULT_SETTINGS
from karaoke_system.engine.session import KaraokeSession
from karaoke_system.models import SongManifest, load_lines
from karaoke_system.pitch.live_pitch import LivePitchTracker
from karaoke_system.pitch.note_mapper import midi_to_note_name
from karaoke_system.ui.pitch_bar import PitchBar
from karaoke_system.ui.score_panel import ScorePanel
from karaoke_system.ui.subtitle_overlay import SubtitleOverlay
from karaoke_system.utils.time import seconds_to_mmss


class MainWindow(QMainWindow):
    def __init__(self, song_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.song_dir = Path(song_dir)
        self.manifest = SongManifest.load(self.song_dir / "manifest.json")
        self.lines = load_lines(self.song_dir / self.manifest.lyrics_path)
        self.session = KaraokeSession(self.lines, tolerance_cents=DEFAULT_SETTINGS.runtime.judge_tolerance_cents)
        self.variant_cache = AudioVariantCache(self.song_dir, self.manifest)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.live_pitch = LivePitchTracker(
            sample_rate=DEFAULT_SETTINGS.runtime.sample_rate,
            block_size=DEFAULT_SETTINGS.runtime.block_size,
        )
        self._current_key_shift = 0
        self._current_mode = self.manifest.default_mode
        self._build_ui()
        self._wire_signals()
        self._load_media()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"Karaoke - {self.manifest.title}")
        central = QWidget(self)
        layout = QVBoxLayout(central)

        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        self.subtitle_overlay = SubtitleOverlay(self.video_widget)
        self.subtitle_overlay.setGeometry(0, 0, 1200, 140)
        self.subtitle_overlay.raise_()

        controls = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.mic_button = QPushButton("Mic Start")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["original", "karaoke"])
        self.key_spin = QSpinBox()
        self.key_spin.setRange(-6, 6)
        self.position_label = QLabel("00:00")

        controls.addWidget(self.play_button)
        controls.addWidget(self.pause_button)
        controls.addWidget(self.mic_button)
        controls.addWidget(QLabel("Mode"))
        controls.addWidget(self.mode_combo)
        controls.addWidget(QLabel("Key"))
        controls.addWidget(self.key_spin)
        controls.addStretch(1)
        controls.addWidget(self.position_label)

        self.pitch_bar = PitchBar(self)
        self.score_panel = ScorePanel(self)

        layout.addWidget(self.video_widget, 10)
        layout.addWidget(self.pitch_bar)
        layout.addWidget(self.score_panel)
        layout.addLayout(controls)

        self.setCentralWidget(central)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.start()

    def _wire_signals(self) -> None:
        self.play_button.clicked.connect(self.player.play)
        self.pause_button.clicked.connect(self.player.pause)
        self.mic_button.clicked.connect(self._toggle_mic)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.key_spin.valueChanged.connect(self._on_key_changed)
        self._timer.timeout.connect(self._poll_state)

    def _load_media(self) -> None:
        media_path = self.variant_cache.ensure_playback_media(kind=self._current_mode, key_shift=self._current_key_shift)
        self.player.setSource(QUrl.fromLocalFile(str(media_path)))

    def _toggle_mic(self) -> None:
        if self.mic_button.text() == "Mic Start":
            try:
                self.live_pitch.start()
            except Exception as exc:
                QMessageBox.warning(self, "Microphone start failed", str(exc))
                return
            self.mic_button.setText("Mic Stop")
        else:
            self.live_pitch.stop()
            self.mic_button.setText("Mic Start")

    def _on_mode_changed(self, mode: str) -> None:
        self._current_mode = mode  # type: ignore[assignment]
        position = self.player.position()
        self._load_media()
        self.player.setPosition(position)

    def _on_key_changed(self, key_shift: int) -> None:
        self._current_key_shift = key_shift
        position = self.player.position()
        self._load_media()
        self.player.setPosition(position)

    def resizeEvent(self, event) -> None:  # pragma: no cover - GUI event path
        super().resizeEvent(event)
        self.subtitle_overlay.setGeometry(24, self.video_widget.height() - 150, self.video_widget.width() - 48, 120)

    def _poll_state(self) -> None:
        playback_time = self.player.position() / 1000.0
        self.position_label.setText(seconds_to_mmss(playback_time))
        snapshot = self.session.update(playback_time, self.live_pitch.latest_midi)
        progress = self.session.timeline.line_progress_at(playback_time)
        self.subtitle_overlay.set_progress(progress)
        self.pitch_bar.set_values(snapshot.target_midi, snapshot.live_midi)
        self.score_panel.update_scores(
            current=snapshot.instant_score,
            average=snapshot.average_score,
            target_text=midi_to_note_name(snapshot.target_midi),
            live_text=midi_to_note_name(snapshot.live_midi),
        )
