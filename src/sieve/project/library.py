"""Which projects this person has, and which they were in last.

The library is per-user and lives beside the settings, because it is a fact
about somebody's working life rather than about any recording: two people
opening the same file each have their own list, and a recording handed to a
colleague does not arrive already in theirs.

**Keyed by the project's identity, not its path.** A recording gets renamed and
moved, and a library keyed by path shows the same project twice and loses which
one was opened. So an entry carries the id out of the project's own document,
and adding a recording whose id is already known updates that entry's path
instead of making a second row.

**Entries are a cache of what the cards need, refreshed on open.** A list of ten
projects should not cost ten container opens to draw — the whole point of a list
is to look at it before deciding which one to pay for. So the name, the summary
and the time are written down when a project is opened, and the file is only
read again when somebody opens it again.

**A recording that has gone is kept and marked, never dropped.** An external
drive that is not plugged in is the ordinary case, and a library that silently
forgot a project every time somebody unplugged something would be one nobody
could rely on. `available` says whether the file is there right now; nothing
removes an entry except a person asking.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sieve import settings
from sieve.project.document import now
from sieve.project.project import Project

_FILE = "library.json"


def path() -> Path:
    """The library document, beside the user's settings."""
    return settings.directory() / _FILE


@dataclass
class Entry:
    """One project as the library remembers it, without opening the folder."""

    project_id: str
    #: the recording itself, which is what a project is
    video: str
    name: str
    summary: str = ""
    opened: str = field(default_factory=now)

    @property
    def folder(self) -> str:
        """Where the recording sits. For a card offering to show it on disk."""
        return str(Path(self.video).parent)

    @property
    def available(self) -> bool:
        """Is the recording there right now?

        Asked rather than stored: a drive gets plugged in between one draw and
        the next, and a cached answer would be wrong exactly when somebody is
        looking at the list to decide whether to go and find it.
        """
        return Path(self.video).is_file()

    def opened_ago(self, at: datetime | None = None) -> str:
        """When it was last opened, written as it is to be read."""
        return _ago(self.opened, at)


class Library:
    """The list of known projects, read and written as a whole."""

    def __init__(self, document: Path | None = None):
        self.path = document or path()
        self.entries: list[Entry] = []
        self._load()

    # ── reading ──────────────────────────────────────────────────────────
    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for record in raw.get("projects", []):
            if not isinstance(record, dict):
                continue
            try:
                self.entries.append(Entry(**record))
            except TypeError:
                continue     # a row this version does not understand
        self._sort()

    def _sort(self) -> None:
        """Most recently opened first, which is the order a list is read in."""
        self.entries.sort(key=lambda entry: entry.opened, reverse=True)

    def __len__(self) -> int:
        return len(self.entries)

    def find(self, project_id: str) -> Entry | None:
        return next((e for e in self.entries if e.project_id == project_id),
                    None)

    def by_video(self, video: Path) -> Entry | None:
        wanted = str(Path(video).resolve())
        return next((e for e in self.entries if e.video == wanted), None)

    # ── writing ──────────────────────────────────────────────────────────
    def add(self, video: Path) -> Project | None:
        """Point at a recording: open it, record it, and hand it back.

        `None` where the file does not read as video, and nothing is added —
        a row for something that cannot be opened is a row that fails every
        time it is touched.

        Adding a recording already in the library is not an error and does not
        duplicate it. It is what reopening is, and the only difference is
        whether the path has changed since.
        """
        project = Project.open(Path(video))
        if project is None:
            return None
        self.remember(project)
        return project

    def add_all(self, videos) -> tuple[list[Project], list[Path]]:
        """Add several recordings at once. Returns what opened and what did not.

        A person with a season of footage picks fifty files in one dialog, and
        one of them being a half-copied download is not a reason for the other
        forty-nine to fail. So the refusals come back as a list rather than as
        an exception, and the caller decides what to say about them.
        """
        opened, refused = [], []
        for video in videos:
            project = self.add(Path(video))
            if project is None:
                refused.append(Path(video))
            else:
                opened.append(project)
        return opened, refused

    def remember(self, project: Project) -> Entry:
        """Record what a project is, now, under its own identity."""
        entry = self.find(project.document.project_id)
        if entry is None:
            entry = Entry(project_id=project.document.project_id,
                          video=str(project.video), name=project.name)
            self.entries.append(entry)
        entry.video = str(project.video)
        entry.name = project.name
        entry.summary = project.summary()
        entry.opened = project.document.opened
        self._sort()
        self.save()
        return entry

    def forget(self, project_id: str) -> bool:
        """Remove a project from the list. The recording is not touched.

        Deliberately not called `delete`: nothing here removes footage, and a
        verb that suggested otherwise would be one somebody eventually
        believed.
        """
        before = len(self.entries)
        self.entries = [e for e in self.entries
                        if e.project_id != project_id]
        if len(self.entries) == before:
            return False
        self.save()
        return True

    def save(self) -> bool:
        payload = {"projects": [asdict(entry) for entry in self.entries]}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(dir=str(self.path.parent),
                                                 suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(payload, out, indent=1)
            os.replace(temporary, self.path)
            return True
        except OSError:
            return False


def _ago(stamp: str, at: datetime | None = None) -> str:
    """An ISO timestamp as a phrase, or an empty string if it will not parse.

    Coarse on purpose. "3 days ago" is what somebody scanning a list wants;
    an exact time would be a number they then have to do arithmetic on, and
    the arithmetic is the thing the phrase exists to have done for them.
    """
    try:
        when = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = ((at or datetime.now(timezone.utc)) - when).total_seconds()
    if seconds < 0:
        return "just now"         # a clock that moved, not a project from the future
    for size, unit in ((60, "second"), (60, "minute"), (24, "hour"),
                       (7, "day"), (4.35, "week"), (12, "month")):
        if seconds < size:
            count = int(seconds)
            if count <= 1:
                return "just now" if unit == "second" else f"a {unit} ago"
            return f"{count} {unit}s ago"
        seconds /= size
    years = int(seconds)
    return "a year ago" if years <= 1 else f"{years} years ago"
