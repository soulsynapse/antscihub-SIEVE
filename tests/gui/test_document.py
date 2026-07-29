








from __future__ import annotations

import pytest

from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)
OTHER_BOX = ROI(x=300, y=300, width=50, height=50)


def _names(document: ReplicateDocument) -> list[str]:
    return [replicate.name for replicate in document.all()]


class TestAdd:
    def test_add_appends_with_the_next_default_name(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        assert _names(document) == ["Replicate 1", "Replicate 2"]

    def test_undo_removes_the_replicate(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.undo_stack.undo()
        assert len(document) == 0

    def test_redo_restores_the_same_identity(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        replicate_id = document.at(0).replicate_id
        document.undo_stack.undo()
        document.undo_stack.redo()
        assert document.at(0).replicate_id == replicate_id

    def test_roi_is_clamped_to_the_source(self, document: ReplicateDocument) -> None:
        document.add_roi(ROI(x=990, y=790, width=100, height=100))
        assert document.at(0).roi == ROI(x=990, y=790, width=10, height=10)

    def test_add_emits_structure_and_position(self, document: ReplicateDocument) -> None:
        added: list[int] = []
        structure: list[None] = []
        document.replicate_added.connect(added.append)
        document.structure_changed.connect(lambda: structure.append(None))

        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)

        assert added == [0, 1]
        assert len(structure) == 2


class TestRemove:
    def test_undo_restores_position_and_identity(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        first, second = document.all()

        document.remove(0)
        assert document.all() == [second]

        document.undo_stack.undo()
        assert document.all() == [first, second]

    def test_out_of_range_removal_records_nothing(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        before = document.undo_stack.count()
        document.remove(5)
        document.remove(-1)
        assert document.undo_stack.count() == before

    def test_removal_frees_the_default_name(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        document.remove(0)
        document.add_roi(BOX)
        assert _names(document) == ["Replicate 2", "Replicate 1"]


class TestRename:
    def test_undo_restores_the_previous_name(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.rename(0, "Nest A")
        assert document.at(0).name == "Nest A"

        document.undo_stack.undo()
        assert document.at(0).name == "Replicate 1"

    def test_identity_and_geometry_survive(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        original = document.at(0)
        document.rename(0, "Nest A")
        renamed = document.at(0)
        assert renamed.replicate_id == original.replicate_id
        assert renamed.roi == original.roi

    def test_surrounding_whitespace_is_stripped(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.rename(0, "  Nest A  ")
        assert document.at(0).name == "Nest A"

    @pytest.mark.parametrize("name", ["", "   ", "Replicate 1"])
    def test_empty_or_unchanged_names_record_nothing(
        self, document: ReplicateDocument, name: str
    ) -> None:
        document.add_roi(BOX)
        before = document.undo_stack.count()
        document.rename(0, name)
        assert document.undo_stack.count() == before

    def test_rename_emits_a_row_edit(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        edited: list[int] = []
        document.replicate_changed.connect(edited.append)

        document.rename(1, "Nest B")

        assert edited == [1]


class TestSetROI:
    def test_undo_restores_the_previous_geometry(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.set_roi(0, OTHER_BOX)
        assert document.at(0).roi == OTHER_BOX

        document.undo_stack.undo()
        assert document.at(0).roi == BOX

    def test_identity_and_name_survive(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        original = document.at(0)
        document.set_roi(0, OTHER_BOX)
        moved = document.at(0)
        assert moved.replicate_id == original.replicate_id
        assert moved.name == original.name

    def test_geometry_is_clamped_to_the_source(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.set_roi(0, ROI(x=900, y=700, width=500, height=500))
        assert document.at(0).roi == ROI(x=900, y=700, width=100, height=100)

    def test_an_unchanged_roi_records_nothing(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        before = document.undo_stack.count()
        document.set_roi(0, BOX)
        assert document.undo_stack.count() == before

    def test_a_clamped_no_op_records_nothing(self, document: ReplicateDocument) -> None:

        document.add_roi(ROI(x=990, y=790, width=10, height=10))
        before = document.undo_stack.count()
        document.set_roi(0, ROI(x=990, y=790, width=100, height=100))
        assert document.undo_stack.count() == before


class TestSelection:









    def test_removing_above_shifts_silently_removing_selected_emits(
        self, document: ReplicateDocument
    ) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        document.select(1)
        selected = document.selected_replicate
        emitted: list[None] = []
        document.selection_changed.connect(lambda: emitted.append(None))

        document.remove(0)
        assert document.selected_replicate == selected, "the selected arena changed"
        assert emitted == [], "a row shift re-rendered the same arena"

        document.remove(0)
        assert document.selected_index is None
        assert len(emitted) == 1

    def test_an_insert_selects_the_inserted_row(self, document: ReplicateDocument) -> None:


        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        assert document.selected_index == 1

        document.remove(1)
        assert document.selected_index == 0
        document.undo_stack.undo()
        assert document.selected_index == 1

    def test_select_refuses_rows_that_do_not_exist(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.select(5)
        assert document.selected_index == 0


class TestHistory:
    def test_a_mixed_session_unwinds_and_replays(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        document.rename(0, "Nest A")
        document.set_roi(1, ROI(x=0, y=0, width=200, height=200))
        document.remove(0)
        final = document.all()
        assert document.undo_stack.count() == 5

        for _ in range(5):
            document.undo_stack.undo()
        assert len(document) == 0
        assert not document.undo_stack.canUndo()

        for _ in range(5):
            document.undo_stack.redo()
        assert document.all() == final
        assert not document.undo_stack.canRedo()

    def test_a_new_edit_discards_the_redo_branch(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.add_roi(OTHER_BOX)
        document.undo_stack.undo()
        document.add_roi(ROI(x=500, y=500, width=40, height=40))
        assert not document.undo_stack.canRedo()
        assert document.undo_stack.count() == 2

    def test_binding_a_source_discards_history(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.bind_source(640, 480)
        assert len(document) == 0
        assert not document.undo_stack.canUndo()
        assert document.source_size == (640, 480)

    def test_unbinding_discards_history(self, document: ReplicateDocument) -> None:
        document.add_roi(BOX)
        document.unbind_source()
        assert len(document) == 0
        assert not document.undo_stack.canUndo()
        assert document.source_size is None

    def test_command_text_names_the_replicate(self, document: ReplicateDocument) -> None:

        document.add_roi(BOX)
        assert document.undo_stack.undoText() == "Add Replicate 1"
        document.rename(0, "Nest A")
        assert document.undo_stack.undoText() == "Rename to Nest A"
        document.set_roi(0, OTHER_BOX)
        assert document.undo_stack.undoText() == "Resize Nest A"
        document.remove(0)
        assert document.undo_stack.undoText() == "Delete Nest A"
