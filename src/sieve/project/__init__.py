"""What a project is: one recording, and the list of them.

**A project is a video file.** The unit of work in SIEVE is a recording — the
crop, the window and the tuning are all about *that* video — so a person opens a
recording and that is the project. The folder it sits in is where its derived
work goes and nothing they have to think about. An earlier version made a
project a folder of footage, and every card then had to summarise a set nobody
was going to work on as a unit.

`document` is a project's own record, written in a dot-directory beside the
recording: an identity that survives the file being renamed, where derived work
goes, and what the headers said last time. `footage` reads those headers, which
is one container open and no demux. `project` is the two together, plus the join
to a session. `library` is the per-user list of which recordings have been
opened, which is a fact about a person rather than about any recording.

Nothing here imports Qt, and nothing here decodes a frame.
"""

from __future__ import annotations

from sieve.project.document import SIEVE_DIR, Document, Footage
from sieve.project.footage import VIDEO_SUFFIXES, dialog_filter, read
from sieve.project.library import Entry, Library
from sieve.project.project import Project

__all__ = [
    "SIEVE_DIR",
    "VIDEO_SUFFIXES",
    "Document",
    "Entry",
    "Footage",
    "Library",
    "Project",
    "dialog_filter",
    "read",
]
