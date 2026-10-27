"""One test per `Check: a test` line under "Navigation", "Tab menu" and "Buttons" in spec/canvas.md.

The tools here are stand-ins with fixed types, as in test_document.py, so a change to a real
tool's EXPECTS or PRODUCES is not a change to these tests: they check the canvas's logic, not the
catalogue. A wire grown into space has no public setter; `_pending` is the one private seam read.
"""
import json
import os
from types import SimpleNamespace as Tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import canvas as canvas_mod  # noqa: E402
from sieve_player.canvas import Canvas  # noqa: E402

gray = Tool(NAME="gray", KIND="frame", EXPECTS="bgr", PRODUCES="gray", DEFAULTS={})
thresh = Tool(NAME="thresh", KIND="frame", EXPECTS="gray", PRODUCES="mask", DEFAULTS={})
passthru = Tool(NAME="passthru", KIND="frame", EXPECTS=("bgr", "gray"), PRODUCES="same", DEFAULTS={})
sel = Tool(NAME="sel", KIND="frame", EXPECTS=None, PRODUCES=D.PATH, DEFAULTS={}, select=lambda folder, p: None)
reader = Tool(NAME="reader", KIND="frame", EXPECTS="bgr", PRODUCES="mask", DEFAULTS={}, PATHS={"settings": lambda p: {}})
TOOLS = {t.NAME: t for t in (gray, thresh, passthru, sel, reader)}


def canvas_with(doc):
    QApplication.instance() or QApplication([])
    canvas = Canvas(TOOLS)
    canvas.resize(400, 300)
    canvas.set_document(doc)
    return canvas


def test_pan_and_zoom_are_not_in_the_document(tmp_path):
    doc = D.from_tools([gray, thresh])
    before = json.dumps(doc.to_dict(), sort_keys=True)
    canvas = canvas_with(doc)
    view = (QPointF(canvas.pan), canvas.zoom)
    canvas.pan_by(QPointF(30, 40))
    canvas.set_zoom(2.0, QPointF(10, 10))
    canvas.frame()
    assert (canvas.pan, canvas.zoom) != view
    D.save(doc, tmp_path / "doc.json")
    with open(tmp_path / "doc.json", encoding="utf-8") as f:
        assert json.dumps(json.load(f), sort_keys=True) == before


def _press(canvas, at, button=Qt.LeftButton):
    e = QMouseEvent(QEvent.MouseButtonPress, at, canvas.mapToGlobal(at.toPoint()), button, button, Qt.NoModifier)
    canvas.mousePressEvent(e)
    e = QMouseEvent(QEvent.MouseButtonRelease, at, canvas.mapToGlobal(at.toPoint()), button, Qt.NoButton, Qt.NoModifier)
    canvas.mouseReleaseEvent(e)


def test_a_button_does_what_its_key_does_and_starts_no_gesture():
    doc = D.from_tools([gray])
    canvas = canvas_with(doc)
    by_key = {key: i for i, (_, _, key) in enumerate(canvas_mod.BUTTONS)}
    frame_at, tab_at, delete_at = (canvas.button_rect(by_key[k]).center() for k in (Qt.Key_H, Qt.Key_Tab, Qt.Key_Delete))
    # frame: the view moves as H would
    view = (QPointF(canvas.pan), canvas.zoom)
    _press(canvas, frame_at)
    assert (canvas.pan, canvas.zoom) != view
    # the column covers the canvas: a node under the delete button in document space is neither
    # selected nor moved by a left press there, and a middle press there does not pan
    node = doc.node("gray")
    under = canvas.to_doc(delete_at)
    node.pos = (under.x() - canvas_mod.NODE_W / 2, under.y() - canvas_mod.NODE_H / 2)
    assert canvas.node_at(under) is node
    canvas.select([])
    state = (list(canvas.selected), node.pos, QPointF(canvas.pan))
    _press(canvas, delete_at)
    _press(canvas, delete_at, Qt.MiddleButton)
    assert (list(canvas.selected), node.pos, canvas.pan) == state and len(doc.nodes) == 2
    # the Tab menu opens; closing it places nothing
    _press(canvas, tab_at)
    assert canvas.findChildren(canvas_mod.TabMenu)
    canvas.close_menu()
    assert not canvas.findChildren(canvas_mod.TabMenu) and len(doc.nodes) == 2
    # delete: the selection goes, as Delete would; with nothing selected the button does nothing
    canvas.select([node.id])
    _press(canvas, delete_at)
    assert [n.id for n in doc.nodes] == [D.VIDEO_TOOL]
    _press(canvas, delete_at)
    assert [n.id for n in doc.nodes] == [D.VIDEO_TOOL]


def test_the_video_node_is_in_the_menu_only_while_the_document_lacks_one():
    doc = D.from_tools([])
    canvas = canvas_with(doc)
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL]      # greyed, with a reason
    canvas.select([D.VIDEO_TOOL])
    canvas.delete_selected()
    assert doc.video_node() is None
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL] == ""
    node = canvas.place(D.VIDEO_TOOL, QPointF(10, 10))
    assert doc.video_node() is node
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL]


def test_a_wire_let_go_in_space_offers_what_its_loose_end_may_join():
    doc = D.from_tools([gray, thresh, reader])
    canvas = canvas_with(doc)

    def live():
        return {n for n, err in canvas.menu_entries() if not err}

    canvas._pending = ("out", "gray", None)             # a gray output: takers of gray, a pass-through among them
    assert live() == {"thresh", "passthru"}
    canvas._pending = ("in", "thresh", D.INPUT)         # a gray input: producers of gray, a pass-through among them
    assert live() == {"gray", "passthru"}
    canvas._pending = ("in", "reader", "settings")      # a path input: a selector, never a pass-through
    assert live() == {"sel"}
    doc.add_node("sel", (0, 400))
    canvas._pending = ("out", "sel", None)              # a path output: path inputs; the video node is greyed while one exists
    assert live() == {"reader"}
    canvas._pending = None
