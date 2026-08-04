"""Proof for session/session.py's secret: a draft is not part of the
pipeline until commit, selecting a step discards a stale draft, and
undo/redo delegate to history while clearing any in-flight draft.
"""

from __future__ import annotations

from proto_sieve.src.sieve.pipeline import Pipeline, Step
from proto_sieve.src.sieve.session.session import Session


def _pipeline(*y1s: int) -> Pipeline:
    return Pipeline(
        source="rep3_intermittent_crop",
        steps=tuple(
            Step(tool="crop", params={"y0": 0, "y1": y1, "x0": 0, "x1": 200})
            for y1 in y1s
        ),
    )


def test_edit_does_not_change_the_committed_pipeline():
    s = Session(_pipeline(100))
    s.edit(Step(tool="crop", params={"y0": 0, "y1": 999, "x0": 0, "x1": 200}))

    assert s.pipeline == _pipeline(100)
    assert s.draft is not None


def test_commit_replaces_the_current_step_and_pushes_history():
    s = Session(_pipeline(100))
    s.edit(Step(tool="crop", params={"y0": 0, "y1": 999, "x0": 0, "x1": 200}))
    s.commit()

    assert s.pipeline == _pipeline(999)
    assert s.draft is None
    assert s.can_undo()


def test_commit_with_no_draft_is_a_no_op():
    s = Session(_pipeline(100))
    s.commit()

    assert s.pipeline == _pipeline(100)
    assert not s.can_undo()


def test_select_discards_a_staged_draft():
    s = Session(_pipeline(100, 200))
    s.edit(Step(tool="crop", params={"y0": 0, "y1": 999, "x0": 0, "x1": 200}))
    s.select(1)

    assert s.draft is None
    assert s.current_index == 1


def test_undo_reverts_a_commit_and_clears_any_draft():
    s = Session(_pipeline(100))
    s.edit(Step(tool="crop", params={"y0": 0, "y1": 999, "x0": 0, "x1": 200}))
    s.commit()
    s.edit(Step(tool="crop", params={"y0": 0, "y1": 1, "x0": 0, "x1": 200}))

    s.undo()

    assert s.pipeline == _pipeline(100)
    assert s.draft is None
