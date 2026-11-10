"""The Tab menu: entries grouped by category in the given order with a description each, the typed
text matching group, name and description and emptying groups away, and the list sized to its rows."""
import os
from types import SimpleNamespace as Tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import registry, theme  # noqa: E402
from sieve_player.menu import MENU_ROWS, UNLOADED, TabMenu  # noqa: E402

gray = Tool(NAME="gray", EXPECTS="bgr", PRODUCES="gray")
reduce = Tool(NAME="reduce", EXPECTS=("gray", "mask"), PRODUCES="signal")
thin = Tool(NAME="thin", EXPECTS="mask", PRODUCES="mask", __doc__="Frame tool: a mask thinned to its skeleton; mask in, mask out.\n\nMore below.")


def menu(entries):
    QApplication.instance() or QApplication([])
    info = {t.NAME: (registry.category(t), registry.description(t), registry.signature(t)) for t in (gray, reduce, thin)}
    info["bad"] = (UNLOADED, "ImportError: no", "")
    return TabMenu(entries, info, registry.CATEGORIES, None)


def test_entries_group_by_category_with_a_description_and_flatten_to_the_typed_text():
    m = menu([("gray", ""), ("reduce", ""), ("thin", ""), ("bad", "ImportError: no")])
    assert m.shown() == [("convert", ["gray"]), ("transform", ["thin"]), ("measure", ["reduce"]), (UNLOADED, ["bad"])]
    assert m.description("thin") == "a mask thinned to its skeleton; mask in, mask out" and m.description("gray") == ""
    assert m.list.currentItem().data(Qt.UserRole) == "gray" and m.item_of("bad").flags() == Qt.NoItemFlags
    m.edit.setText("reduce")
    assert m.shown() == [("measure", ["reduce"])] and m.list.currentItem().data(Qt.UserRole) == "reduce"
    m.edit.setText("skeleton")     # the description matches
    assert m.shown() == [("transform", ["thin"])]
    m.edit.setText("measure")      # and so does the group
    assert m.shown() == [("measure", ["reduce"])]
    m.edit.setText("zzz")
    assert m.shown() == [] and m.item_of("gray") is None


def test_the_list_is_as_tall_as_its_rows_up_to_the_most_shown():
    m = menu([("gray", ""), ("reduce", "")])
    assert m.list.count() == 4 and m.list.height() == sum(m.list.sizeHintForRow(i) for i in range(4)) + 2
    many = menu([(f"t{i}", "") for i in range(40)])
    assert many.list.count() > MENU_ROWS and many.list.height() == sum(many.list.sizeHintForRow(i) for i in range(MENU_ROWS)) + 2
    assert menu([]).list.height() == theme.ROW_H
