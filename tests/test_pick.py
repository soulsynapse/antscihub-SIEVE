"""A click on the frame: offered to the drawers whose pick() claims it, last drawn first, the answer landing in the
document through the card; one that raises is dropped and said; a right click walks the display flag back."""
import os
import time
from types import SimpleNamespace as Tool

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.registry import FACETS, hint  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tools import gray  # noqa: E402


def drawer(name, pick):
    def settings(parent=None):
        from sieve_player import ParamWidget
        w = ParamWidget(parent)
        w.add_text("choice", "")
        return w
    return Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", DEFAULTS={"choice": ""},
                run=lambda f, r, p: f(r), draw=lambda *a: None, pick=pick, settings=settings)


def shown(win, *drawn, timeout=10.0):
    """Waits for the frame and for each node in `drawn` to have a result on it, as the walk brings them in."""
    def ready():
        return win.display._pix is not None and all(win.display.frame_results.get(n) is not None for n in drawn)
    t = time.perf_counter()
    while not ready() and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        win.goto(win.row, commit=True)
        time.sleep(0.005)
    assert ready()


def click(win, button=Qt.LeftButton):
    x, y, w, h = win.display.frame_rect()
    QTest.mouseClick(win.display, button, Qt.NoModifier, QPoint(x + w // 2, y + h // 2))
    QApplication.processEvents()


def test_a_click_is_offered_last_drawn_first_a_raising_pick_is_dropped_and_said_and_the_answer_lands_through_the_card(tmp_path):
    assert "pick" in FACETS and "point" in hint("pick") and "None" in hint("pick")
    QApplication.instance() or QApplication([])
    seen = []
    quiet = drawer("quiet", lambda point, shape, row, result, params: seen.append(("quiet", shape)))
    loud = drawer("loud", lambda point, shape, row, result, params: {"choice": f"{int(point[0])},{int(point[1])}"})
    boom = drawer("boom", lambda *a: 1 / 0)
    tools = [gray, quiet, loud, boom]
    doc = D.from_tools(tools, clip(tmp_path / "v.avi"))
    doc.connect("gray", "boom")
    doc.display = "quiet"
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", tools)
    win.resize(640, 480)
    shown(win, "quiet", "loud", "boom")
    key = win.graph.key("loud")
    click(win)                                                          # boom is drawn last, so asked first: it raises and is dropped; loud is next and claims
    assert win.graph.standing("boom").startswith("pick() raised: ZeroDivisionError") and "boom" not in [nid for nid, *_ in win.display.drawers]
    assert win.doc.node("loud").params["choice"] == "32,24" and win.pane.widget("loud").params()["choice"] == "32,24"
    assert win.graph.key("loud") != key and seen == []
    loud.pick = lambda *a: None
    click(win)
    assert seen == [("quiet", (48, 64))] and win.doc.node("quiet").params["choice"] == ""   # unclaimed: nothing lands
    win.close()


def test_a_right_click_walks_the_display_flag_back_skipping_a_node_that_is_gone():
    QApplication.instance() or QApplication([])
    a, b, c = (drawer(n, None) for n in ("a", "b", "c"))
    tools = [gray, a, b, c]
    win = PlayerWindow(tools, "t")
    assert win.doc.display == "c"                                      # from_tools flags the last frame tool
    for nid in ("a", "b", "c"):
        win.canvas.set_flag(nid)
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == "b"
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == "a"
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == "c"
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == "c"                                      # nothing before: nothing to do
    win.canvas.set_flag("a")
    win.canvas.set_flag("b")
    win.canvas.set_flag("c")
    win.canvas.select(["b"])
    win.canvas.delete_selected()
    win.canvas.changed.emit()
    assert win.doc.display == "c"
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == "a"                                      # b is gone, skipped
    win.set_document(D.from_tools(tools))
    QTest.mouseClick(win.display, Qt.RightButton)
    assert win.doc.display == win._shown_last                         # a loaded document starts with no past
    win.close()
