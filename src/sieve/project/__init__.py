"""What a project is: one recording, and the list of them.

**A project is a recording** — whatever a loaded source tool will open, which
`sieve.registry` answers and nothing here decides. The unit of work in SIEVE is
that recording: the crop, the window and the tuning are all about *it*, so a
person points at one and that is the project. The folder it sits in is where
its derived work will go and nothing they have to think about. Two recordings
are two projects, not two rows in one.

`footage` is what can be said about a recording from the outside. `library` is
the per-user list of which ones have been pointed at, which is a fact about a
person rather than about any recording.

Nothing here imports Qt, and nothing here opens a recording — that is a source
tool's job.
"""

from __future__ import annotations

from sieve.project.footage import kind, size
from sieve.project.library import Entry, Library, ago

__all__ = [
    "Entry",
    "Library",
    "ago",
    "kind",
    "size",
]
