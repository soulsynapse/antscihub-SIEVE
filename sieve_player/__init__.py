"""sieve_player: the shared window SIEVE tools run inside. `play([tool, ...])` is the whole API."""
import os
import sys

from .chain import Chain, Frames, Memo, Series
from .decoder import Decoder
from .widgets import ParamWidget
from .worker import Worker

__all__ = ["play", "Chain", "Decoder", "Frames", "Memo", "ParamWidget", "Series", "Worker"]


def play(tools, path=None, title="SIEVE"):
    from PySide6.QtWidgets import QApplication, QFileDialog

    from .window import PlayerWindow

    app = QApplication.instance() or QApplication(sys.argv)
    if path is None:
        path, _ = QFileDialog.getOpenFileName(None, "Open video", "", "Video (*.mp4 *.MP4 *.avi *.mov *.mkv);;All (*)")
        if not path:
            return 0
    decoder = Decoder(path)
    chain = Chain(decoder, tools)
    worker = Worker(chain)
    win = PlayerWindow(decoder, chain, worker, f"{title} — {os.path.basename(path)}")
    worker.start()
    win.showMaximized()
    return app.exec()
