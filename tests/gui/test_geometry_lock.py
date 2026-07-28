"""The geometry lock: a replicate that has been tuned refuses to be moved.

The claim under test is not "a dialog appears". It is that the three states a
drag can end in are each *complete*: an untuned arena moves with no question
asked, a refused move leaves the document indistinguishable from one that never
happened — undo stack included, which is the part a plain undo cannot give — and
an accepted move keeps the geometry, keeps the pins, and drops the lock so it
re-arms the next time the arena is opened.

Every drag here is at least two steps. One step cannot see merge behaviour at
all, and the refusal is built on the merge: it puts the box back under the
gesture's own token so the entry the drag built absorbs the restore and takes
itself off the stack.
"""

from __future__ import annotations

import pytest

from sieve.core.pipeline_model import Project, SourceRef
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)
STEP_ONE = ROI(x=30, y=20, width=100, height=80)
STEP_TWO = ROI(x=60, y=20, width=100, height=80)

GESTURE = 7


def _drag(document: ReplicateDocument, index: int = 0) -> None:
    """Two steps of one continuous drag, without releasing."""
    document.set_roi(index, STEP_ONE, gesture=GESTURE)
    document.set_roi(index, STEP_TWO, gesture=GESTURE)


def _accept(_replicate: Replicate) -> bool:
    return True


def _decline(_replicate: Replicate) -> bool:
    return False


def _refuse_to_ask(_replicate: Replicate) -> bool:
    raise AssertionError("the lock asked about a replicate that was never tuned")


class TestUnvisited:
    def test_an_untuned_replicate_drags_without_a_question(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        document.undo_stack.clear()

        _drag(document)
        document.finish_roi_gesture(0, GESTURE, _refuse_to_ask)

        assert document.at(0).roi == STEP_TWO
        # And one entry for the whole drag, which is what says the lock did not
        # quietly change how an ordinary gesture reaches the stack.
        assert document.undo_stack.count() == 1


class TestDeclined:
    def test_declining_leaves_the_geometry_exactly_as_it_was(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        document.mark_visited(0)
        _drag(document)

        document.finish_roi_gesture(0, GESTURE, _decline)

        assert document.at(0).roi == BOX

    def test_declining_pushes_nothing_onto_the_undo_stack(
        self, document: ReplicateDocument
    ) -> None:
        # The load-bearing half, and the reason this is not "edit, then undo".
        # A refused drag the user cannot tell they made must leave no entry to
        # step through and no dirty document — so the count is asserted, not
        # just the index.
        document.add_roi(BOX)
        document.mark_visited(0)
        document.undo_stack.clear()
        _drag(document)

        document.finish_roi_gesture(0, GESTURE, _decline)

        assert document.undo_stack.count() == 0
        assert document.undo_stack.isClean()
        assert document.is_visited(0)


class TestAccepted:
    def test_accepting_keeps_the_move_and_disarms_the_lock(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        document.mark_visited(0)
        _drag(document)

        document.finish_roi_gesture(0, GESTURE, _accept)

        assert document.at(0).roi == STEP_TWO
        # "Functionally a new replicate": it has not been opened in the filter
        # tab at *this* geometry, so the next drag is free and the next visit
        # re-arms it.
        assert not document.is_visited(0)

    def test_the_pins_survive_the_move(self, document: ReplicateDocument) -> None:
        # Rule 6 in the warning's direction: the dialog promises the settings
        # stay, and an override is a parameter choice that re-resolves against
        # the new box untouched. If this ever stops holding, the wording is a
        # lie before the code is a bug.
        document.add_roi(BOX)
        document.add_roi(ROI(x=400, y=400, width=50, height=50))
        document.select(0)
        document.edit_detector({"window_frames": 45}, "Window")
        document.mark_visited(0)
        _drag(document)

        document.finish_roi_gesture(0, GESTURE, _accept)

        assert document.at(0).detector_overrides == {"window_frames": 45}


class TestPersistence:
    def test_the_lock_survives_a_save_and_a_load(self, document: ReplicateDocument) -> None:
        # A lock that evaporated on close would protect only the session that
        # did not need it. The round trip goes through YAML rather than through
        # the object, because the field has to survive serialization to be
        # worth having on the artifact at all.
        document.add_roi(BOX)
        document.add_roi(ROI(x=400, y=400, width=50, height=50))
        document.mark_visited(1)
        tuned = document.at(1).replicate_id

        saved = document.apply_to(Project(source=SourceRef(path="clip.mp4")))
        reopened = Project.from_yaml(saved.to_yaml())
        document.load_project(reopened)

        assert reopened.visited == (tuned,)
        assert not document.is_visited(0)
        assert document.is_visited(1)

    def test_a_deleted_replicate_takes_its_lock_out_of_the_file(
        self, document: ReplicateDocument
    ) -> None:
        # The document does not prune on removal — an undo of the delete has to
        # bring the lock back with the arena — so the file is where the stale id
        # is dropped, and the artifact refuses one that reaches it anyway.
        document.add_roi(BOX)
        document.mark_visited(0)
        document.remove(0)

        saved = document.apply_to(Project(source=SourceRef(path="clip.mp4")))

        assert saved.visited == ()
