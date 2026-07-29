from __future__ import annotations

import atexit
import contextlib
import io
import os
import re
import sys
import threading


_RAW_FORMAT_LINE = re.compile(rb"retrieveFrame.*will be treated as 8UC1")

_installed = False
_lock = threading.Lock()


def silence_raw_format_warning() -> bool:
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
    with os.fdopen(read_fd, "rb", buffering=0) as stream:
        for line in stream:
            if not _RAW_FORMAT_LINE.search(line):
                try:
                    os.write(out_fd, line)
                except OSError:
                    return


def _restore(saved: int, thread: threading.Thread) -> None:
    with contextlib.suppress(ValueError):
        sys.stderr.flush()
    with contextlib.suppress(OSError):
        os.dup2(saved, 2)
    thread.join(timeout=1.0)
