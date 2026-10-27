"""One test per `Check: a test` line under "Navigation" in spec/canvas.md."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
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
