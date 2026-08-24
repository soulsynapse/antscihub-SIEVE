"""What a project is: a folder somebody pointed at, and the list of them.

`document` is a project's own record, written in a dot-directory beside the
footage — an identity that survives the folder being renamed, where derived
work goes, and what was found last time. `sources` is the detection: headers
and `stat` calls, nothing decoded, nothing moved. `project` is the two of them
together, plus the join to a session. `library` is the per-user list of which
projects exist, which is a fact about a person rather than about any project.

Nothing here imports Qt, and nothing here decodes a frame. Pointing at a folder
costs one container open per file and no demux, which is what lets adding a
project be a free and reversible move rather than an import.
"""

from __future__ import annotations

from sieve.project.document import SIEVE_DIR, Document, SourceRecord
from sieve.project.library import Entry, Library
from sieve.project.project import Project
from sieve.project.sources import VIDEO_SUFFIXES, detect

__all__ = [
    "SIEVE_DIR",
    "VIDEO_SUFFIXES",
    "Document",
    "Entry",
    "Library",
    "Project",
    "SourceRecord",
    "detect",
]
