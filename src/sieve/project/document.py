"""What a project knows about itself, written where the project is.

One JSON document at `<folder>/.sieve/project.json`. It is small on purpose:
what a project *is* is a folder somebody pointed at, and everything here either
cannot be recovered by looking (an identity, a name somebody typed) or would be
expensive to recover (which sources were found, and what they were when they
were found).

**A project has an identity that is not its path.** Folders get renamed and
moved, and a library keyed by path would show the same project twice and lose
track of which one had been opened. So the document carries an id, generated
once, and the library reconciles against it.

**Sources are recorded with a fingerprint, not just a name.** Size and
modification time, the same discipline the frame table's sidecar uses, so a file
replaced between sessions is noticed rather than served from a stale table. What
is *not* recorded is anything that costs a pass over the file: a frame count
needs a demux, and the count a container volunteers is the one of the three that
is never right (ADR-0004). A project that quoted it would be putting the wrong
number on a card.

**The derived location is a field rather than a rule.** It defaults to `.sieve/`
inside the project, so a project is one directory that can be copied to another
machine with its expensive work intact — building a proxy for an hour of 5.3K is
minutes of ffmpeg, and re-paying that on a colleague's laptop is a real cost. A
project on read-only or shared media names somewhere else instead, and the code
has one path rather than two modes. The answer to "where did my proxy go" is
always "it says in the document."

Nothing here raises. A document that cannot be read is a project that has not
been opened before, which is the same situation as a folder nobody has pointed
at yet; a write that fails is reported by returning `False` and the session
carries on, because losing the record of a name is not worth refusing to work.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

#: Where the document and, by default, everything derived from the project
#: lives. A dot-directory so a folder of footage still looks like a folder of
#: footage to whoever opens it in a file browser.
SIEVE_DIR = ".sieve"
_FILE = "project.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SourceRecord:
    """One footage file as the project last saw it."""

    #: relative to the project folder, in POSIX form, so a document written on
    #: one platform is readable on another
    path: str
    bytes: int
    mtime_ns: int
    #: header facts, cheap to read and worth keeping so a card can be drawn
    #: without opening every file again
    codec: str = ""
    width: int = 0
    height: int = 0
    #: seconds, from the container. Duration is what a card shows, because the
    #: honest frame count costs a demux and the volunteered one is wrong.
    duration_s: float = 0.0

    def matches(self, root: Path) -> bool:
        """Is the file still what it was when this was written?"""
        try:
            stat = (root / self.path).stat()
        except OSError:
            return False
        return stat.st_size == self.bytes and stat.st_mtime_ns == self.mtime_ns


@dataclass
class Document:
    """A project's own record of itself."""

    project_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    created: str = field(default_factory=now)
    opened: str = field(default_factory=now)
    #: where derived work goes, relative to the folder unless absolute
    derived: str = SIEVE_DIR + "/derived"
    #: paths detection must not look in, relative to the folder in POSIX
    #: form. A folder of footage often holds a folder of exports, and
    #: SIEVE cannot tell somebody else’s rendered clips from the footage
    #: they were rendered from — so it is asked once and remembered here,
    #: where the answer travels with the project.
    excluded: list[str] = field(default_factory=list)
    sources: list[SourceRecord] = field(default_factory=list)
    #: files that looked like video and would not open, with their
    #: fingerprints. Kept for the same reason the sources are: without
    #: them, a file that fails to open is retried on every scan, and a
    #: folder that has been worked in accumulates them — one such folder
    #: in this tree holds fifty-one. A skipped file whose fingerprint has
    #: moved is tried again, because a half-copied file that finished
    #: copying is footage now.
    skipped: list[SourceRecord] = field(default_factory=list)

    # ── locating ─────────────────────────────────────────────────────────
    @staticmethod
    def path_in(folder: Path) -> Path:
        return folder / SIEVE_DIR / _FILE

    def derived_in(self, folder: Path) -> Path:
        """Where this project's derived work lives, resolved against `folder`.

        Absolute stays absolute — that is the escape hatch for read-only or
        shared media — and relative is inside the project, which is what makes
        the ordinary case copyable.
        """
        written = Path(self.derived)
        return written if written.is_absolute() else folder / written

    # ── reading and writing ──────────────────────────────────────────────
    @classmethod
    def load(cls, folder: Path) -> "Document | None":
        """The document in `folder`, or `None` if there is not one to read."""
        try:
            raw = json.loads(cls.path_in(folder).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            sources = [SourceRecord(**entry) for entry in raw.get("sources", [])
                       if isinstance(entry, dict)]
        except TypeError:
            # a document written by a newer version, with fields this one does
            # not know: better to re-detect the sources than to refuse the
            # project, since detecting them is cheap and the rest still reads
            sources = []
        return cls(
            project_id=raw.get("project_id") or uuid.uuid4().hex,
            name=raw.get("name", ""),
            created=raw.get("created", now()),
            opened=raw.get("opened", now()),
            derived=raw.get("derived", SIEVE_DIR + "/derived"),
            excluded=[str(x) for x in raw.get("excluded", [])],
            sources=sources,
            skipped=[SourceRecord(**e) for e in raw.get("skipped", [])
                     if isinstance(e, dict)],
        )

    def save(self, folder: Path) -> bool:
        """Write the document, through a rename. `False` if it could not be."""
        target = self.path_in(folder)
        payload = {
            "project_id": self.project_id,
            "name": self.name,
            "created": self.created,
            "opened": self.opened,
            "derived": self.derived,
            "excluded": list(self.excluded),
            "sources": [asdict(source) for source in self.sources],
            "skipped": [asdict(entry) for entry in self.skipped],
        }
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=str(target.parent),
                                                 suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(payload, out, indent=1)
            os.replace(temporary, target)
            return True
        except OSError:
            return False

    def touched(self) -> "Document":
        """The same document, opened now."""
        return replace(self, opened=now())
