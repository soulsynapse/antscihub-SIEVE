"""The geometry utility: a video opened at the plate the player's Decoder reads, seeked to any frame,
a view zoomed no smaller than fit and shown at 100%, the shapes edited by their handles, and the
table that lists, names and deletes them."""
import json
import math
import os

import cv2
import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.decoder import Decoder  # noqa: E402
from tools.region import load_geometry  # noqa: E402
from utilities.geometry import shapes as sh  # noqa: E402
from utilities.geometry.editor import Editor  # noqa: E402
from utilities.geometry.video import EXACT_DECODE_BELOW  # noqa: E402
from utilities.geometry.window import GeometryWindow  # noqa: E402

H, W, N = 48, 64, EXACT_DECODE_BELOW + 16    # past the forward-decoded opening, so the last frame is a seek


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    path = tmp_path_factory.mktemp("g") / "clip.avi"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    for i in range(N):
        w.write(np.full((H, W, 3), 3 * i, np.uint8))
    w.release()
    return str(path)


@pytest.fixture
def window(clip):
    QApplication.instance() or QApplication([])
    win = GeometryWindow(clip)
    yield win
    win.close()


def test_the_plate_is_the_clip_and_the_decoders_shape_and_the_seek_bar_reaches_the_last_frame(window, clip):
    d = Decoder(clip)
    try:
        assert window.plate == (H, W) == d.read(0).shape[:2]
    finally:
        d.close()
    window.seek_bar.setValue(N - 1)
    assert window.index == N - 1 and window.frame_label.text().startswith(f"{N - 1} / {N - 1}")
    assert abs(int(window.frame[0, 0, 0]) - 3 * (N - 1)) <= 2
    window.seek_bar.setValue(5)
    assert abs(int(window.frame[0, 0, 0]) - 15) <= 2


def test_zooming_out_stops_at_fit_and_100_percent_is_one_to_one(window):
    window.show()
    window.resize(900, 700)
    QApplication.processEvents()
    view = window.view
    fit = view.fit_scale()
    assert fit > 1

    def wheel(notches):
        at = QPointF(view.viewport().rect().center())
        e = QWheelEvent(at, view.viewport().mapToGlobal(at), QPoint(), QPoint(0, 120 * notches),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier, Qt.ScrollPhase.NoScrollPhase, False)
        QApplication.sendEvent(view.viewport(), e)

    wheel(3)
    assert view.scale_now() == pytest.approx(fit * 1.25 ** 3)
    wheel(-10)
    assert view.scale_now() == pytest.approx(fit)
    window.actual_button.click()
    assert view.scale_now() == 1
    window.fit_button.click()
    assert view.scale_now() == pytest.approx(fit)


def test_a_square_stays_square_a_rectangle_turns_a_circle_grows_from_its_rim_and_a_polygon_gains_and_loses_vertices():
    sq = sh.square_from_diagonal("s", (10, 10), (30, 30))
    assert sq.w == pytest.approx(20) and sq.angle == pytest.approx(0)
    by_corner = sq.dragged((1, 1), (45, 38))
    assert by_corner.w == by_corner.h == pytest.approx(35)
    assert by_corner.vertices()[0] == pytest.approx((10, 10))
    by_edge = sq.dragged((0, -1), (20, 0))
    assert by_edge.w == by_edge.h == pytest.approx(30)
    assert by_edge.vertices()[3] == pytest.approx((5, 30))

    rect = sh.rectangle_from_corners("r", (0, 0), (40, 20)).rotated(math.pi / 2)
    assert [tuple(v) for v in rect.vertices()] == [pytest.approx(v) for v in [(30, -10), (30, 30), (10, 30), (10, -10)]]

    c = sh.circle_from_centre("c", (50, 50), (60, 50))
    assert c.dragged("rim", (50, 75)).r == pytest.approx(25)
    fit = sh.circle_through("f", *[(7 + 5 * math.cos(t), -3 + 5 * math.sin(t)) for t in (0.3, 2.0, 4.1)])
    assert (fit.cx, fit.cy, fit.r) == pytest.approx((7, -3, 5))
    assert sh.circle_through("f", (0, 0), (1, 1), (2, 2)) is None

    tri = sh.Polygon("p", ((0, 0), (10, 0), (0, 10)))
    quad = tri.with_vertex(tri.edge_near((6, 5), 1), (6, 5))
    assert quad.points == ((0, 0), (10, 0), (6, 5), (0, 10))
    assert quad.without_vertex(2) == tri and tri.without_vertex(0) == tri


def test_no_shape_drawn_or_edited_within_the_plate_leaves_it_and_each_loads_through_region(tmp_path):
    ph, pw = 100, 200
    ed = Editor(plate=(ph, pw))

    def gesture(mode, *points):
        ed.set_mode(mode)
        for a in points:
            ed.press(a, 1)
            ed.release(a, 1)

    def drag(a, b):
        ed.set_mode("select")
        ed.press(a, 1)
        ed.move(b, 1)
        ed.release(b, 1)

    def loads():
        path = tmp_path / "g.json"
        path.write_text(json.dumps({"plate": [ph, pw], "shapes": [s.primitive() for s in ed.shapes]}), encoding="utf-8")
        assert len(load_geometry(str(path))["shapes"]) == len(ed.shapes)

    gesture("circle", (50, 50), (65, 50))
    gesture("square", (110, 40), (125, 70))
    gesture("circle3", (190, 90), (199, 50), (150, 99))
    gesture("square", (5, 95), (195, 5))
    assert len(ed.shapes) == 4 and all(ed.within(s) for s in ed.shapes)
    circle, square = ed.shapes[0], ed.shapes[1]
    assert square.angle != pytest.approx(0)
    ed.shapes = [circle, square]
    loads()
    for name in (circle.name, square.name):
        for far, side in (((-1e4, 0), 0), ((0, -1e4), 1), ((1e4, 0), 2), ((0, 1e4), 3)):
            c = ed.shape(name).centre
            drag(c, (c[0] + far[0], c[1] + far[1] + 3))
            box = ed.shape(name).box()
            assert ed.within(ed.shape(name)) and box[side] == pytest.approx((0, 0, pw, ph)[side], abs=1e-6)
            loads()
    ed.selected = square.name
    drag(ed.shape(square.name).handles()[(1, 1)], (1e4, 1e4))
    ed.selected = circle.name
    drag(ed.shape(circle.name).handles()["rim"], (-1e4, 50))
    ed.selected = square.name
    s = ed.shape(square.name)
    drag(ed.rotation_handle(1), (s.cx + 300, s.cy))
    assert all(ed.within(s) for s in ed.shapes)
    loads()


def test_a_draw_each_drag_and_a_delete_are_one_undo_step_each():
    ed = Editor(plate=(100, 200))
    ed.set_mode("square")
    for a in ((20, 20), (40, 40)):
        ed.press(a, 1)
        ed.release(a, 1)
    drawn = ed.shapes[0]
    ed.set_mode("select")
    for a, b in (((30, 30), (60, 50)), ((60, 50), (90, 70))):
        ed.press(a, 1)
        for t in (0.25, 0.5, 1):
            ed.move((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), 1)
        ed.release(b, 1)
        if a == (30, 30):
            first = ed.shapes[0]
    ed.delete_selected()
    assert ed.shapes == []
    ed.undo()
    ed.undo()
    assert ed.shapes == [first] and first.centre == pytest.approx((60, 50))
    ed.undo()
    assert ed.shapes == [drawn]
    ed.redo()
    assert ed.shapes == [first]


def test_the_table_selects_with_the_frame_refuses_a_taken_name_and_deletes(window):
    ed, table = window.editor, window.table
    window.show()
    window.activateWindow()
    assert QTest.qWaitForWindowActive(window)
    for mode, a, b in (("circle", (10, 10), (15, 10)), ("rectangle", (30, 20), (50, 40))):
        ed.set_mode(mode)
        for p in (a, b):
            ed.press(p, 1)
            ed.release(p, 1)
    first, second = (s.name for s in ed.shapes)
    assert table.rowCount() == 2 and [table.name_at(r) for r in range(2)] == [first, second]
    ed.set_mode("select")
    table.selectRow(1)
    assert ed.selected == second
    ed.select(first)
    assert {i.row() for i in table.selectedItems()} == {0}
    table.selectRow(1)
    table.item(1, 0).setText(first)
    assert [s.name for s in ed.shapes] == [first, second] and table.item(1, 0).text() == second
    assert table.marked[0] == second and first in window.message.text()
    table.item(1, 0).setText("arena")
    assert ed.shapes[1].name == ed.selected == "arena" and table.marked is None
    QTest.keyClick(table, Qt.Key.Key_Delete)
    assert table.rowCount() == 1 and [s.name for s in ed.shapes] == [first]
