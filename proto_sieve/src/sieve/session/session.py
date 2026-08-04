"""Secret: what "current" means and how an edit becomes committed.

Composes ``History`` (chunk: whole committed ``Pipeline`` values) with a
current step index and at most one draft — an uncommitted replacement for
the current step. A draft is not a ``Step`` that exists in the pipeline yet;
``commit`` is the only thing that turns one into a new committed value. See
docs/DECISIONS.md, 2026-08-03.
"""

from __future__ import annotations

from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.session.history import History


class Session:
    def __init__(self, initial: Pipeline, current_index: int = 0) -> None:
        self._history = History(initial)
        self._current_index = current_index
        self._draft: Step | None = None

    @property
    def pipeline(self) -> Pipeline:
        return self._history.present

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def draft(self) -> Step | None:
        return self._draft

    def can_undo(self) -> bool:
        return self._history.can_undo()

    def can_redo(self) -> bool:
        return self._history.can_redo()

    def select(self, index: int) -> None:
        """Move which step is current. Discards any uncommitted draft — a
        draft belongs to the step it was made on, not to whichever step is
        selected next."""
        self._draft = None
        self._current_index = index

    def edit(self, step: Step) -> None:
        """Stage an uncommitted replacement for the current step."""
        self._draft = step

    def discard_draft(self) -> None:
        self._draft = None

    def commit(self) -> None:
        """The draft becomes the current step. A no-op with no draft staged."""
        if self._draft is None:
            return
        steps = list(self.pipeline.steps)
        steps[self._current_index] = self._draft
        self._history.push(Pipeline(self.pipeline.source, tuple(steps)))
        self._draft = None

    def undo(self) -> Pipeline:
        self._draft = None
        return self._history.undo()

    def redo(self) -> Pipeline:
        self._draft = None
        return self._history.redo()

    def history_timeline(self) -> list[Pipeline]:
        return self._history.timeline()

    def history_index(self) -> int:
        return self._history.index

    def jump_to(self, index: int) -> Pipeline:
        """Move directly to a timeline entry, same pointer-move as undo/redo
        (does not touch ``current_index`` — neither does undo/redo today)."""
        self._draft = None
        return self._history.jump(index)

    def load(self, pipeline: Pipeline) -> None:
        """Adopt a pipeline loaded from storage as a fresh commit — it becomes
        the new present, the old present becomes undoable-back-to."""
        self._draft = None
        self._current_index = 0
        self._history.push(pipeline)
