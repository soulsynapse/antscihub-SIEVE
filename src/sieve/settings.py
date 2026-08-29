"""Flat JSON preferences at ``path()``, read once per run.

Nothing here raises or imports Qt.  An unreadable file reads as empty;
a failed write is reported on stderr and dropped.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_NAME = "SIEVE"
_FILE = "settings.json"

# Set by a run that must not touch the person's own settings — a check that
# launches SIEVE and clicks a palette would otherwise silently rewrite theirs.
_OVERRIDE = "SIEVE_SETTINGS"

_document: dict[str, Any] | None = None


def path() -> Path:
    """The settings file.  ``SIEVE_SETTINGS`` overrides the per-user path —
    a full path to a file, not a directory to put one in."""
    override = os.environ.get(_OVERRIDE)
    if override:
        return Path(override)
    return _directory() / _FILE


def stored(key: str, default: Any = None) -> Any:
    """What is remembered under *key*, or *default*."""
    return _read().get(key, default)


def remember(key: str, value: Any) -> None:
    """Persist *value* under *key*.  No-op if already equal."""
    document = _read()
    if key in document and document[key] == value:
        return
    document[key] = value
    _write(document)


def forget(key: str) -> None:
    """Remove *key* so the next run comes up at its default."""
    document = _read()
    if key not in document:
        return
    del document[key]
    _write(document)


def _directory() -> Path:
    """Platform-conventional per-user config directory."""
    if sys.platform == "win32":
        roaming = os.environ.get("APPDATA")
        root = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
        return root / _NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / _NAME
    config = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config) if config else Path.home() / ".config"
    return root / _NAME.lower()


def _read() -> dict[str, Any]:
    """Read once, cache for the process lifetime."""
    global _document
    if _document is not None:
        return _document
    _document = {}
    try:
        text = path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return _document
    except OSError as error:
        _complain(f"could not be read ({error})")
        return _document
    try:
        loaded = json.loads(text)
    except ValueError as error:
        _complain(f"is not readable JSON ({error}); settings are at defaults")
        return _document
    if isinstance(loaded, dict):
        _document = loaded
    else:
        _complain("does not hold a set of settings; settings are at defaults")
    return _document


def _write(document: dict[str, Any]) -> None:
    """Atomic whole-file replace via temp + ``os.replace``.

    The temp file must be in the destination's own directory — ``os.replace``
    is only atomic within a filesystem, and the system temp is routinely on
    another one.
    """
    destination = path()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(
            dir=destination.parent, prefix=f"{_FILE}.", suffix=".tmp"
        )
        # newline="" — text mode on Windows would translate the "\n"s.
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as file:
            json.dump(document, file, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(temporary, destination)
    except OSError as error:
        _complain(f"could not be written ({error}); this change lasts the session")


def _complain(trouble: str) -> None:
    print(f"sieve: settings file {path()} {trouble}", file=sys.stderr)
