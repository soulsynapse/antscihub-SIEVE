"""Replace the running process with a fresh run of the same command."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def relaunch() -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    launcher, command = _command()
    os.execv(launcher, command)


def _command() -> tuple[str, list[str]]:
    """The executable and argv for a relaunch."""
    entry = Path(sys.argv[0])
    if entry.suffix.lower() == ".exe":
        return str(entry), sys.argv
    return sys.executable, [sys.executable, *sys.orig_argv[1:]]
