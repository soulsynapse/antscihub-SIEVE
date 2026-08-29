"""Which recordings this person has opened, and when they last did.

The library is per-user and lives beside the settings, because it is a fact
about somebody's working life rather than about any recording: two people
opening the same file each have their own list, and a recording handed to a
colleague does not arrive already in theirs.

**Keyed by the recording's address — resolved when that address is a path,
which is location and not identity.** The key answers which row a file on this machine belongs to, and
nothing beyond that: the same recording is one path on a desktop and another
on a cluster, and one renamed in place becomes a new row with the old one
left pointing at nothing. That is the right trade for a list that never
leaves the machine it was written on, and the wrong one for anything that
travels. Identity has to be written where a rename and a move carry it — a
document beside the recording, holding whatever also tells a re-export from
the file it replaced, since a name that survives a rename survives a
substitution too. Nothing writes one yet. When something does, it is the
identity and this stays the location; a durable record that named a
recording by this key would be naming where it was on one machine on one
day.

An address is not always a path. `Source.handles` takes a `str` and the
contract never says file, so a folder of stills and a generator are addresses
too, and resolving one of those against the working directory invented a path
nobody meant — measured in
`docs/findings/2026.08.29-what-two-more-sources-found-the-contract-cannot-say.md`,
where `synthetic:frames=40` became a row under this repository's own
directory. What is not on this filesystem is kept verbatim and is its own key.

**A recording that has gone is kept and marked, never dropped.** An external
drive that is not plugged in is the ordinary case, and a library that forgot a
project every time somebody unplugged something is one nobody could rely on.
`available` says whether the file is there right now, asked rather than stored:
a drive gets plugged in between one draw and the next, and a cached answer would
be wrong exactly when somebody is looking at the list to decide whether to go
and find it.

**Versioned from the first byte.** The cost is one field; the retrofit is
orphaning every library in existence. A document written by a later version is
left alone rather than reinterpreted or overwritten.

Nothing here imports Qt, and nothing here raises: an unreadable library reads as
empty and a failed write is reported on stderr and dropped, which is what the
settings document beside it does.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

from sieve import settings
from sieve.project import footage

_FILE = "library.json"

#: Bumped when a stored row means something a reader of the old version would
#: get wrong. Additive fields do not need it; a changed meaning does.
VERSION = 1


def path() -> Path:
    """The library document, beside the user's settings.

    Beside, and read off the settings path rather than rebuilt from the same
    rules: `SIEVE_SETTINGS` exists so a run can be made not to touch the
    person's own documents, and a library that missed the override would write
    into theirs from a check.
    """
    return settings.path().parent / _FILE


def now() -> str:
    """A stamp to write down. UTC, and finer than it reads.

    Full precision rather than whole seconds, which is what the list is sorted
    by: adding two recordings from one dialog, or opening a project the second
    after adding it, ties at second resolution and leaves the wrong row on top.
    """
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Entry:
    """One project as the library remembers it, without touching the file."""

    #: the recording itself, resolved — which is what a project is
    video: str
    name: str
    added: str = field(default_factory=now)
    #: empty until it has been opened once, which is not the same as added
    opened: str = ""
    #: which source tool answered for this recording when the row was made
    source: str = ""

    @property
    def folder(self) -> str:
        """Where the recording sits, or empty where that is not a place.

        A folder of stills is its own folder; a file's is its parent; an
        address this filesystem does not have has none, and saying so is what
        lets a card decline to offer a verb rather than opening this
        repository's directory because a scheme resolved into it.
        """
        if not footage.on_disk(self.video):
            return ""
        here = Path(self.video)
        return str(here if here.is_dir() else here.parent)

    @property
    def available(self) -> bool:
        """Is the recording there right now, as far as this can tell?

        A path is asked of the filesystem — either a file or a directory of
        stills, since both are ordinary recordings and `is_file` alone
        reported a present folder as gone. An address that is not on this
        filesystem answers `True`, which is not a claim that it is reachable:
        it is this document declining to say. Only a source tool can answer
        for a camera or a generator, and the library holds no registry on
        purpose — a per-user list that had to load every tool to draw itself
        is one that fails differently on every machine.
        """
        if footage.on_disk(self.video):
            return True
        return not Path(self.video).is_absolute()

    @property
    def last(self) -> str:
        """The stamp the list is ordered by: opened if ever, added otherwise."""
        return self.opened or self.added


class Library:
    """The list of remembered recordings, read and written as a whole."""

    def __init__(self, document: Path | None = None) -> None:
        self.path = document or path()
        self.entries: list[Entry] = []
        #: written by a version this one does not understand — read nothing,
        #: and above all write nothing over it
        self.foreign = False
        self._load()

    # -- reading -----------------------------------------------------------

    def _load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as trouble:
            _complain(f"could not be read ({trouble}); the library reads as empty")
            return
        if not isinstance(raw, dict):
            _complain("does not hold a library; it reads as empty")
            return
        if raw.get("version") != VERSION:
            self.foreign = True
            _complain(
                f"was written by another version of SIEVE (version "
                f"{raw.get('version')!r}, this one reads {VERSION}); it is left "
                f"alone and nothing is remembered this session"
            )
            return
        known = {column.name for column in fields(Entry)}
        for record in raw.get("projects", []):
            if not isinstance(record, dict) or not record.get("video"):
                continue
            self.entries.append(
                Entry(**{key: value for key, value in record.items() if key in known})
            )
        self._sort()

    def _sort(self) -> None:
        """Most recently touched first, which is the order a list is read in."""
        self.entries.sort(key=lambda entry: entry.last, reverse=True)

    def __len__(self) -> int:
        return len(self.entries)

    def find(self, video: Path | str) -> Entry | None:
        wanted = _key(video)
        return next((entry for entry in self.entries if entry.video == wanted), None)

    # -- writing -----------------------------------------------------------

    def add(self, video: Path | str, source: str = "") -> Entry:
        """Point at a recording and remember it.

        Adding one already in the library is not an error and does not duplicate
        it — that is what re-adding is, and the only thing it changes is that the
        row rises to the top.

        `source` is the name of the tool that answered for the file, written
        down because which tool answers is not a property of the file: the
        search path is the user's to order and `source_for` takes the first
        willing tool, so the same recording is served by a different producer
        the moment a directory is added or reordered. The name only — a tool's
        version belongs to the key over its output (ADR-0010), where a bump
        invalidates what was cached under it; on this row it would orphan the
        project every time a tool was upgraded. Empty on a row written before
        this was recorded, and on one whose tool has since gone: both mean ask
        again, which is what happened every time before.
        """
        entry = self.find(video)
        if entry is None:
            resolved = _key(video)
            entry = Entry(video=resolved, name=Path(resolved).stem, source=source)
            self.entries.append(entry)
        else:
            entry.added = now()
            entry.source = source or entry.source
        self._sort()
        self.save()
        return entry

    def touch(self, video: Path | str) -> Entry | None:
        """Record that a project was opened. Unknown recordings are not minted.

        Not re-sorted, though this is what the order is on. Opening a card is
        the one moment somebody is looking straight at it, and a list that
        rearranged itself under the hand that just acted would be reordering as
        an answer to being used. The rank is read at load, where nobody is
        mid-gesture; adding is the move that does reorder, because a new row
        that did not appear where it was put would be worse.
        """
        entry = self.find(video)
        if entry is None:
            return None
        entry.opened = now()
        self.save()
        return entry

    def forget(self, video: Path | str) -> bool:
        """Out of the list. The recording on disk is not touched.

        Deliberately not `delete`: nothing here removes footage, and a verb that
        suggested otherwise is one somebody eventually believes.
        """
        before = len(self.entries)
        wanted = _key(video)
        self.entries = [entry for entry in self.entries if entry.video != wanted]
        if len(self.entries) == before:
            return False
        self.save()
        return True

    def save(self) -> bool:
        """Atomic whole-file replace, as the settings document does it."""
        if self.foreign:
            return False
        document = {
            "version": VERSION,
            "projects": [asdict(entry) for entry in self.entries],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle, temporary = tempfile.mkstemp(
                dir=str(self.path.parent), prefix=f"{_FILE}.", suffix=".tmp"
            )
            # newline="" — text mode on Windows would translate the "\n"s.
            with os.fdopen(handle, "w", encoding="utf-8", newline="") as file:
                json.dump(document, file, indent=2, sort_keys=True)
                file.write("\n")
            os.replace(temporary, self.path)
            return True
        except OSError as trouble:
            _complain(f"could not be written ({trouble}); this change lasts the session")
            return False


def ago(stamp: str, at: datetime | None = None) -> str:
    """An ISO stamp as a phrase, or an empty string if it will not parse.

    Coarse on purpose. "3 days ago" is what somebody scanning a list wants; an
    exact time is a number they then have to do arithmetic on, and the
    arithmetic is the thing the phrase exists to have done for them.
    """
    try:
        when = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return ""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = ((at or datetime.now(timezone.utc)) - when).total_seconds()
    if seconds < 0:
        return "just now"  # a clock that moved, not a project from the future
    for size, unit in ((60, "second"), (60, "minute"), (24, "hour"), (7, "day"),
                       (4.35, "week"), (12, "month")):
        if seconds < size:
            count = int(seconds)
            if count <= 1:
                return "just now" if unit == "second" else f"a {unit} ago"
            return f"{count} {unit}s ago"
        seconds /= size
    years = int(seconds)
    return "a year ago" if years <= 1 else f"{years} years ago"


def _key(video: Path | str) -> str:
    """One spelling per recording, so the same address is not two rows.

    This list's own key, and local to this machine. Nothing durable names a
    recording by it — see the module docstring for what would.

    Resolved only where resolving means something. `Path.resolve` on an
    address this filesystem does not have answers with the working directory
    joined to it, which is a path that never existed and a row that can never
    match again from another directory.
    """
    address = str(video)
    if not footage.on_disk(address):
        return address
    return str(Path(address).resolve())


def _complain(trouble: str) -> None:
    print(f"sieve: library file {path()} {trouble}", file=sys.stderr)
