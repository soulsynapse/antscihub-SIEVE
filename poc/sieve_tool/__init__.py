"""The player a tool's standalone.py imports. See poc/PLAN.md for the rules."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from PySide6.QtWidgets import QApplication, QFileDialog

from .chain import Chain, Frames, Series
from .player import PlayerWindow
from .source import VideoSource

__all__ = ["Chain", "Frames", "Series", "PlayerWindow", "VideoSource", "play"]


def play(tools: list[ModuleType], video: str | Path | None = None) -> int:
    """Open `video` (or ask for one) and run `tools` as a chain in the player."""
    app = QApplication.instance() or QApplication(sys.argv)
    if video is None:
        video = sys.argv[1] if len(sys.argv) > 1 else QFileDialog.getOpenFileName(None, "Video")[0]
    if not video:
        return 1
    chain = Chain(VideoSource(video), tools)
    window = PlayerWindow(chain)
    window.show()
    return app.exec()
