"""sieve_player: the shared window SIEVE tools run inside. `play([tool, ...])` is the whole API."""
import os
import sys

from .chain import Chain, Frames, Memo, Series
from .decoder import Decoder
from .sections import Inputs, Outputs, probe
from .widgets import ParamWidget, Trace
from .worker import Worker

__all__ = ["play", "Chain", "Decoder", "Frames", "Inputs", "Memo", "Outputs", "ParamWidget", "Series", "Trace",
           "Worker", "probe", "theme"]


def play(tools, path=None, title="SIEVE"):
    """Open the player on `tools`. With a path it loads it; without, it opens empty and never prompts."""
    if sys.platform == "win32":
        # DirectWrite ignores the hinting preference and draws ClearType colour fringes on a dark
        # ground; FreeType honours full hinting and renders grayscale. Must be set before the app.
        os.environ.setdefault("QT_QPA_PLATFORM", "windows:fontengine=freetype")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from . import theme
    from .window import PlayerWindow

    app = QApplication.instance()
    if app is None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.Round)  # 125% becomes 100%, 150% becomes 200%: no fractional blur
        app = QApplication(sys.argv)
    theme.install_font(app)
    win = PlayerWindow(tools, title)
    win.showMaximized()
    theme.paint_caption(win)
    if path:
        win.load(path)
    return app.exec()
