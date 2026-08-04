"""Secret: how committed ``Pipeline`` values are tracked over time.

Two stacks of whole ``Pipeline`` values, past and future, around one present
value. History never sees a step, a draft, an index, or the GUI — only
``Pipeline`` values going in (``push``) and coming back out (``undo``/
``redo``/``jump``). Undo is moving a pointer through a list of values, not
inverting an edit, which is what keeps this module from needing to know what
a step is. ``timeline``/``index``/``jump`` exist so a caller can display and
revisit any entry directly, not just step one at a time — ``jump`` still
moves the same pointer through the same list, it just accepts an arbitrary
target instead of ±1.
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

    @property
    def index(self) -> int:
        return len(self._past)

    def timeline(self) -> list[Pipeline]:
        return [*self._past, self._present, *self._future]

    def jump(self, index: int) -> Pipeline:
        combined = self.timeline()
        if not 0 <= index < len(combined):
            raise IndexError(f"history index {index} out of range for {len(combined)} entries")
        self._past = combined[:index]
        self._present = combined[index]
        self._future = combined[index + 1 :]
        return self._present
