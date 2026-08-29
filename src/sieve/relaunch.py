"""Replace the running process with a fresh run of the same command.

On Windows ``execv`` cannot overwrite a process: the launching shell sees the
old one exit and returns to a prompt while the new window stands. That is the
relaunch working, not failing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def relaunch() -> None:
    # The process is replaced without unwinding — no atexit, no Qt teardown —
    # so flush what Python has buffered while it still can.
    sys.stdout.flush()
    sys.stderr.flush()
    launcher, command = _command()
    os.execv(launcher, command)


def _command() -> tuple[str, list[str]]:
    """The executable and argv for a relaunch."""
    entry = Path(sys.argv[0])
    if entry.suffix.lower() == ".exe":  # `uv run sieve`: a self-starting console script
        return str(entry), sys.argv
    # `uv run SIEVE.py` or `-m sieve`: a script needs the interpreter and its
    # flags back in front — `sys.orig_argv` still has them, `sys.argv` does not.
    return sys.executable, [sys.executable, *sys.orig_argv[1:]]
