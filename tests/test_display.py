"""to_qimage: uint8 as it is, a measured plane over its top, a flow field as the colour wheel."""
import os

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage  # noqa: E402

from sieve_player.window import flow_top, to_qimage  # noqa: E402


def test_a_plane_is_shown_over_its_top_and_a_field_by_direction():
    plane = np.array([[0.0, 500.0], [1000.0, 250.0]], np.float32)
    img = to_qimage(plane)
    assert img.format() == QImage.Format_Grayscale8 and img.pixelColor(0, 1).value() == 255
    assert to_qimage(plane, 2000.0).pixelColor(0, 1).value() == 128         # a running top from before; 127.5 rounds
    assert to_qimage(np.array([[7, 250]], np.uint8)).pixelColor(1, 0).value() == 250
    field = np.zeros((2, 2, 2), np.float32)
    field[0, 0], field[1, 1] = (3.0, 0.0), (0.0, -4.0)
    assert flow_top(field) == 4.0
    img = to_qimage(field)
    assert img.format() == QImage.Format_BGR888 and img.pixelColor(0, 1).value() == 0
    right, up = img.pixelColor(0, 0), img.pixelColor(1, 1)
    assert right.hue() != up.hue() and up.value() == 255 and 0 < right.value() < 255


def _stopped_window(tmp_path, tools, shown):
    """A paused window over a six-row clip whose worker is stopped, so the test's thread computes every row."""
    from PySide6.QtWidgets import QApplication
    from sieve_player import document as D
    from sieve_player.window import PlayerWindow
    from tests.test_crop import clip

    QApplication.instance() or QApplication([])
    doc = D.from_tools(tools, clip(tmp_path / "v.avi"))
    doc.display = shown
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", tools)
    win.worker.stop()
    win.timer.stop()                                            # it opens playing; the test says when it plays
    win.graph.halt, win.window_, win.playing = False, (0, win.count), False
    return win


def test_a_proxy_is_the_display_s_alone_and_goes_with_the_shown_key(tmp_path):
    from tools import gray, threshold
    win = _stopped_window(tmp_path, [gray, threshold], "threshold")
    exact = win.graph.compute("threshold", 0)
    win.graph.memo.limit = 2 * exact.nbytes                     # two rows of six fit
    assert win._show(0) and not win.display.proxied and 0 in win.display._proxies
    assert win.graph.peek(0) is exact
    win.graph.memo.empty()
    assert win.graph.peek(0) is None and not win._show(0)       # stopped, the row is asked for, never the proxy
    win.playing = True
    assert win._show(0) and win.display.proxied and win.graph.peek(0) is None
    win.doc.node("threshold").params = {**win.doc.node("threshold").params, "thresh": 7}
    win.graph.sync()
    assert not win._show(0) and win.display._proxies == {}
    win.playing = False
    win.close()


def test_a_loop_makes_no_proxy_until_the_memo_lets_go(tmp_path):
    from tools import gray
    win = _stopped_window(tmp_path, [gray], "gray")
    for row in range(win.count):
        win.graph.compute("gray", row)
        assert win._show(row)
    assert win.display._proxies == {}
    win.graph.memo.evictions += 1                               # the memo let a plane go: the loop did not fit after all
    assert win._show(0) and 0 in win.display._proxies
    win.close()
