"""One recording, and what SIEVE knows about it.

Opening a project is: read the document if there is one, read the recording's
headers if the file has changed since, write the document back. All of it is one
container open, so pointing at a recording is instant and reversible — which is
what makes adding one a free move rather than an import.

**A project is the recording.** Not a folder holding one, and not a file
describing one: the video is what somebody chose, and the document is SIEVE's
note to itself in a dot-directory beside it. An earlier version made a project a
folder and every card then had to summarise a set nobody was going to work on as
a unit. The crop, the window and the tuning are about *this* recording; two
recordings are two projects.

**Nothing is moved and nothing is copied.** The file is read. What SIEVE writes
goes under the derived location the document names, which defaults to
`.sieve/<stem>/` beside the recording — so the expensive work sits next to what
it came from, and a folder copied whole carries it.

**A session is the project, opened.** There is one recording, so there is one
session and no choosing: `session()` is the join to the substrate and the only
place in this package that knows a decoder exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sieve.project import footage as headers
from sieve.project.document import Document, Footage
from sieve.session.session import Session


@dataclass
class Project:
    """One recording, its document, and what its headers say."""

    video: Path
    document: Document

    # ── opening ──────────────────────────────────────────────────────────
    @classmethod
    def open(cls, video: Path) -> "Project | None":
        """Open or adopt a recording. `None` if it does not read as video.

        A file nobody has pointed at before and one whose document is
        unreadable are the same situation and are treated the same way: make a
        document, read the headers, write it. The only difference between
        adopting and reopening is whether an identity already exists, and that
        difference belongs in the document rather than in two methods.

        `None` rather than an exception, and rather than a project with nothing
        in it: a person who picked a file that is not video is owed being told,
        and a library row for something that cannot be opened is a row that
        fails every time it is touched.
        """
        video = Path(video).resolve()
        document = Document.load(video) or Document(name=video.stem)
        if not document.name:
            document.name = video.stem
        # the headers again only if the file has moved under the record. That
        # is the whole of what a fingerprint buys here: reopening a recording
        # costs a stat, and reopening one that has been re-exported costs the
        # open it actually needs.
        if document.footage is None or not document.footage.matches(video):
            fresh = headers.read(video)
            if fresh is None:
                return None
            document.footage = fresh
        project = cls(video=video, document=document.touched())
        project.save()
        return project

    def save(self) -> bool:
        return self.document.save(self.video)

    # ── what it is ───────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self.document.name or self.video.stem

    @property
    def footage(self) -> Footage | None:
        return self.document.footage

    @property
    def derived(self) -> Path:
        return self.document.derived_for(self.video)

    @property
    def folder(self) -> Path:
        """Where the recording sits. For a card offering to show it on disk."""
        return self.video.parent

    def present(self) -> bool:
        """Is the recording still where the document says?

        Asked rather than stored: a drive gets plugged in between one draw and
        the next, and a cached answer would be wrong exactly when somebody is
        looking at the list to decide whether to go and find it.
        """
        return self.video.is_file()

    def summary(self) -> str:
        """What the card says this recording is, in the user's terms.

        Formed here rather than in the view, because what is worth saying about
        a recording is a decision about what a project is. Duration rather than
        a frame count, for the reason `footage.py` gives: the honest count costs
        a demux and the cheap one is wrong.
        """
        held = self.document.footage
        if held is None:
            return "not read yet"
        parts = [held.shape, _duration(held.duration_s)]
        if held.codec:
            parts.append(held.codec)
        return " · ".join(parts)

    # ── the join to the substrate ────────────────────────────────────────
    def session(self, **kwargs) -> Session:
        """A session over this recording.

        The derived directory comes from the document, so every session of one
        project writes to one place and a recording carried to another machine
        finds its own chunks rather than rebuilding them.
        """
        return Session(self.video, self.derived, **kwargs)


def _duration(seconds: float) -> str:
    """Seconds as somebody reads them, not as they are stored."""
    if seconds < 1:
        return "under a second"
    minutes, remainder = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {remainder:02d}s"
    return f"{remainder}s"
