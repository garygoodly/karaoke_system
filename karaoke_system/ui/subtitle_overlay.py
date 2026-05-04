from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget

from karaoke_system.engine.timeline import LineProgress


class SubtitleOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._progress = LineProgress(line=None, active_unit_index=None, progress=0.0)
        self.font_main = QFont("Sans Serif", 24)
        self.font_reading = QFont("Sans Serif", 13)

    def set_progress(self, progress: LineProgress) -> None:
        self._progress = progress
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI paint path
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 70))
        if self._progress.line is None:
            return

        margin = 20
        baseline = self.height() - 38
        cursor_x = margin
        painter.setFont(self.font_main)
        metrics = painter.fontMetrics()

        for index, unit in enumerate(self._progress.line.units):
            text = unit.text
            width = metrics.horizontalAdvance(text + " ")
            if index < (self._progress.active_unit_index or 0):
                color = QColor(70, 220, 120)
            elif index == self._progress.active_unit_index:
                color = QColor(255, 210, 60)
            else:
                color = QColor(255, 255, 255)
            painter.setPen(color)
            painter.drawText(cursor_x, baseline, text)
            if index == self._progress.active_unit_index and self._progress.progress > 0:
                highlight_width = int(width * self._progress.progress)
                painter.fillRect(cursor_x, baseline + 4, highlight_width, 4, QColor(255, 210, 60))
            if unit.reading:
                painter.setFont(self.font_reading)
                painter.drawText(cursor_x, baseline - 28, unit.reading)
                painter.setFont(self.font_main)
            cursor_x += width + 8
