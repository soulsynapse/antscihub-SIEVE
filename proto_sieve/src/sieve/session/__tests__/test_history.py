"""Proof for session/history.py's secret: undo/redo move a pointer through
whole committed ``Pipeline`` values, and a push after an undo discards the
redo branch it undid away from.
"""

from __future__ import annotations

from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.session.history import History


def _pipeline(*y1s: int) -> Pipeline:
    return Pipeline(
        source="rep3_intermittent_crop",
        steps=tuple(
            Step(tool="crop", params={"y0": 0, "y1": y1, "x0": 0, "x1": 200})
            for y1 in y1s
        ),
    )


def test_undo_returns_the_previous_committed_value():
    h = History(_pipeline(100))
    h.push(_pipeline(100, 200))

    assert h.undo() == _pipeline(100)
    assert h.present == _pipeline(100)


def test_redo_returns_the_value_undone_away_from():
    h = History(_pipeline(100))
    h.push(_pipeline(100, 200))
    h.undo()

    assert h.redo() == _pipeline(100, 200)


def test_undo_at_the_start_of_history_is_a_no_op():
    h = History(_pipeline(100))

    assert h.undo() == _pipeline(100)
    assert not h.can_undo()


def test_push_after_undo_discards_the_redo_branch():
    h = History(_pipeline(100))
    h.push(_pipeline(100, 200))
    h.undo()
    h.push(_pipeline(100, 300))

    assert not h.can_redo()
    assert h.present == _pipeline(100, 300)


def test_can_undo_and_can_redo_track_stack_state():
    h = History(_pipeline(100))
    assert not h.can_undo()
    assert not h.can_redo()

    h.push(_pipeline(100, 200))
    assert h.can_undo()
    assert not h.can_redo()

    h.undo()
    assert not h.can_undo()
    assert h.can_redo()
