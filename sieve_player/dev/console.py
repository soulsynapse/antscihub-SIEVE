"""Where the player's diagnostics go once the console may be gone: stderr teed into a log, the
previous launch's kept beside it, C-level stderr sent nowhere so cv2's plugin stops warning on
every frame, and faulthandler, the Qt warning handler and the watchdog writing to the same place.
`start()` before anything imports cv2, since the plugin keeps the stderr handle it loads with; `watch(app)`
once the QApplication exists."""
import faulthandler
import os
import sys
import time

LOG_ENV = "SIEVE_LOG"       # the log's path; unset: stderr.log under store.app_folder(); 0: no log


class _Tee:
    """A text stream writing to every stream given; the first answers for the descriptor and
    encoding. A stream that will not take a write is passed over, so a full disk or a console that
    has gone never turns a traceback being printed into a second exception."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except (OSError, ValueError):
                pass
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
    from ..store import app_folder
    return os.path.join(app_folder(), "stderr.log")


def log_stderr(path):
    """Opens the log at `path`, the previous one kept beside it as .prev.log, and tees sys.stderr
    into it; while another player holds `path` open, a log named with this process's id beside it.
    Returns the log, or None when it could not be opened, stderr then left alone."""
    stem = os.path.splitext(path)[0]
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            if os.path.exists(path):
                os.replace(path, stem + ".prev.log")
        except PermissionError:
            path = f"{stem}.{os.getpid()}.log"
        log = open(path, "w", encoding="utf-8", errors="backslashreplace", buffering=1)
    except OSError:
        return None
    sys.stderr = _Tee(sys.stderr, log)
    return log


def hush_c_stderr():
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


def start():
    """Hushes C-level stderr, telling the decoder so, and opens the log; the first line on stderr
    carries the launch time and the log's name, or that it would not open. Returns the log, or
    None when there is none."""
    from .. import decoder
    decoder.QUIET = hush_c_stderr() or decoder.QUIET
    log = None if log_path() is None else log_stderr(log_path())
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if log is not None:
        print(f"SIEVE {stamp}: stderr also in {log.name}", file=sys.stderr)
    elif log_path() is not None:
        print(f"SIEVE {stamp}: could not open the log at {log_path()}; stderr only", file=sys.stderr)
    return log


def watch(app, log):
    """A crash in cv2 or Qt prints every thread's Python stack, a Qt warning its origin, and a hung
    GUI thread its stacks, all to the log when there is one, since faulthandler takes one
    descriptor and a console may already be gone. The watchdog timer is returned for the caller
    to hold."""
    from . import qt_trace
    faulthandler.enable(file=log or sys.stderr)
    qt_trace.install()
    return qt_trace.watchdog(app, file=log or sys.stderr)
