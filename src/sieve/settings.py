"""What the user has set, kept where the next run will find it.

Held above `gui` because a preference is not a drawing decision. The palette is
the only one written so far, but the sections beside it in the preferences card
— where projects are kept, how much footage is decoded ahead, what a new step
starts at — are settings of the application and not of its view, and a document
owned by the GUI would have to be imported back out of it the first time a
decoder asked how far to read ahead. Nothing here imports Qt for the same
reason.

It is one flat JSON object, keyed by strings, at `path()`. Flat rather than
nested: a key is what a setting is *called*, and a tree would make every reader
agree on a grouping as well as on a name. JSON rather than a binary store or
Qt's own `QSettings` because the file is meant to be openable — a user who
wants to know what SIEVE remembers about them can read it, and one who wants to
undo a setting can delete the line rather than hunting for the control that
wrote it. On Windows `QSettings` writes to the registry, which is neither.

Nothing in this module raises. A settings document is a convenience, and an
application that refused to start because a JSON file had a stray comma would
be trading the whole product for the convenience — so an unreadable document
reads as an empty one, a failed write is reported and dropped, and the run
carries on with defaults. What is lost in that case is the memory of a
preference, which is what the user had before this file existed.

The write is a whole-document replace on every change, and that is affordable
because the document is a handful of keys: there is no format here where a
partial update would be cheaper than rewriting it. It goes through a temporary
file in the same directory and `os.replace`, so a process killed mid-write
leaves the previous document intact rather than a truncated one — the failure
that would otherwise turn a lost preference into an unreadable file for every
run after it.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

#: The directory's name, capitalised on the platforms whose convention is a
#: display name and lowercase where the convention is a dotfile-ish path.
_NAME = "SIEVE"
_FILE = "settings.json"

#: Names a document to use instead of the per-user one. Set by a run that must
#: not touch the person at the keyboard — a check that launches SIEVE, clicks a
#: palette and closes it writes that palette exactly as a real click would. An
#: environment variable rather than an argument, because the writers are
#: `palette` and `metrics`, reached through `stored`/`remember` from wherever a
#: view happens to be built.
_OVERRIDE = "SIEVE_SETTINGS"

#: The document as last read or written, or `None` before it has been read.
#: Held so that reading a preference is not a file open: `stored()` is called
#: during startup and can be called from a view being built.
_document: dict[str, Any] | None = None


def path() -> Path:
    """The settings document, whether or not it exists yet.

    Per-user and outside the project tree, because a preference follows the
    person and not the footage: two projects opened by the same user get the
    same palette, and a project copied to a colleague does not carry it.

    `SIEVE_SETTINGS` names another document and is taken as given — a full path
    to a file, not a directory to put `settings.json` in, so a run can point at
    a name of its choosing inside a temporary directory it already owns. An
    empty or unset variable is the per-user document, so clearing it is how a
    shell gets back to being a person rather than a test.
    """
    override = os.environ.get(_OVERRIDE)
    if override:
        return Path(override)
    return _directory() / _FILE


def stored(key: str, default: Any = None) -> Any:
    """What is remembered under `key`, or `default` if nothing is.

    The value is returned as JSON left it — a string, a number, a bool. What a
    stored value *means* is the caller's, and a caller that stores a name has
    to survive being handed a name that no longer exists: the document outlives
    the run that wrote it, and a palette can be renamed between the two.
    """
    return _read().get(key, default)


def remember(key: str, value: Any) -> None:
    """Keep `value` under `key`, for the next run and every one after it.

    A value equal to the one already stored writes nothing. That is what keeps
    startup off the disk: the palette in use is set on the way up from what the
    document says, and the setter records it again, which would be a write on
    every launch for a preference nobody touched.
    """
    document = _read()
    if key in document and document[key] == value:
        return
    document[key] = value
    _write(document)


def forget(key: str) -> None:
    """Stop remembering `key`, so the next run comes up at its default."""
    document = _read()
    if key not in document:
        return
    del document[key]
    _write(document)


def _directory() -> Path:
    """Where this platform keeps a user's application settings.

    Each branch is that platform's own convention rather than one path with the
    separators swapped: a dotfile under `~` on Windows is invisible to the user
    and a file under `%APPDATA%` on Linux is a directory called `AppData` in
    their home. The environment variables are read rather than assumed, since
    both platforms let them be moved — a roaming profile, or an `XDG_CONFIG_HOME`
    pointing into a dotfile repo — and the fallback is only for the case where
    the variable is unset.
    """
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
    """The document, read once and held after that.

    Read once and not per call, so the file on disk is not authority over a
    running process: a settings file edited by hand while SIEVE is open does
    not half-arrive, one key at a time, as whichever views happen to ask next.
    It takes effect on the next run, which is when the rest of it does too.

    Anything that is not an object of keys — a list, a number, a file of
    something else entirely that happens to sit at this path — reads as empty
    rather than as itself, because every reader here does a key lookup and a
    `TypeError` out of `stored()` is a crash in whatever was starting up.
    """
    global _document
    if _document is not None:
        return _document
    _document = {}
    try:
        text = path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return _document  # A first run, which is not a problem to report.
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
    """Put the whole document on disk, or say why it could not be.

    The temporary file is made in the destination's own directory rather than
    the system's temp: `os.replace` is only atomic within a filesystem, and the
    two are routinely on different ones. It is left behind on a failed replace
    — a stray `.tmp` beside the settings is a smaller problem than a partial
    settings file, and the next successful write does not need it gone.
    """
    destination = path()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(
            dir=destination.parent, prefix=f"{_FILE}.", suffix=".tmp"
        )
        # `newline=""` so the JSON is written with the "\n" it is built with:
        # text mode on Windows would translate them, and the document is read
        # back by a JSON parser that does not care either way but by people who
        # may open it in something that does.
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as file:
            json.dump(document, file, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(temporary, destination)
    except OSError as error:
        _complain(f"could not be written ({error}); this change lasts the session")


def _complain(trouble: str) -> None:
    """Say what went wrong with the document, on stderr, and carry on.

    Not a dialog and not an exception: the failures here are all ones the user
    did not ask about — they clicked a palette — and the cost of every one of
    them is that a preference is not remembered. The path is named because it
    is the only thing they could act on.
    """
    print(f"sieve: settings file {path()} {trouble}", file=sys.stderr)
