"""sieve_player: the shared window SIEVE tools run inside. `play(...)` is the whole API.

The names in `__all__` are imported on first use, so importing one submodule (the document, say)
pulls in neither Qt nor cv2."""
import importlib
import os
import sys

_HOME = {"Frames": "graph", "Memo": "graph", "Series": "graph", "Decoder": "decoder", "probe": "decoder",
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


def _hush_c_stderr():
    """Sends C-level stderr nowhere, keeping Python's: cv2's FFmpeg plugin warns on every unconverted
    frame and libavcodec on every seek, and neither reads a log level set in-process.
    SIEVE_C_STDERR=1 leaves it alone. Returns whether it was done."""
    if os.environ.get("SIEVE_C_STDERR"):
        return False
    try:
        kept = os.dup(2)
        null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null, 2)
        if sys.platform == "win32":
            import ctypes
            import msvcrt
            # the plugin links msvcrt, whose stderr is the Win32 handle when the plugin loads
            ctypes.windll.kernel32.SetStdHandle(-12, msvcrt.get_osfhandle(null))
    except OSError:
        return False
    old = sys.stderr
    sys.stderr = os.fdopen(kept, "w", encoding=getattr(old, "encoding", None) or "utf-8",
                           errors="backslashreplace", buffering=1)
    return True


def play(source, path=None, title="SIEVE", tools=()):
    """Open the player. `source` is a list of tools, or the path of a saved document, which is
    opened against `tools`, the tools its nodes may name. A tool is its module, or the registry's
    entry for it, so one that failed to import is still listed. With a video `path` it loads it;
    without, it opens on whatever the document names, or empty, and never prompts."""
    from . import decoder
    decoder.QUIET = _hush_c_stderr() or decoder.QUIET   # before any capture: the plugin keeps the stderr it loads with
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
    import faulthandler
    faulthandler.enable()   # a crash in cv2 or Qt prints every thread's Python stack instead of nothing
    from .dev import qt_trace
    qt_trace.install()
    app._watchdog = qt_trace.watchdog(app)   # a hung GUI thread prints them too
    theme.install_font(app)
    win = PlayerWindow(source, title, tools)
    win.showMaximized()
    theme.paint_caption(win)
    if path:
        win.load(path)
    return app.exec()
