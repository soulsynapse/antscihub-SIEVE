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

    def __init__(self, path: Path, project: Project, *, on_disk: bool = False) -> None:
        self._path = path
        self._past: list[Project] = []
        self._present = project
        self._future: list[Project] = []
        # The value the file is known to hold, or `None` for a session that has
        # never read or written one. `False` by default because a caller that
        # composed a project in memory cannot say what is at `path` — it may not
        # even exist — and a session that claimed the file agreed would decline
        # the one write that would make it true.
        self._on_disk: Project | None = project if on_disk else None

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
        return cls(path, Project.load(path), on_disk=True)

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

    def commit(self, project: Project) -> bool:
        """`project` becomes the present value, if it is not already.

        A value equal to the present one is dropped whole: nothing appended,
        nothing to undo, and no new value for anything downstream to re-plan
        from. That is part of what being the document's only writer means rather
        than an exception to it — a write is a change, and a value identical to
        the one held is not one. It has to live here for the same reason the
        writes do: every surface that can produce a no-op would otherwise need
        its own guard, and Qt hands them out freely — re-selecting the entry a
        combo already shows, arrowing a spin box away and back. A live drag is
        untouched, because its stream is distinct values and every one of them
        is real.

        **Whether the write took is the return value, because the drop is not
        otherwise observable.** A caller that announced its edit regardless would
        tell the rest of the window something happened that did not — a graph
        marked stale and re-rendered for a document that has not moved. Reading
        it back off the session instead would mean every caller re-deriving the
        equality this method just computed.

        The redo branch is dropped: an edit made after an undo is a divergence,
        and keeping the abandoned side reachable would offer a redo that lands on
        a document the user has since edited away from.

        The caller supplies the whole value, already built. That is the split
        with the intent layer above — it knows what a SetParam means, this knows
        only that a new document has arrived.

        Returns:
            Whether the document moved.
        """
        if project == self._present:
            return False
        self._past.append(self._present)
        self._present = project
        self._future.clear()
        return True

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

        Unconditional, unlike `save_if_edited`: a caller reaching this is saying
        the file must hold the present value when it returns, which is what the
        run button means by it — the argv it is about to issue names the path.
        """
        self._present.save(self._path)
        self._on_disk = self._present

    @property
    def edited(self) -> bool:
        """Whether the present value differs from the one the file holds.

        The comparison an undo already makes (`commit`), asked against the value
        last read or written rather than against the top of the past stack — so
        stepping back onto the value that was opened is not an edit, and a
        parameter moved and moved back is not one either. That is the whole of
        what dirty state costs here: two stacks of whole values means the saved
        value is another whole value, and nothing has to record what an edit
        *was* to know one has happened.
        """
        return self._present != self._on_disk

    def save_if_edited(self) -> bool:
        """Write the present value back, unless the file already holds it.

        The guard is not an optimisation. `Project.to_yaml` is stable byte for
        byte so that version control is usable on the one file a user most wants
        a history of (`core/pipeline_model.py`), and a session that rewrote its
        file on every close would spend that stability on documents nobody
        touched — a mtime moved, a sync woken, a diff that says the project was
        worked on when it was only opened.

        Returns:
            Whether anything was written.
        """
        if not self.edited:
            return False
        self.save()
        return True
