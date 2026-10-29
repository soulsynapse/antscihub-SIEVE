"""sieve_player: the shared window SIEVE tools run inside. `play(...)` is the whole API.

The names in `__all__` are imported on first use, so importing one submodule (the document, say)
pulls in neither Qt nor cv2."""
import importlib
import os
import sys

_HOME = {"Frames": "graph", "Memo": "graph", "Series": "graph", "Decoder": "decoder", "probe": "pane",
         "ParamWidget": "widgets", "Trace": "widgets", "Density": "widgets", "Worker": "worker"}
__all__ = ["play", *_HOME, "theme"]


def __getattr__(name):
    if name == "theme":
        return importlib.import_module(".theme", __name__)
    if name in _HOME:
        value = getattr(importlib.import_module("." + _HOME[name], __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def play(source, path=None, title="SIEVE", tools=()):
    """Open the player. `source` is a list of tools, or the path of a saved document, which is
    opened against `tools`, the tools its nodes may name. A tool is its module, or the registry's
    entry for it, so one that failed to import is still listed. With a video `path` it loads it;
    without, it opens on whatever the document names, or empty, and never prompts."""
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
    win = PlayerWindow(source, title, tools)
    win.showMaximized()
    theme.paint_caption(win)
    if path:
        win.load(path)
    return app.exec()
