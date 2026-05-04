from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel


class ScorePanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QGridLayout(self)
        self.current_label = QLabel("Current: 0.0")
        self.average_label = QLabel("Average: 0.0")
        self.target_label = QLabel("Target: --")
        self.live_label = QLabel("Live: --")
        layout.addWidget(self.current_label, 0, 0)
        layout.addWidget(self.average_label, 0, 1)
        layout.addWidget(self.target_label, 1, 0)
        layout.addWidget(self.live_label, 1, 1)

    def update_scores(self, current: float, average: float, target_text: str, live_text: str) -> None:
        self.current_label.setText(f"Current: {current:5.1f}")
        self.average_label.setText(f"Average: {average:5.1f}")
        self.target_label.setText(f"Target: {target_text}")
        self.live_label.setText(f"Live: {live_text}")
