"""Owns what's played. Nothing outside this module opens a ``QMediaPlayer``.

``open`` does its own normalizing and checking — a caller may hand it a
relative path, a ``str``, or a typo, and it must either play or fail loudly.
Silently doing nothing (the old behavior, on a bad path) is what already
cost one round of "why isn't the video showing" — the fix belongs here,
not in every caller.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget


class VideoPlayer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._video_widget = QVideoWidget(self)
        self._player = QMediaPlayer(self)
        self._player.setVideoOutput(self._video_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._video_widget)

    def open(self, path: str | os.PathLike) -> None:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"no such video file: {resolved}")
        self._player.setSource(QUrl.fromLocalFile(str(resolved)))
        self._player.play()

    def toggle_play_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()


if __name__ == "__main__":
    # Standalone smoke test: this widget must play something on its own,
    # with no app.py, no layout.py, no pipeline in the loop.
    import sys

    from PySide6.QtWidgets import QApplication

    def _find_repo_root(start: Path) -> Path:
        # Walks up to the marker (pyproject.toml) instead of counting
        # parents — a fixed index breaks the moment this file moves depth.
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        raise RuntimeError(f"no pyproject.toml found above {start}")

    video_path = _find_repo_root(Path(__file__).resolve()) / "video-test" / "rep3_intermittent_crop.MP4"

    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.open(video_path)
    player.resize(640, 480)
    player.show()
    sys.exit(app.exec())
