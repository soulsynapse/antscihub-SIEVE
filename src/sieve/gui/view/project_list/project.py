"""One project as the list reads it: a name and two display-ready lines.

The row is what a card draws, not what the library stores: every field is a
finished string, so the card never formats anything and the list never has to
know what a recording is. `video` is not drawn — it is the identity the list
hands back when somebody asks for a row to be opened or removed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sieve.project import footage
from sieve.project.library import Entry, ago


@dataclass(frozen=True)
class Project:
    """A row in the library: what it is called, what it is, when it was here."""

    name: str
    holds: str
    opened: str
    folder: str
    #: the recording, resolved — the row's identity, never drawn
    video: str = ""

    @classmethod
    def of(cls, entry: Entry) -> "Project":
        """Read one library entry as the lines a card shows."""
        return cls(
            name=entry.name,
            holds=_holds(entry),
            opened=_when(entry),
            folder=entry.folder,
            video=entry.video,
        )


def _holds(entry: Entry) -> str:
    """What the project is, or that it is not where it was.

    A missing recording says so on the line that would have described it: the
    drive is unplugged or the file has moved, and that is the one fact somebody
    scanning the list needs before they act on the row.
    """
    video = Path(entry.video)
    if not entry.available:
        return "not where it was"
    return " · ".join(part for part in (footage.kind(video), footage.size(video)) if part)


def _when(entry: Entry) -> str:
    """Opened if it ever has been, added otherwise — they are different facts."""
    if entry.opened:
        return f"opened {ago(entry.opened)}"
    return f"added {ago(entry.added)}"
