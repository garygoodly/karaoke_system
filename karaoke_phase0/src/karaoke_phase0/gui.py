"""PySide6 song library, import and asynchronous Demucs separation."""
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QProcess, QUrl, Qt, QTimer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QTabWidget, QProgressBar, QAbstractItemView,
)
from .version_info import git_version
from .song_manager import import_song, list_songs, get_song, set_song_status
from .separation import demucs_command, publish_stems
from .alignment_workflow import read_timeline
from .lyrics_preview import render as render_lyrics_preview
from .lyrics_display_data import load_word_timings
from .lyrics_qa_server import start_preview_server


class SongLibrary(QMainWindow):
    def __init__(self, root):
        super().__init__()
        self.root = Path(root).resolve()
        self.mp3 = None
        self.lyrics_file = None
        self.process = None
        self.qa_servers = []
        self.active_song_id = None
        self.active_task = None
        self.preparation_folder = None
        self.prepare_timer = QTimer(self)
        self.prepare_timer.timeout.connect(self.poll_preparation)
        self.setWindowTitle('Karaoke Studio - Song Library [Git ' + git_version(self.root) + ']')
        self.resize(960, 700)
        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        library = QWidget()
        ll = QVBoxLayout(library)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(['Song', 'Artist', 'Language', 'Status'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        ll.addWidget(self.table)
        buttons = QHBoxLayout()
        self.prepare_btn = QPushButton('Prepare Song / Retry')
        self.prepare_btn.clicked.connect(self.prepare_selected)
        buttons.addWidget(self.prepare_btn)
        self.analyze_btn = QPushButton('Analyze Selected (GPU)')
        self.analyze_btn.clicked.connect(self.analyze_selected)
        self.analyze_btn.hide()  # Legacy diagnostic action; not shown in main workflow.
        self.align_btn = QPushButton('Align Lyrics (GPU)')
        self.align_btn.clicked.connect(self.align_selected)
        self.align_btn.hide()  # Legacy diagnostic action; not shown in main workflow.
        self.lyrics_preview_btn = QPushButton('Karaoke Player / Lyrics QA')
        self.lyrics_preview_btn.clicked.connect(self.preview_lyrics)
        buttons.addWidget(self.lyrics_preview_btn)
        self.cancel_btn = QPushButton('Cancel Analysis')
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_analysis)
        buttons.addWidget(self.cancel_btn)
        refresh = QPushButton('Refresh Library')
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(refresh)
        ll.addLayout(buttons)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        ll.addWidget(self.progress)
        self.status_label = QLabel('Select a song, then Prepare Song / Retry.')
        ll.addWidget(self.status_label)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        ll.addWidget(self.log)
        audio_controls = QHBoxLayout()
        self.vocal_btn = QPushButton('Preview Vocals')
        self.vocal_btn.clicked.connect(lambda: self.preview('vocals.wav'))
        self.music_btn = QPushButton('Preview Instrumental')
        self.music_btn.clicked.connect(lambda: self.preview('instrumental.wav'))
        self.stop_btn = QPushButton('Stop Preview')
        self.stop_btn.clicked.connect(self.stop_preview)
        for b in (self.vocal_btn, self.music_btn, self.stop_btn):
            audio_controls.addWidget(b)
        ll.addLayout(audio_controls)
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)
        self.player.errorOccurred.connect(lambda error, message: self.status_label.setText('Playback error: ' + message))
        tabs.addTab(library, 'Song Library')
        add = QWidget()
        form = QVBoxLayout(add)
        self.title_edit = QLineEdit()
        self.artist_edit = QLineEdit()
        self.language = QComboBox()
        self.language.addItems(['auto', 'zh', 'en', 'ja'])
        for label, widget in [('Song title (required)', self.title_edit), ('Artist', self.artist_edit), ('Language', self.language)]:
            form.addWidget(QLabel(label))
            form.addWidget(widget)
        self.mp3_label = QLabel('No MP3 selected')
        choose_mp3 = QPushButton('Choose MP3...')
        choose_mp3.clicked.connect(self.pick_mp3)
        form.addWidget(choose_mp3)
        form.addWidget(self.mp3_label)
        self.lyrics_tabs = QTabWidget()
        paste = QWidget()
        paste_layout = QVBoxLayout(paste)
        self.lyrics_text = QTextEdit()
        self.lyrics_text.setPlaceholderText('Paste the full lyrics here...')
        paste_layout.addWidget(self.lyrics_text)
        self.lyrics_tabs.addTab(paste, 'Paste lyrics')
        file_tab = QWidget()
        fl = QVBoxLayout(file_tab)
        self.lyrics_label = QLabel('No TXT/LRC selected')
        choose_lyrics = QPushButton('Choose TXT / LRC...')
        choose_lyrics.clicked.connect(self.pick_lyrics)
        fl.addWidget(choose_lyrics)
        fl.addWidget(self.lyrics_label)
        fl.addStretch()
        self.lyrics_tabs.addTab(file_tab, 'Lyrics file')
        form.addWidget(self.lyrics_tabs)
        form.addWidget(QLabel('Import MOVES source files into managed songs folder after confirmation.'))
        submit = QPushButton('Import Song (Move Sources)')
        submit.clicked.connect(self.do_import)
        form.addWidget(submit)
        tabs.addTab(add, 'Add Song')
        self.tabs = tabs
        self.songs = []
        self.refresh()

    def pick_mp3(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select MP3', '', 'MP3 (*.mp3)')
        if path:
            self.mp3 = path
            self.mp3_label.setText(path)
            if not self.title_edit.text().strip():
                self.title_edit.setText(Path(path).stem)

    def pick_lyrics(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select lyrics', '', 'Lyrics (*.txt *.lrc)')
        if path:
            self.lyrics_file = path
            self.lyrics_label.setText(path)

    @staticmethod
    def display_song_status(folder, database_status):
        """Derive player readiness from outputs, not the separation-only DB status.

        Never display Ready based only on a checkpoint or database value.
        """
        import json
        folder = Path(folder)
        generated = folder / 'generated'
        stems = all((generated / name).is_file() and
                    (generated / name).stat().st_size > 0
                    for name in ('vocals.wav', 'instrumental.wav'))
        if not stems:
            return database_status
        for name in ('lyrics_timeline.json', 'reference_pitch.json'):
            path = generated / name
            if not path.is_file() or path.stat().st_size == 0:
                return 'Separated (preparation incomplete)'
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, UnicodeError, ValueError):
                return 'Separated (preparation incomplete)'
            if not isinstance(data, (dict, list)) or not data:
                return 'Separated (preparation incomplete)'
        checkpoint = generated / 'preparation_status.json'
        if checkpoint.is_file():
            try:
                report = json.loads(checkpoint.read_text(encoding='utf-8'))
                if report.get('status') in ('failed', 'review_required', 'running'):
                    return 'Needs review' if report['status'] != 'running' else 'Preparing'
            except (OSError, UnicodeError, ValueError, TypeError):
                return 'Needs review'
        return 'Ready'

    def refresh(self):
        selected_id = self.selected_song_id()
        self.songs = list_songs(self.root)
        self.table.setRowCount(len(self.songs))
        for i, song in enumerate(self.songs):
            for j, key in enumerate(('title', 'artist', 'language', 'status')):
                value = self.display_song_status(song['folder'], song['status']) if key == 'status' else song[key]
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
            if song['id'] == selected_id:
                self.table.selectRow(i)

    def selected_song_id(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(getattr(self, 'songs', [])):
            return None
        return self.songs[row]['id']

    def prepare_selected(self):
        if self.process is not None:
            return
        song_id = self.selected_song_id()
        if not song_id:
            QMessageBox.warning(self, 'No selection', 'Select a song first.')
            return
        folder = Path(get_song(self.root, song_id)['folder'])
        project = Path(__file__).resolve().parents[2]
        script = project / 'tools' / 'prepare_song.py'
        if not script.is_file():
            QMessageBox.warning(self, 'Missing preparation tool', str(script))
            return
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.active_song_id = song_id
        self.active_task = 'preparation'
        self.preparation_folder = folder
        self.log.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText(f'Preparing song ({device}); completed steps will be reused...')
        self.prepare_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.align_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.errorOccurred.connect(self.process_error)
        self.process.finished.connect(self.process_finished)
        self.process.start(sys.executable, [str(script), '--song-folder', str(folder), '--device', device])
        self.prepare_timer.start(500)

    def poll_preparation(self):
        if self.preparation_folder is None:
            return
        import json
        status_file = self.preparation_folder / 'generated' / 'preparation_status.json'
        if not status_file.is_file():
            return
        try:
            report = json.loads(status_file.read_text(encoding='utf-8'))
            steps = report.get('steps', {})
            names = ('separation', 'alignment', 'reference_pitch')
            done = sum(steps.get(name, {}).get('status') in ('completed', 'skipped_existing') for name in names)
            current = next((name for name in names if steps.get(name, {}).get('status') == 'running'), None)
            failed = next((name for name in names if steps.get(name, {}).get('status') == 'failed'), None)
            self.progress.setValue(round(100 * done / len(names)))
            if failed:
                self.status_label.setText(f'Preparation failed at {failed}; see log. Retry will reuse completed steps.')
            elif current:
                self.status_label.setText(f'Preparing {current} ({done}/{len(names)} steps complete)...')
        except (OSError, ValueError, TypeError):
            pass  # Writer may be updating the checkpoint; retry on the next poll.

    def analyze_selected(self):
        if self.process is not None:
            return
        song_id = self.selected_song_id()
        if not song_id:
            QMessageBox.warning(self, 'No selection', 'Select a song first.')
            return
        song = get_song(self.root, song_id)
        folder = Path(song['folder'])
        if song['status'] == 'separated':
            if QMessageBox.question(self, 'Re-analyze', 'Existing stems will be replaced. Continue?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        try:
            command = demucs_command(folder)
            set_song_status(self.root, song_id, 'analyzing')
        except Exception as exc:
            QMessageBox.critical(self, 'Cannot analyze', str(exc))
            return
        self.active_song_id = song_id
        self.active_task = 'separation'
        self.log.clear()
        self.progress.setRange(0, 0)  # Indeterminate until Demucs reports completion.
        self.status_label.setText('Running Demucs on NVIDIA CUDA GPU...')
        self.analyze_btn.setEnabled(False)
        self.align_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.errorOccurred.connect(self.process_error)
        self.process.finished.connect(self.process_finished)
        self.process.start(command[0], command[1:])
        self.refresh()

    def align_selected(self):
        if self.process is not None:
            return
        song_id = self.selected_song_id()
        if not song_id:
            QMessageBox.warning(self, 'No selection', 'Select a song first.')
            return
        song = get_song(self.root, song_id)
        folder = Path(song['folder'])
        if not (folder / 'generated' / 'vocals.wav').is_file():
            QMessageBox.warning(self, 'Missing vocals', 'Run Analyze Selected (GPU) first.')
            return
        if (folder / 'generated' / 'lyrics_timeline.json').exists():
            if QMessageBox.question(self, 'Re-align', 'Existing lyrics alignment will be replaced. Continue?',
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        self.active_song_id = song_id
        self.active_task = 'alignment'
        self.log.clear()
        self.progress.setRange(0, 0)
        self.status_label.setText('Aligning supplied lyrics with WhisperX (CUDA)...')
        self.analyze_btn.setEnabled(False)
        self.align_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.errorOccurred.connect(self.process_error)
        self.process.finished.connect(self.process_finished)
        lang = song['language'] if song['language'] != 'auto' else 'zh'
        self.process.start(sys.executable, [str(Path(__file__).resolve().parents[2] / 'main.py'),
                                            'align-song', '--folder', str(folder),
                                            '--language', lang, '--device', 'cuda'])

    def preview_lyrics(self):
        song_id = self.selected_song_id()
        if not song_id:
            QMessageBox.warning(self, 'No selection', 'Select a song first.')
            return
        folder = Path(get_song(self.root, song_id)['folder'])
        try:
            timeline = read_timeline(folder)
            reference_file = folder / 'generated' / 'reference_pitch.json'
            reference_pitch = None
            vocal_activity = None
            mask_file = folder / 'generated' / 'vocal_activity.json'
            if mask_file.is_file():
                import json
                vocal_activity = json.loads(mask_file.read_text(encoding='utf-8-sig'))
            if reference_file.is_file():
                import json
                reference_pitch = json.loads(reference_file.read_text(encoding='utf-8'))
            page = render_lyrics_preview(timeline, folder / 'generated' / 'lyrics_qa.html',
                                         word_timings=load_word_timings(folder), player_mode=True,
                                         reference_pitch=reference_pitch, vocal_activity=vocal_activity)
            server, url = start_preview_server(page, folder / 'generated' / 'vocals.wav',
                                               folder / 'generated' / 'instrumental.wav')
            self.qa_servers.append(server)
        except Exception as exc:
            QMessageBox.warning(self, 'Preview unavailable', str(exc))
            return
        webbrowser.open(url)
        self.status_label.setText('Karaoke Player opened (Line Mode, instrumental by default).')

    def read_output(self):
        if self.process is None:
            return
        data = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        if data:
            self.log.insertPlainText(data.replace('\r', '\n'))
            self.log.ensureCursorVisible()

    def process_error(self, error):
        self.status_label.setText('Process error: ' + str(error))

    def process_finished(self, exit_code, exit_status):
        self.read_output()
        if self.active_task == 'preparation':
            self.poll_preparation()
            self.prepare_timer.stop()
            self.preparation_folder = None
        song_id = self.active_song_id
        task = self.active_task
        self.active_song_id = None
        self.active_task = None
        success = exit_code == 0 and exit_status == QProcess.NormalExit
        try:
            if task == 'preparation':
                if success:
                    self.status_label.setText('Song ready! Open Karaoke Player / Lyrics QA.')
                    self.progress.setValue(100)
                    set_song_status(self.root, song_id, 'separated')
                else:
                    self.status_label.setText(f'Preparation stopped (exit {exit_code}). Review log, then click Prepare Song / Retry.')
            elif task == 'alignment':
                if success:
                    song = get_song(self.root, song_id)
                    result = read_timeline(song['folder'])
                    self.status_label.setText(
                        f"Lyrics {result['status']}: {len(result['lines'])} lines, "
                        f"{len(result['warnings'])} warnings. Use Preview Lyrics QA.")
                else:
                    self.status_label.setText(f'Alignment failed (exit {exit_code}); inspect log.')
            elif success:
                song = get_song(self.root, song_id)
                publish_stems(song['folder'])
                set_song_status(self.root, song_id, 'separated')
                self.status_label.setText('Separation complete. Preview vocals or instrumental.')
            else:
                set_song_status(self.root, song_id, 'failed')
                self.status_label.setText(f'Separation failed (exit code {exit_code}). See log.')
        except Exception as exc:
            if task == 'separation':
                set_song_status(self.root, song_id, 'failed')
            success = False
            self.status_label.setText('Output validation failed: ' + str(exc))
        self.process.deleteLater()
        self.process = None
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if success else (self.progress.value() if task == 'preparation' else 0))
        self.prepare_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.align_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.refresh()

    def cancel_analysis(self):
        if self.process is not None:
            self.status_label.setText('Stopping analysis...')
            self.process.kill()

    def preview(self, filename):
        song_id = self.selected_song_id()
        if not song_id:
            QMessageBox.warning(self, 'No selection', 'Select a song first.')
            return
        song = get_song(self.root, song_id)
        path = Path(song['folder']) / 'generated' / filename
        if not path.is_file():
            QMessageBox.warning(self, 'Not available', 'Analyze this song first.')
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()
        self.status_label.setText('Playing: ' + filename)

    def stop_preview(self):
        self.player.stop()

    def do_import(self):
        if not self.mp3:
            QMessageBox.warning(self, 'Missing MP3', 'Select an MP3 first.')
            return
        using_file = self.lyrics_tabs.currentIndex() == 1
        source = self.lyrics_file if using_file else None
        if using_file and not source:
            QMessageBox.warning(self, 'Missing lyrics', 'Select a TXT/LRC file.')
            return
        if QMessageBox.question(self, 'Confirm move',
            'The selected source files will be moved and renamed in the song library.\n'
            'They will no longer remain in their original locations. Continue?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            result = import_song(self.root, self.mp3, self.title_edit.text(), self.artist_edit.text(),
                                 self.language.currentText(), lyrics_file=source,
                                 lyrics_text=None if using_file else self.lyrics_text.toPlainText(), confirm_move=True)
        except Exception as exc:
            QMessageBox.critical(self, 'Import failed', str(exc))
            return
        self.refresh()
        message = f"Imported to:\n{result['folder']}"
        if result['retained_sources']:
            message += '\n\nCould not remove original file(s):\n' + '\n'.join(result['retained_sources'])
        QMessageBox.information(self, 'Import complete', message)
        self.mp3 = None
        self.lyrics_file = None
        self.mp3_label.setText('No MP3 selected')
        self.lyrics_label.setText('No TXT/LRC selected')
        self.lyrics_text.clear()
        self.title_edit.clear()
        self.artist_edit.clear()
        self.tabs.setCurrentIndex(0)

    def closeEvent(self, event):
        if self.process is not None:
            QMessageBox.warning(self, 'Analysis running', 'Cancel analysis before closing the app.')
            event.ignore()
            return
        self.player.stop()
        super().closeEvent(event)


def run(root):
    app = QApplication.instance() or QApplication([])
    window = SongLibrary(root)
    window.show()
    return app.exec()

    def closeEvent(self, event):
        for server in self.qa_servers:
            server.shutdown()
            server.server_close()
        super().closeEvent(event)
