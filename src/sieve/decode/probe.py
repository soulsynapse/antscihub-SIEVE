"""What this machine measured about itself, kept so it measures it once.

A probe verdict is not a preference and not a fact about SIEVE. It is a
measurement of one box — which decoder lands a random frame faster here — and
ADR-0007's whole position is that such a thing is measured where it runs rather
than declared by whoever wrote the code. Measuring it costs several real seeks
on a heavy file, which is affordable once per machine and per source shape and
is not affordable at every open.

**Keyed by machine and source shape, never by file.** The answer depends on the
GPU, the core count and the frame size, and not on which recording is in front
of it, so two files of the same shape share a verdict and a new file of a shape
already probed pays nothing. `Shape.probe_key` composes the key, in one place,
so a reader and a writer cannot spell it differently.

**A stale verdict is deleted, never migrated.** The reason to re-probe is a new
GPU or a new driver, and neither leaves a trace this file could detect. So there
is no versioning here: the file is small, rebuilding it costs one probe per
shape actually used, and a user who suspects it can delete it. What *is*
recorded beside each verdict is when it was taken and what it measured, so a
verdict that looks wrong can be argued with rather than merely distrusted.

Nothing here raises. An unreadable or unwritable cache means the probe runs
again, which costs seconds; a session that refused to open because a JSON file
was malformed would have traded the application for the optimisation.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sieve import settings

_FILE = "probes.json"


def path() -> Path:
    """The probe document, beside the user's settings."""
    return settings.directory() / _FILE


def load() -> dict[str, Any]:
    try:
        return json.loads(path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get(key: str) -> dict[str, Any] | None:
    """The verdict filed under `key`, or `None`."""
    entry = load().get(key)
    return entry if isinstance(entry, dict) else None


def store(key: str, verdict: str, measured_ms: dict[str, float]) -> None:
    """Record a verdict and what it was decided on.

    Written through a temporary file in the same directory and renamed, so a
    process killed mid-write leaves the previous document rather than a
    truncated one — the failure that turns a re-probe into an unreadable cache
    for every run after it.
    """
    document = load()
    document[key] = {
        "verdict": verdict,
        "measured_ms": measured_ms,
        "when": datetime.now(timezone.utc).isoformat(),
    }
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(target.parent),
                                             suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(document, out, indent=1)
        os.replace(temporary, target)
    except OSError:
        pass  # a verdict that could not be kept is one that gets re-measured
