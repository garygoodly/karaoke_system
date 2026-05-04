from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class PitchBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._target_midi: float | None = None
        self._live_midi: float | None = None
        self.setMinimumHeight(90)

    def set_values(self, target_midi: float | None, live_midi: float | None) -> None:
        self._target_midi = target_midi
        self._live_midi = live_midi
        self.update()

    def paintEvent(self, event) -> None:  # pragma: no cover - GUI paint path
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(20, 20, 30))
        width = self.width()
        center_y = self.height() // 2
        painter.setPen(QColor(100, 100, 100))
        painter.drawLine(20, center_y, width - 20, center_y)

        def to_y(midi: float) -> int:
            return int(center_y - (midi - 60) * 4)

        if self._target_midi is not None:
            painter.setPen(QColor(255, 210, 60))
            y = to_y(self._target_midi)
            painter.drawLine(40, y, width - 40, y)
        if self._live_midi is not None:
            painter.setBrush(QColor(70, 220, 120))
            painter.setPen(Qt.PenStyle.NoPen)
            y = to_y(self._live_midi)
            painter.drawEllipse(width // 2 - 8, y - 8, 16, 16)
