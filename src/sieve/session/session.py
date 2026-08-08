"""The open project, the file it came from, and the two stacks around it.

Undo moves a pointer through whole values; it never inverts an edit. Nothing
here knows what an edit *was*, which is what keeps the layer above free to add
an intent kind without teaching this module an inverse for it — the failure v2's
`document.py`/`commands.py` pair co-changed for. It is also what keeps history
out of the widgets: a stack of values has nothing a view could bind to except
the value it already renders.

**Whole values are affordable because the expensive part is not stored here.**
Two documents sharing a graph prefix key their shared nodes identically
(`pipeline/cache_key.py`), so stepping back through history serves that prefix
out of the executor's store and recomputes only the tail — the mechanism
`pipeline/preview.py` describes for a parameter edit, arriving here for free
because an undo produces the same kind of value an edit does. There is no
history-aware code anywhere below this layer, and there is nothing for one to
do.

**The stacks hold `Project`, not `Pipeline`.** VISION names the shape "two
stacks of whole immutable pipeline values"; in schema v1 the whole value is the
document, because the graph alone cannot carry a checkoff — `checkpoints` and
`outputs` are recorded on `Project` for the identity reason
`core/pipeline_model.py` states. Stacking graphs would make the save screen's
writes the one class of edit that could not be undone.

Nothing here computes: a new value arrives from above already made, and what it
renders to is `pipeline`'s answer to give.
"""

from __future__ import annotations

from pathlib import Path
from typing import Self

from sieve.core.pipeline_model import Project


class Session:
    """One open project: where it came from, what it is now, where it has been.

    A session exists only for a project that is open. There is no state here for
    "nothing chosen yet" — which screen a front end shows before one is open is
    view state, and the first cut opens a project that already exists
    (`PLAN.md`, Phase 7).
    """

    def __init__(self, path: Path, project: Project) -> None:
        self._path = path
        self._past: list[Project] = []
        self._present = project
        self._future: list[Project] = []

    @classmethod
    def open(cls, path: Path) -> Self:
        """Read the project at `path` and hold it as the present value.

        The history starts empty rather than seeded: what a file held before this
        session opened it is not something this session can step back to, and an
        undo that appeared available and did nothing is worse than one that is
        greyed out.

        Raises:
            OSError: if `path` cannot be read.
            ValidationError: if the document is structurally invalid.
        """
        return cls(path, Project.load(path))

    @property
    def path(self) -> Path:
        """The file this project was read from, and the one `save` writes."""
        return self._path

    @property
    def project(self) -> Project:
        """The present value — what a front end renders and a run runs."""
        return self._present

    def can_undo(self) -> bool:
        return bool(self._past)

    def can_redo(self) -> bool:
        return bool(self._future)

    def commit(self, project: Project) -> None:
        """`project` becomes the present value.

        The redo branch is dropped: an edit made after an undo is a divergence,
        and keeping the abandoned side reachable would offer a redo that lands on
        a document the user has since edited away from.

        The caller supplies the whole value, already built. That is the split
        with the intent layer above — it knows what a SetParam means, this knows
        only that a new document has arrived.
        """
        self._past.append(self._present)
        self._present = project
        self._future.clear()

    def undo(self) -> Project:
        """Step back one value, or stay put at the bottom of the stack.

        A no-op rather than an error, because a held-down shortcut reaching the
        end of history is ordinary use and not a fault.
        """
        if self._past:
            self._future.append(self._present)
            self._present = self._past.pop()
        return self._present

    def redo(self) -> Project:
        """Step forward one value, or stay put at the top of the stack."""
        if self._future:
            self._past.append(self._present)
            self._present = self._future.pop()
        return self._present

    def save(self) -> None:
        """Write the present value back to the file this project was opened from.

        Only the present: history is this session's, not the document's, so a
        reopened project has no stacks and nothing about it records that it once
        did.
        """
        self._present.save(self._path)
