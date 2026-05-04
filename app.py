from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from karaoke_system.ui.main_window import MainWindow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop karaoke player")
    parser.add_argument("--song-dir", type=Path, required=True, help="Path to a preprocessed song folder")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    window = MainWindow(song_dir=args.song_dir)
    window.resize(1366, 820)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
