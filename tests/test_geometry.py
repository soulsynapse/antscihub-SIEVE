"""The geometry utility: a video opened at the plate the player's Decoder reads, seeked to any frame,
a view zoomed no smaller than fit and shown at 100%, the shapes edited by their handles, and the
table that lists, names, orders and deletes them, the stamp groups, the file saved and reopened, and the library of kept configurations."""
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
from tools.region import load_geometry, pick as region_pick  # noqa: E402
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


def test_new_shapes_take_the_stems_least_free_index(window):
    ed = window.editor
    window.stem_field.setText("dish")
    ed.set_mode("circle")

    def circle(x):
        for p in ((x, 20), (x + 5, 20)):
            ed.press(p, 1)
            ed.release(p, 1)

    for x in (10, 25, 40):
        circle(x)
    assert [s.name for s in ed.shapes] == ["dish-1", "dish-2", "dish-3"]
    ed.select("dish-2")
    ed.delete_selected()
    ed.set_mode("circle")
    circle(25)
    assert [s.name for s in ed.shapes] == ["dish-1", "dish-3", "dish-2"]
    window.stem_field.setText("")
    circle(55)
    assert ed.shapes[-1].name == "circle-1"


def test_the_files_order_is_the_tables_and_a_click_picks_the_last_shape_under_it(window, tmp_path):
    ed = window.editor
    ed.set_mode("circle")
    for a, b in (((30, 24), (34, 24)), ((30, 24), (50, 24))):
        for p in (a, b):
            ed.press(p, 1)
            ed.release(p, 1)
    small, large = (s.name for s in ed.shapes)

    def picked():
        path = tmp_path / "g.json"
        path.write_text(json.dumps({"plate": [H, W], "shapes": [s.primitive() for s in ed.shapes]}), encoding="utf-8")
        return region_pick((30, 24), (H, W), 0, None, {**load_geometry(str(path)), "choice": ""})["choice"]

    assert picked() == large
    ed.set_mode("select")
    window.table.selectRow(0)
    window.down_button.click()
    assert [window.table.name_at(r) for r in range(2)] == [large, small] and picked() == small
    ed.undo()
    assert [s.name for s in ed.shapes] == [small, large]


def test_stamps_are_one_group_a_linked_rotation_turns_every_member_and_a_solo_resize_leaves_it():
    ed = Editor(plate=(100, 200))
    ed.set_mode("square")
    for p in ((10, 10), (30, 30)):
        ed.press(p, 1)
        ed.release(p, 1)
    ed.set_mode("stamp")
    at = [(60, 50), (100, 50), (198, 98)]
    for p in at:
        ed.press(p, 1)
        ed.release(p, 1)
    assert len(ed.shapes) == 4 and len({s.group for s in ed.shapes}) == 1 and ed.shapes[0].group
    assert ed.within(ed.shapes[3]) and ed.shapes[3].centre != pytest.approx(at[2])
    centres = [s.centre for s in ed.shapes]
    ed.set_mode("select")
    ed.select(ed.shapes[1].name)
    s = ed.current
    ed.press(ed.rotation_handle(1), 1)
    ed.move((s.cx + 50, s.cy), 1)
    ed.release((s.cx + 50, s.cy), 1)
    assert [t.angle for t in ed.shapes] == pytest.approx([math.pi / 2] * 4, abs=1e-3)
    assert [t.centre for t in ed.shapes] == [pytest.approx(c) for c in centres]
    ed.press(ed.rotation_handle(1), 1)
    ed.release((s.cx + 50, s.cy - 50), 1)
    turned = [t.angle for t in ed.shapes]
    assert all(ed.within(t) for t in ed.shapes) and len(set(turned)) == 1
    assert turned[0] == pytest.approx(math.pi / 2, abs=1e-6)
    ed.set_link(s.group, False)
    edge = ed.current.handles()[(1, 0)]
    ed.press(edge, 1)
    ed.move((edge[0] + 0.01, edge[1] + 5), 1)
    ed.release((edge[0] + 0.01, edge[1] + 5), 1)
    assert ed.current.group == "" and len({t.group for t in ed.shapes if t is not ed.current}) == 1
    assert len({t.w for t in ed.shapes}) == 2


def _draw(ed, mode, *points):
    ed.set_mode(mode)
    for p in points:
        ed.press(p, 1)
        ed.release(p, 1)


def test_save_writes_what_region_loads_and_reopening_gives_back_kinds_and_groups(clip, tmp_path):
    path = str(tmp_path / "new.json")
    win = GeometryWindow(clip, path)
    ed = win.editor
    _draw(ed, "circle", (10, 10), (15, 10))
    _draw(ed, "square", (20, 5), (30, 15))
    _draw(ed, "rectangle", (35, 5), (60, 12))
    _draw(ed, "polygon", (5, 30), (20, 30), (12, 45))
    ed.finish()
    ed.select(ed.shapes[1].name)
    _draw(ed, "stamp", (40, 35))
    assert win.save() and win.name_label.text() == "new.json"
    loaded = load_geometry(path)["shapes"]
    for s, d in zip(ed.shapes, loaded):
        key = "circle" if s.kind == "circle" else "polygon"
        assert d["name"] == s.name and np.allclose(d[key], s.primitive()[key])
    win.close()
    again = GeometryWindow(clip, path)
    assert [(s.name, s.kind, s.group) for s in again.editor.shapes] == [(s.name, s.kind, s.group) for s in ed.shapes]
    assert again.editor.shapes[-1].group and again.message.text() == ""
    again.close()


def test_a_file_without_a_drawing_opens_with_its_kinds_inferred(clip, tmp_path):
    path = tmp_path / "hand.json"
    path.write_text(json.dumps({"plate": [H, W], "shapes": [
        {"name": "dish", "circle": [10, 10, 5]},
        {"name": "box", "polygon": [[30, 10], [40, 20], [30, 30], [20, 20]]},
        {"name": "tri", "polygon": [[45, 40], [60, 40], [50, 30]]}]}), encoding="utf-8")
    win = GeometryWindow(clip, str(path))
    assert [s.kind for s in win.editor.shapes] == ["circle", "square", "polygon"]
    assert "inferred" in win.message.text() and "box" in win.message.text()
    win.close()


def test_a_file_of_another_plate_marks_what_is_past_the_edge_and_refuses_the_save(clip, tmp_path):
    path = tmp_path / "big.json"
    path.write_text(json.dumps({"plate": [200, 200], "shapes": [
        {"name": "far", "circle": [180, 180, 10]}, {"name": "near", "circle": [10, 10, 5]}]}), encoding="utf-8")
    win = GeometryWindow(clip, str(path))
    ed = win.editor
    assert "200×200" in win.message.text() and f"{W}×{H}" in win.message.text()
    assert ed.outside() == ["far"]
    before = path.read_text(encoding="utf-8")
    assert not win.save() and path.read_text(encoding="utf-8") == before
    _draw(ed, "select")
    ed.press((180, 180), 1)
    ed.move((30, 24), 1)
    ed.release((30, 24), 1)
    assert ed.outside() == [] and win.save()
    assert load_geometry(str(path))["plate"] == [H, W]
    ed.press((30, 24), 1)
    ed.move((1e4, 24), 1)
    ed.release((1e4, 24), 1)
    assert ed.shape("far").box()[2] == pytest.approx(W)
    win.close()


def test_a_kept_configuration_is_listed_on_the_next_run_and_loads_under_the_plate_check(clip, tmp_path):
    other = str(tmp_path / "other.avi")
    w = cv2.VideoWriter(other, cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    for _ in range(3):
        w.write(np.zeros((H, W, 3), np.uint8))
    w.release()
    lib = str(tmp_path / "library")
    win = GeometryWindow(clip, library=lib)
    _draw(win.editor, "circle", (10, 10), (15, 10))
    _draw(win.editor, "square", (20, 5), (30, 15))
    assert win.keep_configuration("rig") and not win.keep_configuration("rig")
    drawn = [(s.name, s.kind, s.primitive()) for s in win.editor.shapes]
    win.close()
    again = GeometryWindow(other, str(tmp_path / "doc.json"), library=lib)
    assert again.kept_names() == ["rig"] and f"{W}×{H}" in again.kept_list.item(0).text()
    assert again.load_configuration("rig") and again.file.endswith("doc.json")
    assert [(s.name, s.kind, s.primitive()) for s in again.editor.shapes] == drawn
    assert again.rename_configuration("rig", "arena") and not again.rename_configuration("arena", "a/b")
    (tmp_path / "library" / "big.json").write_text(json.dumps(
        {"plate": [200, 200], "shapes": [{"name": "far", "circle": [180, 180, 10]}]}), encoding="utf-8")
    again.refresh_library()
    assert again.kept_names() == ["arena", "big"]
    assert again.load_configuration("big") and "200×200" in again.message.text()
    assert again.editor.outside() == ["far"]
    assert again.remove_configuration("arena") and again.kept_names() == ["big"]
    again.close()
