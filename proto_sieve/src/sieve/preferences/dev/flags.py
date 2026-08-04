"""Secret: which dev-only toggles exist and how they're read.

Not what a toggle does — call sites own that. Nothing outside this file
reads ``os.environ`` for a feature toggle; a new dev switch means a new
name here, not a stray ``os.environ.get()`` at the call site.
"""

from __future__ import annotations

import os


def _env_int(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return int(value)


# Which screen the main window opens on, by index into QGuiApplication's
# screen list. Defaults on for this dev sitting so it fires without having
# to set the env var every launch — set SIEVE_DEV_MONITOR=0 (or unset and
# change the default below) once the second-monitor workflow is over.
MONITOR_INDEX = _env_int("SIEVE_DEV_MONITOR")
if MONITOR_INDEX is None:
    MONITOR_INDEX = 1
