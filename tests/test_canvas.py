"""One test per `Check: a test` line under "Navigation" and "Buttons" in spec/canvas.md."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import canvas as canvas_mod  # noqa: E402
from sieve_player.canvas import Canvas  # noqa: E402


def test_pan_and_zoom_are_not_in_the_document(tmp_path):
    QApplication.instance() or QApplication([])
    doc = D.Document()
    doc.add_node(D.VIDEO_TOOL, (0, 0))
    doc.add_node("gray", (0, 100))
    doc.connect("video", "gray")
    before = json.dumps(doc.to_dict(), sort_keys=True)
    canvas = Canvas({})
    canvas.resize(400, 300)
    canvas.set_document(doc)
    canvas.pan_by(QPointF(30, 40))
    canvas.set_zoom(2.0, QPointF(10, 10))
    canvas.frame()
    assert (canvas.pan, canvas.zoom) != (QPointF(16, 16), 1.0)
    path = tmp_path / "doc.json"
    D.save(doc, path)
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    assert json.dumps(d, sort_keys=True) == before
    assert set(d) == {"version", "video", "display", "nodes", "wires"}
    assert all(set(n) == {"id", "tool", "params", "pos"} for n in d["nodes"])


def _press(canvas, at, button=Qt.LeftButton):
    e = QMouseEvent(QEvent.MouseButtonPress, at, canvas.mapToGlobal(at.toPoint()), button, button, Qt.NoModifier)
    canvas.mousePressEvent(e)
    e = QMouseEvent(QEvent.MouseButtonRelease, at, canvas.mapToGlobal(at.toPoint()), button, Qt.NoButton, Qt.NoModifier)
    canvas.mouseReleaseEvent(e)


def test_a_button_does_what_its_key_does_and_starts_no_gesture():
    QApplication.instance() or QApplication([])
    doc = D.Document()
    doc.add_node(D.VIDEO_TOOL, (0, 0))
    gray = doc.add_node("gray", (0, 100))
    canvas = Canvas({})
    canvas.resize(400, 300)
    canvas.set_document(doc)
    by_key = {key: i for i, (_, _, key) in enumerate(canvas_mod.BUTTONS)}
    # frame: the view moves as H would
    view = (QPointF(canvas.pan), canvas.zoom)
    _press(canvas, canvas.button_rect(by_key[Qt.Key_H]).center())
    assert (canvas.pan, canvas.zoom) != view and canvas._drag is None
    # a press on the column selects nothing and draws no box, whatever lies beneath in document space
    canvas.select([gray.id])
    _press(canvas, canvas.button_rect(by_key[Qt.Key_Tab]).center(), Qt.MiddleButton)
    assert canvas.selected == [gray.id] and canvas._drag is None
    # the Tab menu opens; Escape closes it with nothing placed
    _press(canvas, canvas.button_rect(by_key[Qt.Key_Tab]).center())
    assert canvas._menu is not None
    canvas.close_menu()
    assert len(doc.nodes) == 2
    # delete: the selection goes, as Delete would; with nothing selected the button does nothing
    _press(canvas, canvas.button_rect(by_key[Qt.Key_Delete]).center())
    assert [n.id for n in doc.nodes] == ["video"]
    _press(canvas, canvas.button_rect(by_key[Qt.Key_Delete]).center())
    assert [n.id for n in doc.nodes] == ["video"]


def test_the_video_node_is_in_the_menu_only_while_the_document_lacks_one():
    QApplication.instance() or QApplication([])
    doc = D.Document()
    doc.add_node(D.VIDEO_TOOL, (0, 0))
    canvas = Canvas({})
    canvas.resize(400, 300)
    canvas.set_document(doc)
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL]      # greyed, with a reason
    canvas.select([D.VIDEO_TOOL])
    canvas.delete_selected()
    assert doc.video_node() is None
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL] == ""
    node = canvas.place(D.VIDEO_TOOL, QPointF(10, 10))
    assert doc.video_node() is node
    assert dict(canvas.menu_entries())[D.VIDEO_TOOL]


def test_a_wire_let_go_in_space_offers_what_its_loose_end_may_join():
    QApplication.instance() or QApplication([])
    from sieve_player.registry import discover
    tools = {e.name: e.module for e in discover("tools") if e.ok}
    doc = D.from_tools([tools["gray"], tools["threshold"], tools["inrange"]])
    canvas = Canvas(tools)
    canvas.set_document(doc)

    def live():
        return {n for n, err in canvas.menu_entries() if not err}

    canvas._pending = ("out", "gray", None)             # a gray output: takers of gray, so not gray itself
    assert {"threshold", "rescale"} <= live() and "gray" not in live()
    canvas._pending = ("in", "threshold", D.INPUT)      # a gray input: producers of gray, a pass-through among them
    assert {"gray", "rescale"} <= live() and not {"threshold", "inrange", "file"} & live()   # masks are not gray
    canvas._pending = ("in", "inrange", "settings")     # a path input: a selector, never a pass-through
    assert "file" in live() and "rescale" not in live()
    canvas._pending = None
