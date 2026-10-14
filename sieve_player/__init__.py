"""sieve_player: the shared window SIEVE tools run inside. `play([tool, ...])` is the whole API."""
import sys

from .chain import Chain, Frames, Memo, Series
from .decoder import Decoder
from .sections import Inputs, Outputs, Section, probe
from .widgets import ParamWidget
from .worker import Worker

__all__ = ["play", "Chain", "Decoder", "Frames", "Inputs", "Memo", "Outputs", "ParamWidget", "Section", "Series", "Worker", "probe"]


def play(tools, path=None, title="SIEVE"):
    """Open the player on `tools`. With a path it loads it; without, it opens empty and never prompts."""
    from PySide6.QtWidgets import QApplication

    from .window import PlayerWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = PlayerWindow(tools, title)
    win.showMaximized()
    if path:
        win.load(path)
    return app.exec()
