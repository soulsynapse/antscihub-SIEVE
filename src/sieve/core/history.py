"""Automatic project history: whole documents, one per user-meaningful action.

The safety net that replaced the save prompt. `confirm_discard` existed because
every path that dropped the document destroyed a session's work; that reason was
transferred here rather than retired, and the prompt came out once it had been —
see `docs/completed-todo/` for the two items that did it, in that order.

Three decisions are worth stating here because the shape of this module is all
three:

**Snapshots are whole projects, on disk, beside the project file.** A
`<project>.sieve.yaml.history/` directory holds files that are themselves valid
project documents — `Project.load` reads one directly, and a directory listing
already reads as history. The alternative, keeping history inside the project
file, would make every snapshot a rewrite of the artifact the CLI reads; an
app-data directory keyed by project path would detach the moment a project is
copied.

**A snapshot's `source` is relative to the history directory, not to the project
directory.** That is what makes each file openable on its own rather than a
fragment that only means something in a parent it does not name.

**Retention keeps the newest `SNAPSHOT_LIMIT` plus every session start.** At
replicate scale a document is a few kilobytes, so fifty whole copies are noise;
the session-start marks are the "before today" restore points that a pure
newest-N rule ages out mid-session, which is the case the net is most for. The
session marks are not themselves capped, and that is a deliberate small
unboundedness: a few kilobytes per session against losing the one snapshot a
user would actually want. Revisit when outputs make documents heavy — rule 7
already names which fields would do it.

**In `core/` beside `pipeline_model.py`, because the filename is the metadata.**
Nothing stamps a time or an action into a snapshot — the document has no field
for either — so `NNNNNN-kind-slug.sieve.yaml` *is* the record, and reading a
history without SIEVE running means parsing that name. That makes the grammar a
serialization claim of the same kind as `Project.save`, and it belongs beside
it. `storage/` would be the other candidate and is the wrong one: that package
declares it never knows a project, which is what keeps `crop_writer.py`
testable without a document, and `SnapshotStore` writes projects.

This module was `gui/history.py` until it was moved on the grounds above. What
stayed in `gui/` is the half that is genuinely the window's: *when* to snapshot
(`document.py`, `main_window.py`) and how to render an age as English
(`history_dialog.age_text`). The file held both, and Qt-freedom hid it —
`docs/todo/qt-free-logic-under-gui.md` had this module in "probably stay,
interaction policy" for exactly that reason.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sieve.core.pipeline_model import PROJECT_SUFFIX, Project

#: Appended to the project file's whole name, not to its stem: a project named
#: `arena.sieve.yaml` gets `arena.sieve.yaml.history/`. Using the stem would
#: collide with a sibling actually named `arena.history`.
HISTORY_SUFFIX = ".history"

#: How many ordinary snapshots survive. Session starts are kept on top of this.
SNAPSHOT_LIMIT = 50

#: What a snapshot filename says about itself, in the two-token middle field.
SESSION_KIND = "session"
STEP_KIND = "step"

#: Used when the undo stack has no text to offer — everything undone, or a
#: command that was pushed without one.
UNTITLED = "Edit"

_FILENAME = re.compile(
    rf"^(?P<sequence>\d+)-(?P<kind>{SESSION_KIND}|{STEP_KIND})-(?P<slug>.*)"
    rf"{re.escape(PROJECT_SUFFIX)}$"
)

_UNSAFE = re.compile(r"[^A-Za-z0-9]+")

#: Longest slug written into a filename. Undo texts are short ("Set All to
#: 1000x800"); the cap is against a rename carrying a paragraph, not against
#: normal use.
_SLUG_LIMIT = 48


def slugged(text: str) -> str:
    """`text` reduced to the filename-safe form a snapshot is named with.

    Lossy in punctuation and nothing else — runs of anything unsafe collapse to
    a single underscore, which `Snapshot.text` turns back into a space. That
    round trip is exact for every undo text the application produces, and the
    point of the loss is that the directory listing stays readable on every
    filesystem rather than only on the developer's.
    """
    cleaned = _UNSAFE.sub("_", text).strip("_")[:_SLUG_LIMIT].strip("_")
    return cleaned or UNTITLED


@dataclass(frozen=True)
class Snapshot:
    """One written document, and what the store can say about it without reading it.

    Everything here comes from the filename or the directory entry, so listing a
    history costs no parsing: the restore dialog shows what an entry is and how
    old it is, and only the one the user picks is ever loaded.
    """

    path: Path
    sequence: int
    #: Whether this was the first snapshot a session wrote. Retention keeps
    #: these past the newest-N window; see the module docstring.
    session_start: bool
    #: Seconds since the epoch, from the file's mtime. The store never stamps a
    #: time into the document — a snapshot is a project, and a project has no
    #: field for when it was written.
    written_at: float

    @property
    def text(self) -> str:
        """The undo action this snapshot followed, as close as the name kept it."""
        match = _FILENAME.match(self.path.name)
        return match["slug"].replace("_", " ") if match else UNTITLED


class SnapshotStore:
    """The history directory for one project, and the retention rule over it.

    Scans on every read rather than caching a list. The directory is tens of
    small files, the cost is a `listdir`, and the alternative is an in-memory
    index that goes wrong the first time two windows have the same project open
    — which is a state nothing prevents.
    """

    def __init__(self, directory: Path, *, limit: int = SNAPSHOT_LIMIT) -> None:
        self._directory = directory
        self._limit = max(limit, 1)
        self._written = 0

    @property
    def directory(self) -> Path:
        """Where snapshots are written. May not exist until the first record."""
        return self._directory

    def entries(self) -> list[Snapshot]:
        """Every snapshot in the directory, oldest first.

        Files that do not parse are ignored rather than reported: this directory
        sits in a user's project folder and anything may end up in it, and a
        history that refuses to list because somebody dropped a note in it would
        be a safety net that fails exactly when it is reached for.
        """
        if not self._directory.is_dir():
            return []
        found: list[Snapshot] = []
        for path in self._directory.iterdir():
            match = _FILENAME.match(path.name)
            if match is None or not path.is_file():
                continue
            found.append(
                Snapshot(
                    path=path,
                    sequence=int(match["sequence"]),
                    session_start=match["kind"] == SESSION_KIND,
                    written_at=path.stat().st_mtime,
                )
            )
        return sorted(found, key=lambda snapshot: snapshot.sequence)

    def record(self, project: Project, text: str) -> Snapshot:
        """Write `project` as the next snapshot, then prune.

        The first call of a store's life is a session start, whatever else is
        already in the directory. That is the whole session-boundary mechanism:
        nothing has to be told when a session begins, because a store is
        constructed exactly once per project a session opens.

        Raises:
            OSError: if the directory cannot be made or the file cannot be
                written. Deliberately not swallowed — a history that has
                silently stopped being kept is rule 6's failure, and the caller
                is the only thing that can say so where a user will see it.
        """
        self._directory.mkdir(parents=True, exist_ok=True)
        existing = self.entries()
        sequence = existing[-1].sequence + 1 if existing else 1
        session_start = self._written == 0
        kind = SESSION_KIND if session_start else STEP_KIND
        path = self._directory / f"{sequence:06d}-{kind}-{slugged(text)}{PROJECT_SUFFIX}"
        project.save(path)
        self._written += 1
        self._prune()
        return Snapshot(
            path=path,
            sequence=sequence,
            session_start=session_start,
            written_at=path.stat().st_mtime,
        )

    def _prune(self) -> None:
        """Drop everything outside the newest window that is not a session start.

        A file that will not delete is left alone: it is somebody else's lock or
        somebody else's permissions, and failing a snapshot because an old one
        could not be tidied would turn a housekeeping problem into a lost
        document.
        """
        entries = self.entries()
        ordinary = [snapshot for snapshot in entries if not snapshot.session_start]
        doomed = set(ordinary[: max(len(ordinary) - self._limit, 0)])
        for snapshot in doomed:
            try:
                snapshot.path.unlink()
            except OSError:
                continue


def history_directory(project_path: Path) -> Path:
    """Where the history for the project file at `project_path` lives."""
    return project_path.with_name(project_path.name + HISTORY_SUFFIX)
