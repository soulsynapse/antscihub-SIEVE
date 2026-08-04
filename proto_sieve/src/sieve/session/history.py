"""Secret: how committed ``Pipeline`` values are tracked over time.

Two stacks of whole ``Pipeline`` values, past and future, around one present
value. History never sees a step, a draft, an index, or the GUI — only
``Pipeline`` values going in (``push``) and coming back out (``undo``/
``redo``). Undo is moving a pointer through a list of values, not inverting
an edit, which is what keeps this module from needing to know what a step is.
"""

from __future__ import annotations

from proto_sieve.src.sieve.pipeline import Pipeline


class History:
    def __init__(self, initial: Pipeline) -> None:
        self._past: list[Pipeline] = []
        self._present = initial
        self._future: list[Pipeline] = []

    @property
    def present(self) -> Pipeline:
        return self._present

    def can_undo(self) -> bool:
        return bool(self._past)

    def can_redo(self) -> bool:
        return bool(self._future)

    def push(self, pipeline: Pipeline) -> None:
        """Commit a new present value. Clears redo — a fresh commit after an
        undo discards the branch it undid away from."""
        self._past.append(self._present)
        self._present = pipeline
        self._future.clear()

    def undo(self) -> Pipeline:
        if self._past:
            self._future.append(self._present)
            self._present = self._past.pop()
        return self._present

    def redo(self) -> Pipeline:
        if self._future:
            self._past.append(self._present)
            self._present = self._future.pop()
        return self._present
