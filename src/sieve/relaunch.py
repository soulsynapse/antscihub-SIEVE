"""Start SIEVE over: the same command, in place of the process running it.

This is the tuning loop's key applied to the application itself. Reloading by
re-importing would leave every object built from the old modules still standing
— the window, its panes, the views inside them — and what the user would then be
looking at is a mix of two versions of the code with no way to tell which one
answered. Replacing the process is the only reload that cannot be partial.

Nothing is handed to the new process, because there is nothing to hand it yet: a
project is not opened, so the window has no state a restart loses. What survives
a relaunch survives it the same way it survives a reboot — the palette comes
back because it is in the settings document, not because this file carried it —
and that is the arrangement to keep reaching for. This is the file where "reload
keeps X" would be written for an X that is genuinely of *this run* and has
nowhere on disk to be.

The command is rebuilt rather than guessed, and there are two of them to rebuild
because the app has two entry points — a console script, which is an executable
that already knows how to start itself, and a file handed to the interpreter,
which is only a script and needs the same interpreter and the same flags in
front of it again. `sys.orig_argv` is what holds those flags; `sys.argv` has
already had them taken off. Either way the interpreter is the one `uv run`
selected, so the new process skips the launcher and not the environment.

On Windows `execv` cannot overwrite a process, so the shell that launched the
old one sees it exit and returns to a prompt while the new window stands. The
app reloads either way; the parent shell is not the app.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def relaunch() -> None:
    """Replace this process with a fresh run of the same command."""
    # The process is about to be gone without unwinding — no atexit, no Qt
    # teardown — so flush what Python has buffered while it still can.
    sys.stdout.flush()
    sys.stderr.flush()
    launcher, command = _command()
    os.execv(launcher, command)


def _command() -> tuple[str, list[str]]:
    """The executable to run and the argument list to run it with."""
    entry = Path(sys.argv[0])
    if entry.suffix.lower() == ".exe":  # `uv run sieve`
        return str(entry), sys.argv
    # `uv run SIEVE.py`, or `-m sieve`: everything after the interpreter, which
    # is `-m sieve` itself in that case and the script path in the other.
    return sys.executable, [sys.executable, *sys.orig_argv[1:]]
