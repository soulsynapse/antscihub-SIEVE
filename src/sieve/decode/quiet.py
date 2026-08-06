"""Drop one known-benign OpenCV line from stderr, and pass everything else on.

`reader.py`'s luma path sets `CAP_PROP_CONVERT_RGB = 0`, and this build's FFmpeg
backend answers every single `retrieveFrame` with

    [ WARN:0@87.958] global cap_ffmpeg_impl.hpp:1889 retrieveFrame
    Unknown/unsupported picture format: yuv420p, will be treated as 8UC1.

That fallback is exactly what the luma path asks for, so the line is expected and
carries nothing — but it is emitted *per frame*, and a 70 s window render at
59.94 fps is 4200 of them. The console stops being readable, which means the next
warning that does matter arrives invisible.

**Why this is fd surgery and not a log level.** Three cheaper routes were
measured and none of them work in this build:

* `cv2.utils.logging.setLogLevel(LOG_LEVEL_ERROR)` and `LOG_LEVEL_SILENT`, set
  before the capture and after it — the message goes out regardless.
* `OPENCV_LOG_LEVEL=ERROR` in `os.environ` before `import cv2`, and the same
  through `kernel32.SetEnvironmentVariableW` — neither reaches the plugin, which
  reads its configuration from an environment block Python's `putenv` does not
  write. The variable *does* work when set before the process starts, which is
  not something a library can arrange for its own process.
* A different backend: MSMF and DSHOW do not open files at all here, so FFMPEG
  is not a choice.

What is left is the stream. This filters it by line rather than muting it,
because muting stderr for the duration of a render would take a traceback with
it — and the whole reason to care about the noise is to keep real messages
visible.

**Why the application calls this and the reader does not.** Redirecting file
descriptor 2 is process-global and irreversible in practice, which makes it a
decision belonging to whatever owns the process — the same division
`mutual/shares.py` draws between declaring a share of the machine and applying
one. The declaration can live anywhere a consumer can reach; the act belongs to
whoever owns the process, and here the act is the whole of it. A reader that
installed this on construction would also do it inside pytest, where fd 2
belongs to the capture fixture and taking it is how a test suite starts losing
output it was asserting on.
"""

from __future__ import annotations

import atexit
import contextlib
import io
import os
import re
import sys
import threading

#: The one line this drops. Anchored on the two fixed parts — the function that
#: emits it and the fallback it announces — rather than on the whole message,
#: because the prefix carries a thread id and a timestamp that vary per line.
#: Narrow on purpose: a different unsupported format, or a warning from anywhere
#: else in videoio, is something to see.
_RAW_FORMAT_LINE = re.compile(rb"retrieveFrame.*will be treated as 8UC1")

_installed = False
_lock = threading.Lock()


def silence_raw_format_warning() -> bool:
    """Start filtering `_RAW_FORMAT_LINE` out of this process's stderr.

    Idempotent, and safe to call before anything has been decoded. Returns
    whether the filter is now running — `False` means the platform refused the
    redirection, which is not an error worth raising over: the outcome is a noisy
    console, not a wrong result, and a decode path that failed to start because
    a log line could not be hidden would be the worse trade.

    Call once, from an application entry point, before the first luma read.
    """
    global _installed
    with _lock:
        if _installed:
            return True
        try:
            saved = os.dup(2)
            read_fd, write_fd = os.pipe()
            os.dup2(write_fd, 2)
            os.close(write_fd)
        except OSError:
            return False

        # fd 2 is a pipe now, and Python picks its buffering from what the
        # stream *is*: a console gets line buffering, a pipe gets 8 KB blocks.
        # Left alone, every `print(..., file=sys.stderr)` and every warning would
        # sit unseen until something filled the block — a far worse regression
        # than the noise this exists to remove, and one that would look like the
        # filter eating output rather than delaying it.
        # Replaced rather than reconfigured. `reconfigure` is a `TextIOWrapper`
        # method and `sys.stderr` is only promised to be a `TextIO`, so reaching
        # for it means narrowing a generic that has nothing to do with the
        # buffering being fixed. Building the wrapper says the same thing with
        # the type known: a fresh text layer over the same descriptor, flushed
        # from the old one first so nothing in flight is dropped.
        previous = sys.stderr
        with contextlib.suppress(ValueError):
            previous.flush()
        sys.stderr = io.TextIOWrapper(
            io.FileIO(2, "wb", closefd=False),
            encoding=previous.encoding or "utf-8",
            errors="backslashreplace",
            line_buffering=True,
        )

        thread = threading.Thread(
            target=_pump,
            args=(read_fd, saved),
            name="sieve-stderr-filter",
            daemon=True,
        )
        thread.start()
        atexit.register(_restore, saved, thread)
        _installed = True
        return True


def _pump(read_fd: int, out_fd: int) -> None:
    """Forward stderr line by line, dropping the one known line.

    Binary and unbuffered: this sits underneath Python's `sys.stderr` as well as
    OpenCV's C++ writes, and decoding text here would mean guessing an encoding
    for bytes that are not ours. `readline` on a pipe returns as soon as a line
    is available, so nothing is held back waiting for a buffer to fill.
    """
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        for line in stream:
            if not _RAW_FORMAT_LINE.search(line):
                try:
                    os.write(out_fd, line)
                except OSError:
                    return


def _restore(saved: int, thread: threading.Thread) -> None:
    """Put the real stderr back, and let the pump drain before the process goes.

    The order is the whole of it. Flush first, so anything Python is still
    holding enters the pipe while the pump is alive. Then `dup2` over fd 2,
    which closes the last write end and is what lets the pump see end of stream
    at all — without it the thread blocks in `readline` forever and everything
    written since the last newline is lost with it.

    Then join, briefly. The pump is a daemon, so interpreter shutdown would
    otherwise kill it mid-drain and swallow exactly the last few lines — which
    on a crash are the ones worth having. The timeout is the concession: a wedged
    pump delays exit by a second rather than hanging it.
    """
    with contextlib.suppress(ValueError):
        sys.stderr.flush()
    with contextlib.suppress(OSError):
        os.dup2(saved, 2)
    thread.join(timeout=1.0)
