"""What a project knows about itself, written beside the recording it is about.

**A project is one recording.** That is the whole shape of this package and it
is worth stating first, because an earlier version had a project be a folder and
everything downstream inherited it. The unit of work in SIEVE is a recording:
the crop, the window and the tuning are all about *that* video, and two
recordings are two analyses rather than two rows in one thing. So a person opens
a video and that is the project; the folder it happens to sit in is where its
derived work goes and nothing they have to think about.

One JSON document per recording, at `<folder>/.sieve/<stem>.json`. Several
recordings in one folder are several projects sharing one dot-directory, which
is what lets a folder of a season's footage work without the folder meaning
anything.

**A project has an identity that is not its path.** Files get renamed and moved,
and a library keyed by path would show the same project twice and lose which one
had been opened. So the document carries an id, generated once, and the library
reconciles against it.

**The recording is recorded with a fingerprint.** Size and modification time,
the same discipline the frame table's sidecar uses, so a file replaced between
sessions is noticed rather than served from a stale table. What is *not*
recorded is anything that costs a pass over the file: a frame count needs a
demux, and the count a container volunteers is the one of the three that is
never right (ADR-0004). A card that quoted it would be putting a wrong number on
the screen.

**The derived location is a field rather than a rule.** It defaults to
`.sieve/<stem>/` beside the recording, so the expensive work sits next to what
it came from and a folder copied whole carries it. A recording on read-only or
shared media names somewhere else instead, and the code keeps one path rather
than gaining two modes. The answer to "where did my proxy go" is always "it says
in the document."

Nothing here raises. A document that cannot be read is a recording that has not
been opened before, which is the same situation as a file nobody has pointed at;
a write that fails is reported by returning `False` and the session carries on,
because losing the record of a name is not worth refusing to work.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

#: Where a project's document and, by default, its derived work live. A
#: dot-directory so a folder of footage still looks like a folder of footage to
#: whoever opens it in a file browser.
SIEVE_DIR = ".sieve"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Footage:
    """The recording as the project last saw it.

    Named for what it is rather than `SourceRecord`, which is what it was called
    when a project held several of these and any one of them was *a* source. A
    project has one recording, and it is not one of anything.
    """

    name: str            #: the file's own name, for a card and for a sidecar
    bytes: int
    mtime_ns: int
    codec: str = ""
    width: int = 0
    height: int = 0
    #: seconds, from the container. Duration is what a card shows, because the
    #: honest frame count costs a demux and the volunteered one is wrong.
    duration_s: float = 0.0

    def matches(self, path: Path) -> bool:
        """Is the file still what it was when this was written?"""
        try:
            stat = path.stat()
        except OSError:
            return False
        return stat.st_size == self.bytes and stat.st_mtime_ns == self.mtime_ns

    @property
    def shape(self) -> str:
        return f"{self.width}×{self.height}" if self.width else "unknown size"


@dataclass
class Document:
    """A project's own record of itself."""

    project_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    created: str = field(default_factory=now)
    opened: str = field(default_factory=now)
    #: Where derived work goes, relative to the recording's folder unless
    #: absolute. Empty means "the default beside this recording", worked out
    #: from the stem rather than stored — so renaming the file does not leave
    #: the document pointing at a directory named after what it used to be.
    derived: str = ""
    footage: Footage | None = None

    # ── locating ─────────────────────────────────────────────────────────
    @staticmethod
    def path_for(video: Path) -> Path:
        """Where this recording's document lives."""
        return video.parent / SIEVE_DIR / f"{video.stem}.json"

    def derived_for(self, video: Path) -> Path:
        """Where this recording's derived work lives.

        Absolute stays absolute — the escape hatch for read-only or shared
        media — and anything else is beside the recording, under a directory
        named for it so two recordings in one folder cannot collide.
        """
        if self.derived:
            written = Path(self.derived)
            return written if written.is_absolute() else video.parent / written
        return video.parent / SIEVE_DIR / video.stem

    # ── reading and writing ──────────────────────────────────────────────
    @classmethod
    def load(cls, video: Path) -> "Document | None":
        """The document for `video`, or `None` if there is not one to read."""
        try:
            raw = json.loads(cls.path_for(video).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        recorded = raw.get("footage")
        try:
            footage = Footage(**recorded) if isinstance(recorded, dict) else None
        except TypeError:
            # written by a version carrying fields this one does not know.
            # Reading the headers again is one container open; refusing the
            # project over a field nobody here needs would cost the work.
            footage = None
        return cls(
            project_id=raw.get("project_id") or uuid.uuid4().hex,
            name=raw.get("name", ""),
            created=raw.get("created", now()),
            opened=raw.get("opened", now()),
            derived=raw.get("derived", ""),
            footage=footage,
        )

    def save(self, video: Path) -> bool:
        """Write the document, through a rename. `False` if it could not be."""
        target = self.path_for(video)
        payload = {
            "project_id": self.project_id,
            "name": self.name,
            "created": self.created,
            "opened": self.opened,
            "derived": self.derived,
            "footage": asdict(self.footage) if self.footage else None,
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
