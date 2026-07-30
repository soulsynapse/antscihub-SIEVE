"""The table model as an edit path into the document.

The model is the second way a replicate can be mutated (the first is a drag on
the video), and the rule is that it owns none of the mutation: every accepted
edit has to appear on the undo stack, and every rejected edit has to leave the
document untouched rather than half-applied.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QModelIndex, Qt

from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.types import ROI
from sieve.gui.document import ReplicateDocument
from sieve.gui.replicate_table import Column, ReplicateTableModel

pytestmark = pytest.mark.gui

BOX = ROI(x=10, y=20, width=100, height=80)

EDIT = Qt.ItemDataRole.EditRole
DISPLAY = Qt.ItemDataRole.DisplayRole


@pytest.fixture
def model(document: ReplicateDocument) -> ReplicateTableModel:
    """A model over a document holding one replicate."""
    document.add_roi(BOX)
    return ReplicateTableModel(document)


def _cell(model: ReplicateTableModel, column: Column, row: int = 0) -> QModelIndex:
    return model.index(row, int(column))


class TestShape:
    def test_rows_track_the_document(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        assert model.rowCount() == 1
        document.add_roi(ROI(x=200, y=200, width=30, height=30))
        assert model.rowCount() == 2

    def test_children_have_no_rows(self, model: ReplicateTableModel) -> None:
        assert model.rowCount(_cell(model, Column.NAME)) == 0
        assert model.columnCount(_cell(model, Column.NAME)) == 0

    def test_headers_are_the_column_titles(self, model: ReplicateTableModel) -> None:
        titles = [
            model.headerData(int(column), Qt.Orientation.Horizontal, DISPLAY) for column in Column
        ]
        assert titles == ["Replicate", "Group", "X", "Y", "W", "H", "Pixels"]

    def test_row_numbers_are_one_based(self, model: ReplicateTableModel) -> None:
        assert model.headerData(0, Qt.Orientation.Vertical, DISPLAY) == 1

    def test_the_derived_columns_are_read_only(self, model: ReplicateTableModel) -> None:
        editable = Qt.ItemFlag.ItemIsEditable
        assert model.flags(_cell(model, Column.NAME)) & editable
        assert model.flags(_cell(model, Column.WIDTH)) & editable
        assert not model.flags(_cell(model, Column.AREA)) & editable
        assert not model.flags(_cell(model, Column.GROUP)) & editable

    def test_an_invalid_index_has_no_flags(self, model: ReplicateTableModel) -> None:
        assert model.flags(QModelIndex()) == Qt.ItemFlag.NoItemFlags


class TestReading:
    def test_geometry_is_shown_in_source_pixels(self, model: ReplicateTableModel) -> None:
        assert model.data(_cell(model, Column.X), DISPLAY) == 10
        assert model.data(_cell(model, Column.Y), DISPLAY) == 20
        assert model.data(_cell(model, Column.WIDTH), DISPLAY) == 100
        assert model.data(_cell(model, Column.HEIGHT), DISPLAY) == 80

    def test_area_is_grouped_for_display_and_numeric_for_editing(
        self, model: ReplicateTableModel
    ) -> None:
        assert model.data(_cell(model, Column.AREA), DISPLAY) == "8,000"
        assert model.data(_cell(model, Column.AREA), EDIT) == 8000

    def test_a_row_past_the_end_reads_as_nothing(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        """Views can outlive a removal by one repaint; reading must not raise."""
        stale = _cell(model, Column.NAME)
        document.remove(0)
        assert model.data(stale, DISPLAY) is None


class TestEditing:
    def test_a_rename_lands_on_the_undo_stack(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        assert model.setData(_cell(model, Column.NAME), "Nest A", EDIT)
        assert document.at(0).name == "Nest A"

        document.undo_stack.undo()
        assert document.at(0).name == "Replicate 1"

    @pytest.mark.parametrize(
        ("column", "value", "expected"),
        [
            (Column.X, 40, ROI(x=40, y=20, width=100, height=80)),
            (Column.Y, 50, ROI(x=10, y=50, width=100, height=80)),
            (Column.WIDTH, 25, ROI(x=10, y=20, width=25, height=80)),
            (Column.HEIGHT, 25, ROI(x=10, y=20, width=100, height=25)),
        ],
    )
    def test_a_geometry_edit_lands_on_the_undo_stack(
        self,
        model: ReplicateTableModel,
        document: ReplicateDocument,
        column: Column,
        value: int,
        expected: ROI,
    ) -> None:
        assert model.setData(_cell(model, column), value, EDIT)
        assert document.at(0).roi == expected

        document.undo_stack.undo()
        assert document.at(0).roi == BOX

    def test_a_numeric_string_is_accepted(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        """Qt's default line-edit delegate hands back text, not an int."""
        assert model.setData(_cell(model, Column.WIDTH), "25", EDIT)
        assert document.at(0).roi.width == 25

    @pytest.mark.parametrize("column", [Column.WIDTH, Column.HEIGHT])
    @pytest.mark.parametrize("value", [0, -5])
    def test_a_zero_or_negative_extent_is_rejected(
        self,
        model: ReplicateTableModel,
        document: ReplicateDocument,
        column: Column,
        value: int,
    ) -> None:
        before = document.undo_stack.count()
        assert not model.setData(_cell(model, column), value, EDIT)
        assert document.at(0).roi == BOX
        assert document.undo_stack.count() == before

    @pytest.mark.parametrize("column", [Column.X, Column.Y])
    def test_a_negative_origin_is_rejected(
        self, model: ReplicateTableModel, document: ReplicateDocument, column: Column
    ) -> None:
        before = document.undo_stack.count()
        assert not model.setData(_cell(model, column), -1, EDIT)
        assert document.at(0).roi == BOX
        assert document.undo_stack.count() == before

    @pytest.mark.parametrize("value", ["", "wide", None, 3.5j])
    def test_a_non_integer_is_rejected(
        self, model: ReplicateTableModel, document: ReplicateDocument, value: object
    ) -> None:
        before = document.undo_stack.count()
        assert not model.setData(_cell(model, Column.WIDTH), value, EDIT)
        assert document.undo_stack.count() == before

    @pytest.mark.parametrize("value", ["", "   ", "Replicate 1"])
    def test_a_rename_the_document_refuses_is_reported_as_no_change(
        self, model: ReplicateTableModel, document: ReplicateDocument, value: str
    ) -> None:
        """Empty, whitespace, and unchanged are all names the document drops.

        `True` here would tell Qt the model changed, and the user would see a
        cell repaint as if the rename had been taken.
        """
        before = document.undo_stack.count()
        assert not model.setData(_cell(model, Column.NAME), value, EDIT)
        assert document.at(0).name == "Replicate 1"
        assert document.undo_stack.count() == before

    @pytest.mark.parametrize("column", [Column.AREA, Column.GROUP])
    def test_a_derived_column_refuses_edits(
        self, model: ReplicateTableModel, column: Column
    ) -> None:
        assert not model.setData(_cell(model, column), 1234, EDIT)

    def test_only_the_edit_role_writes(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        assert not model.setData(_cell(model, Column.NAME), "Nest A", DISPLAY)
        assert document.at(0).name == "Replicate 1"

    def test_an_invalid_index_refuses_edits(self, model: ReplicateTableModel) -> None:
        assert not model.setData(QModelIndex(), "Nest A", EDIT)


class TestEquivalenceGroups:
    def _graphed(self, document: ReplicateDocument) -> None:
        """Give the document a one-node graph and a second replicate."""
        document.add_roi(ROI(x=200, y=200, width=100, height=80))
        node = Node(node_id="n1", filter_id="threshold", version="1.0.0", params={"level": 0.5})
        document.set_pipeline(Pipeline(nodes=(node,)))

    def test_identical_replicates_share_a_group_and_a_deviation_splits_them(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        # The column's whole job: twelve arenas configured once read as one
        # group, and the one that had to differ is visible without opening it.
        self._graphed(document)
        assert model.data(_cell(model, Column.GROUP, 0), DISPLAY) == 1
        assert model.data(_cell(model, Column.GROUP, 1), DISPLAY) == 1

        document.apply_replace(1, document.at(1).with_override("n1", {"level": 0.9}))

        assert model.data(_cell(model, Column.GROUP, 1), DISPLAY) == 2

    def test_the_number_is_derived_rather_than_stored(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        # Pinning a parameter to the value it was already inheriting must not
        # split the group — the number tracks what a replicate *runs with*, not
        # whether anyone has configured it. A group cached at the moment an
        # override was written would answer this the other way and stay wrong.
        self._graphed(document)
        document.apply_replace(1, document.at(1).with_override("n1", {"level": 0.5}))

        assert model.data(_cell(model, Column.GROUP, 1), DISPLAY) == 1

    def test_a_new_graph_repaints_the_whole_column(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        # Not one row: the numbers are positional, so a change that moves any
        # replicate shifts every number below it. A per-row signal would leave
        # stale numbers painted above and below the edit.
        document.add_roi(ROI(x=200, y=200, width=100, height=80))
        spans: list[tuple[int, int, int, int]] = []

        def record(top_left: QModelIndex, bottom_right: QModelIndex, roles: object = None) -> None:
            del roles
            spans.append(
                (top_left.row(), bottom_right.row(), top_left.column(), bottom_right.column())
            )

        model.dataChanged.connect(record)
        document.set_pipeline(
            Pipeline(nodes=(Node(node_id="n1", filter_id="threshold", version="1.0.0"),))
        )

        assert spans == [(0, 1, int(Column.GROUP), int(Column.GROUP))]


class TestNotification:
    def test_an_added_row_resets_the_model(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        resets: list[None] = []
        model.modelReset.connect(lambda: resets.append(None))
        document.add_roi(ROI(x=200, y=200, width=30, height=30))
        assert len(resets) == 1

    def test_an_in_place_edit_repaints_the_whole_row(
        self, model: ReplicateTableModel, document: ReplicateDocument
    ) -> None:
        """The area column is derived, so a width edit dirties more than its cell."""
        spans: list[tuple[int, int, int]] = []

        def record(top_left: QModelIndex, bottom_right: QModelIndex, roles: object = None) -> None:
            del roles
            spans.append((top_left.row(), top_left.column(), bottom_right.column()))

        model.dataChanged.connect(record)
        document.set_roi(0, ROI(x=10, y=20, width=50, height=80))
        assert spans == [(0, 0, len(Column) - 1)]
