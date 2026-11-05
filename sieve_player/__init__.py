"""sieve_player: the shared window SIEVE tools run inside. `play(...)` is the whole API.

The names in `__all__` are imported on first use, so importing one submodule (the document, say)
pulls in neither Qt nor cv2. `play` tees stderr into the log `log_path()` names, so a traceback, a
Qt warning or a crash's stacks outlive the console."""
import importlib
import os
import sys
import tempfile

_HOME = {"Frames": "graph", "Memo": "graph", "Series": "graph", "Decoder": "decoder", "probe": "decoder",
         "ParamWidget": "widgets", "Trace": "widgets", "Density": "widgets", "Worker": "worker"}
__all__ = ["play", *_HOME, "theme"]
LOG_ENV = "SIEVE_LOG"       # the log's path; unset: SIEVE/stderr.log under LOCALAPPDATA or the temp dir; 0: no log


class _Tee:
    """A text stream writing to every stream given; the first answers for the descriptor and encoding."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()

    def fileno(self):
        return self.streams[0].fileno()

    def isatty(self):
        return self.streams[0].isatty()

    @property
    def encoding(self):
        return self.streams[0].encoding


def log_path():
    """Where stderr is also written, as LOG_ENV says; None for nowhere."""
    want = os.environ.get(LOG_ENV)
    if want == "0":
        return None
    if want:
        return want
    return os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "SIEVE", "stderr.log")


def log_stderr(path):
    """Opens the log at `path`, the previous one kept beside it as .prev.log, and tees sys.stderr
    into it. Returns the log, or None when it could not be opened, stderr then left alone."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if os.path.exists(path):
            os.replace(path, os.path.splitext(path)[0] + ".prev.log")
        log = open(path, "w", encoding="utf-8", errors="backslashreplace", buffering=1)
    except OSError:
        return None
    sys.stderr = _Tee(sys.stderr, log)
    return log


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
    log = None if log_path() is None else log_stderr(log_path())
    if log is not None:
        print(f"stderr also in {log.name}", file=sys.stderr)
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
    # a crash in cv2 or Qt prints every thread's Python stack instead of nothing; faulthandler writes
    # to one descriptor, so the log's when there is one, where a console may already be gone
    faulthandler.enable(file=log or sys.stderr)
    from .dev import qt_trace
    qt_trace.install()
    app._watchdog = qt_trace.watchdog(app, file=log or sys.stderr)   # a hung GUI thread prints them too
    theme.install_font(app)
    win = PlayerWindow(source, title, tools)
    win.showMaximized()
    theme.paint_caption(win)
    if path:
        win.load(path)
    return app.exec()
