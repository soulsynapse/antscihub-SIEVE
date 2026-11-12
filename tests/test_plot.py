"""The plot under the frame: the frame's width and flush with its bottom inside one outline, drawing the selection and the pinned set over the window."""
import os
import time

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.plot import AXIS_W, LABEL_ROOM, TICK_ROOM, ChipRow, Plot  # noqa: E402
from sieve_player.theme import FADED_ALPHA, GROUND, HEAD, INK_ALPHA, LINE_LIFT, GlyphButton, mono_font  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_graph import tool  # noqa: E402
from tools import gray  # noqa: E402


def series(name, fn):
    def settings(parent=None):
        from sieve_player import ParamWidget
        w = ParamWidget(parent)
        w.add_int("k", 0, 9, 1)
        return w
    t = tool(name, "gray", "signal", kind="series")
    t.fold = lambda frame: np.asarray([float(frame.mean())])
    t.run = lambda s, params: {"signal": fn(np.asarray(s.data, np.float64).reshape(len(s.data), -1)[:, 0])}
    t.settings = settings
    return t


def settle(win, *nodes, timeout=10.0):
    t = time.perf_counter()
    while not all(isinstance(win.results.get(n), dict) and len(win.results[n]["signal"]) == win.count for n in nodes):
        assert time.perf_counter() - t < timeout
        QApplication.processEvents()
        time.sleep(0.005)
    QApplication.processEvents()


def mouse(widget, kind, at, button=Qt.LeftButton):
    held = button if kind != QEvent.MouseButtonRelease else Qt.NoButton
    handler = {QEvent.MouseButtonPress: widget.mousePressEvent, QEvent.MouseMove: widget.mouseMoveEvent,
               QEvent.MouseButtonRelease: widget.mouseReleaseEvent}[kind]
    handler(QMouseEvent(kind, at, widget.mapToGlobal(at.toPoint()), button, held, Qt.NoModifier))
    QApplication.processEvents()


def coloured(img, rect):
    """Whether any pixel in `rect` is a series line's teal or gate green, which no gray, ink or handle is."""
    return any(c.green() > c.red() + 60 and c.blue() > c.red() + 20
               for c in (img.pixelColor(x, y) for x in range(int(rect.left()), int(rect.right()), 2)
                         for y in range(int(rect.top()), int(rect.bottom()), 2)))


def test_the_plot_is_under_the_frame_at_its_width_and_the_pane_holds_no_plot_or_pin():
    QApplication.instance() or QApplication([])
    win = PlayerWindow([gray], "t")
    win.resize(900, 600)
    win.show()
    QApplication.processEvents()
    assert win.plot.y() == win.display.y() + win.display.height()
    assert win.plot.width() == win.display.width() and win.plot.height() == Plot.ROWS * 22
    assert win.pane.findChildren(Plot) == [] and not [b for b in win.pane.findChildren(GlyphButton) if b.off == "pin"]
    img = win.stage.grab().toImage()
    edge = GROUND + LINE_LIFT
    assert img.pixelColor(0, win.display.height() // 2).red() == edge and img.pixelColor(0, win.plot.y() + 20).red() == edge
    assert img.pixelColor(win.stage.width() // 2, win.plot.y()).red() != edge           # the seam: no line between the two
    win.close()


def test_ticks_are_whole_seconds_apart_with_the_window_s_ends_among_them():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(100, 300, 30.0)
    rows = w.ticks()
    assert rows[0] == 100 and rows[-1] == 399 and rows == sorted(set(rows))
    assert all((r / 30.0).is_integer() for r in rows[1:-1]) and len(rows) > 4
    assert min(b - a for a, b in zip(rows, rows[1:])) * w._step() >= TICK_ROOM


def test_the_plot_draws_the_selection_and_the_pinned_set_stays_when_the_selection_has_no_plot(tmp_path):
    QApplication.instance() or QApplication([])
    head, flat = series("head", lambda v: np.arange(len(v), dtype=np.float64)), series("flat", lambda v: np.ones_like(v))
    doc = D.from_tools([gray, head, flat], clip(tmp_path / "v.avi"))
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head, flat])
    win.resize(900, 600)
    win.show()
    settle(win, "head", "flat")
    win.canvas.select(["head"])
    inner = win.plot._inner()
    assert win.plot.selection == "head" and coloured(win.plot.grab().toImage(), inner)
    win.doc.pinned = ["flat"]
    win.sync()
    win.canvas.select(["video"])
    assert win.plot.shown() == ["video", "flat"] and "video" not in win.plot.lines
    img = win.plot.grab().toImage()
    c = img.pixelColor(int(inner.center().x()), int(inner.top()))       # flat's line, 1.0 everywhere, at its own top: ink
    assert c.red() == c.green() == c.blue() and 80 < c.red() < 170
    assert not coloured(img, inner)
    win.close()


def test_a_press_in_the_plot_seeks_and_pauses_and_the_circle_astride_the_seam_is_the_playhead_s(tmp_path):
    QApplication.instance() or QApplication([])
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    doc = D.from_tools([gray, head], clip(tmp_path / "v.avi"))
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head])
    win.resize(900, 600)
    win.show()
    settle(win, "head")
    win.canvas.select(["head"])
    plot, inner = win.plot, win.plot._inner()
    assert win.playing                                        # a load opens playing
    at = QPointF(inner.center().x(), inner.center().y())
    mouse(plot, QEvent.MouseButtonPress, at)
    assert win.row == plot._row(at.x()) and win.row > 0 and not win.playing
    to = QPointF(inner.left() + inner.width() * 0.25, at.y())
    mouse(plot, QEvent.MouseMove, to)
    assert win.row == plot._row(to.x())
    mouse(plot, QEvent.MouseButtonRelease, to)
    assert win.playing
    win.toggle_play()
    # the circle: white over the frame above the seam at the playhead's x, and the line down the plot under it
    x = plot.head_x()
    stage = win.stage
    img = stage.grab().toImage()
    seam = plot.y()
    assert img.pixelColor(int(x) + plot.x(), seam - 3).red() == HEAD
    y = seam + int(inner.height() * 0.5)
    line = max(img.pixelColor(int(x) + plot.x() + dx, y).red() for dx in (-1, 0, 1))    # 1.5 px wide on a fractional x: a blend
    assert line > 190 and img.pixelColor(int(x) + plot.x() + 6, y).red() < 100
    assert stage.head.isVisible() and stage.head.mask().contains(QPointF(x, stage.head.R).toPoint())         and not stage.head.mask().contains(QPointF(x + 4 * stage.head.R, stage.head.R).toPoint())
    # a press on the circle's upper half, over the frame, seeks though the open band's handle lies at the plot's top
    assert plot.levels("head")[1] == float("inf")
    head_at = QPointF(x, stage.head.R - 2)
    mouse(stage.head, QEvent.MouseButtonPress, head_at)
    assert plot._mode == "head"
    far = QPointF(inner.right() - 1, head_at.y())
    mouse(stage.head, QEvent.MouseMove, far)
    assert win.row == plot._row(far.x())
    mouse(stage.head, QEvent.MouseButtonRelease, far)
    assert plot._mode is None and plot.levels("head")[1] == float("inf")
    win.close()


def test_the_selection_s_axis_is_labelled_in_the_gutter_with_the_band_s_values_in_level_and_nothing_on_the_line():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(0, 100, 30.0)
    w.set_lines({"a": (np.arange(100, dtype=np.float64), None)}, 0)
    w.set_selection("a")
    w.set_bands({"a": (20.0, 70.0)})
    labels = w.axis_labels()
    band = sorted(v for v, _, kind in labels if kind == "band")
    axis = [(v, y) for v, y, kind in labels if kind == "axis"]
    assert band == [20.0, 70.0] and len(axis) >= 2 and all(w._inner().top() <= y <= w._inner().bottom() for _, y in axis)
    ys = sorted(y for _, y, _ in labels)
    assert min(b - a for a, b in zip(ys, ys[1:])) >= LABEL_ROOM / 2
    img = w.grab().toImage()
    inner, right = w._inner(), w._label_right()

    def level_text(y):   # LEVEL ink in the gutter at this height, left of the handle's dot
        return any(c.red() > c.green() + 60 for c in (img.pixelColor(x, yy) for x in range(0, int(right), 2) for yy in range(int(y) - 6, int(y) + 7, 2)))

    def ink_text(y):
        return any(80 < c.red() < 170 and c.red() == c.blue() for c in (img.pixelColor(x, yy) for x in range(0, int(right), 2) for yy in range(int(y) - 6, int(y) + 7, 2)))
    assert all(level_text(y) for _, y, kind in labels if kind == "band")
    assert all(ink_text(y) for _, y, kind in labels if kind == "axis")
    y = int(w._y(70.0, "a"))
    assert not any(img.pixelColor(x, y).red() > 60 for x in range(int(inner.right() + Plot.STUB + Plot.DOT) + 2, w.width() - 1))   # no readout at the line's end
    assert not coloured(img, QRectF(0, 0, right, w.height()))   # the curve stays out of the gutter


def test_dragging_a_handle_saves_the_band_and_fades_the_pinned_while_held(tmp_path):
    QApplication.instance() or QApplication([])
    head, down = series("head", lambda v: np.arange(len(v), dtype=np.float64)), series("down", lambda v: np.arange(len(v) - 1, -1, -1, dtype=np.float64))
    doc = D.from_tools([gray, head, down], clip(tmp_path / "v.avi"))
    doc.pinned = ["down"]
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head, down])
    win.resize(900, 600)
    win.show()
    settle(win, "head", "down")
    win.toggle_play()
    win.canvas.select(["head"])
    plot, inner = win.plot, win.plot._inner()
    assert plot.shown() == ["head", "down"] and plot.ink_alpha() == INK_ALPHA
    at_down = (int(inner.left() + inner.width() * 0.1), int(inner.bottom() - inner.height() * 0.9))   # down's line, high where head is low
    assert plot.grab().toImage().pixelColor(*at_down).red() > 100
    x = inner.left() + inner.width() * 0.75
    mouse(plot, QEvent.MouseButtonPress, QPointF(x, inner.top()))                  # the open band's upper handle, infinity, at the top
    assert plot._mode == 1 and plot.ink_alpha() == FADED_ALPHA
    assert plot.grab().toImage().pixelColor(*at_down).red() < 80
    to = QPointF(x, inner.bottom() - inner.height() * 0.75)
    mouse(plot, QEvent.MouseMove, to)
    lo, hi = win.doc.node("head").band
    top = plot.lines["head"].top
    assert lo == 0.0 and abs(hi - top * 0.75) < top * 0.02
    assert plot.levels("head") == [lo, hi]                                         # the plot draws the document's band, handed back
    mouse(plot, QEvent.MouseMove, QPointF(x, inner.bottom() - inner.height() * 0.5))
    assert plot.levels("head") == list(win.doc.node("head").band) and win.doc.node("head").band[1] < hi
    mouse(plot, QEvent.MouseMove, to)
    mouse(plot, QEvent.MouseButtonRelease, to)
    assert plot._mode is None and plot.ink_alpha() == INK_ALPHA and win.doc.node("head").band == (lo, hi)
    assert plot.levels("head") == [lo, hi]
    assert plot.grab().toImage().pixelColor(*at_down).red() > 100
    win.close()


def test_a_field_s_crop_is_the_same_before_a_paint_as_after_and_new_fields_leave_a_held_handle():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(0, 100, 30.0)
    counts = np.zeros((100, 256), np.uint32)
    counts[:, 40] = 100
    counts[50:, 120] = 5
    w.set_fields({"f": counts}, 0)
    w.set_selection("f")
    w.set_bands({"f": (3.0, 2000.0)})
    before = (w.axis_labels(), w._y(3.0, "f"), w._y(2000.0, "f"), (w.fields["f"].lo, w.fields["f"].hi))
    w.grab()
    after = (w.axis_labels(), w._y(3.0, "f"), w._y(2000.0, "f"), (w.fields["f"].lo, w.fields["f"].hi))
    assert before == after and before[3] == (40 - 2, 120 + 2)
    w.set_window(0, 40, 30.0)                                       # the window ends before the second bin's rows: the crop follows the window, not a paint
    assert (w.fields["f"].lo, w.fields["f"].hi) == (40 - 2, 40 + 2)
    w.set_window(0, 100, 30.0)
    w.bandDragged.connect(lambda nid, lv: w.set_bands({nid: lv}))
    inner = w._inner()
    mouse(w, QEvent.MouseButtonPress, QPointF(inner.center().x(), w._y(2000.0, "f")))
    assert w._mode == 1
    held = list(w.levels("f"))
    w.set_fields({"f": counts.copy()}, 0)                            # a walk result landing while the handle is held
    assert w.levels("f") == held and abs(w._y(held[1], "f") - before[2]) < 1e-6
    mouse(w, QEvent.MouseButtonRelease, QPointF(inner.center().x(), w._y(2000.0, "f")))


def test_chips_stay_right_of_the_gutter_with_long_names_elided_and_every_pin_kept():
    QApplication.instance() or QApplication([])
    names = ["a_very_long_node_name_" * 6, "another_long_one_" * 6, "s"]
    row = ChipRow(mono_font(), names, AXIS_W, 640 - 8, 154)
    assert [c[0] for c in row.chips] == names
    assert all(name.left() >= AXIS_W and pin.left() >= AXIS_W and pin.right() <= 640 for _, name, pin, _ in row.chips)
    assert all("…" in text for n, _, _, text in row.chips if len(n) > 20) and row.chips[2][3] == "s"
    assert row.hit(row.chips[0][1].center()) == ("name", names[0]) and row.hit(row.chips[1][2].center()) == ("pin", names[1])
    assert row.hit(QPointF(0, 150)) is None
    short = ChipRow(mono_font(), ["head", "down"], AXIS_W, 640 - 8, 154)
    assert all(n == text for n, _, _, text in short.chips)


def test_pinned_lines_each_span_the_height_in_one_ink_and_the_selection_is_drawn_once_in_colour():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(0, 100, 30.0)
    small, large = np.arange(100, dtype=np.float64) % 10, 5000.0 * (np.arange(100, dtype=np.float64) % 10)
    w.set_lines({"s": (small, None), "l": (large, None), "none": (np.zeros(0), None)}, 0)
    w.set_pinned(["s", "l", "none"])
    w.set_selection("video")
    assert w._y(small.max(), "s") == w._y(large.max(), "l") == w._inner().top() and w._y(0.0, "s") == w._inner().bottom()
    img = w.grab().toImage()
    inner = w._inner()
    inks = [img.pixelColor(int(w._x(r)), int(w._y(v, n))) for n, vals in (("s", small), ("l", large)) for r, v in ((9, vals[9]), (10, vals[10]))]
    assert all(c.red() == c.green() == c.blue() for c in inks) and max(c.red() for c in inks) - min(c.red() for c in inks) < 24   # one ink; a vertex antialiases
    assert not coloured(img, inner)
    c = img.pixelColor(int(w._x(9)), int(inner.top()))
    assert c.red() == c.green() == c.blue() and 80 < c.red() < 170
    w.set_bands({"s": (2.0, 7.0)})                                   # s's band: its ink dims where its value is shut out, the field untouched
    img = w.grab().toImage()
    kept, shut = img.pixelColor(int(w._x(5)), int(w._y(5.0, "s"))), img.pixelColor(int(w._x(9)), int(w._y(9.0, "s")))
    assert shut.red() == shut.green() == shut.blue() and 50 < shut.red() + 25 < kept.red()
    assert img.pixelColor(int(w._x(5)) + 3, int(w._y(9.0, "s")) + 3).red() == img.pixelColor(int(w._x(5)) + 3, int(w._y(0.0, "s")) - 3).red()
    w.set_bands({})
    w.set_selection("l")
    w.set_bands({"l": (10000.0, 40000.0)})                           # handles clear of the peak the pixel below reads
    img = w.grab().toImage()
    assert coloured(img, inner)
    top = img.pixelColor(int(w._x(9)), int(inner.top()))
    assert top.green() > top.red() + 60                              # the one drawing of l at its peak is the series colour, no ink under it


def test_a_pinned_field_is_drawn_first_under_the_selection_s_line():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(0, 100, 30.0)
    counts = np.zeros((100, 256), np.uint32)
    counts[:, 5] = 1000                                             # every row's pixels at value 5: one lit bin across the plot
    w.set_fields({"f": counts}, 0)
    w.set_lines({"a": (np.full(100, 5.0), None)}, 0)
    w.set_pinned(["f"])
    w.set_selection("a")
    w.set_bands({"a": (1.0, 4.0)})                                   # handles clear of the line at its top
    w.grab()
    y = int(w._y(5.5, "f"))                                        # the lit bin's centre, cropped to the occupied bins
    img = w.grab().toImage()
    inner = w._inner()
    c = img.pixelColor(int(inner.center().x()), y)
    assert c.blue() > c.red() + 20 and c.green() > c.red() + 20      # the field's ramp, dimmed, where no line is
    assert w.field_shown() == "f" and coloured(img, QRectF(inner.left(), inner.top() - 0.5, inner.width(), 4))   # a's flat line at its own top, over the field


def test_the_hover_reads_each_shown_line_by_name_and_value_and_two_equal_values_are_pushed_apart():
    QApplication.instance() or QApplication([])
    w = Plot()
    w.resize(640, 154)
    w.set_window(0, 100, 30.0)
    up = np.arange(100, dtype=np.float64)
    w.set_lines({"up": (up, None), "twin": (up.copy(), None), "short": (up[:10], None)}, 0)
    w.set_selection("up")
    w.set_pinned(["twin", "short"])
    w.set_hover(40)
    outs = w.readouts()
    assert [o[0] for o in outs] == ["up", "twin"] and all(o[1] == f"{o[0]} 40" for o in outs)
    assert outs[0][2] == outs[1][2] and not outs[0][3].intersects(outs[1][3])
    img = w.grab().toImage()
    assert coloured(img, outs[0][3]) and not coloured(img, outs[1][3])    # the selection's in the series colour, the pinned's in ink
    w.set_hover(-1)
    assert w.readouts() == []


def test_the_chip_row_is_legend_selector_and_pinned_set(tmp_path):
    QApplication.instance() or QApplication([])
    head, down = series("head", lambda v: np.arange(len(v), dtype=np.float64)), series("down", lambda v: np.arange(len(v) - 1, -1, -1, dtype=np.float64))
    doc = D.from_tools([gray, head, down], clip(tmp_path / "v.avi"))
    doc.pinned = ["down"]
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head, down])
    win.resize(900, 600)
    win.show()
    settle(win, "head", "down")
    win.toggle_play()
    win.canvas.select(["head"])
    plot = win.plot
    chips = plot.chips()
    assert [c[0] for c in chips] == ["head", "down"] and chips[0][1].right() < chips[1][1].left()
    assert all(r.bottom() <= plot.height() and r.top() >= plot._inner().bottom() for _, name, pin, _ in chips for r in (name, pin))
    img = plot.grab().toImage()
    bright = lambda rect: max(img.pixelColor(x, y).red() for x in range(int(rect.left()), int(rect.right())) for y in range(int(rect.top()), int(rect.bottom())))
    assert bright(chips[0][1]) == HEAD and bright(chips[1][1]) < HEAD
    mouse(plot, QEvent.MouseButtonPress, chips[1][1].center())           # down's name: the canvas selection moves
    mouse(plot, QEvent.MouseButtonRelease, chips[1][1].center())
    assert win.canvas.selected == ["down"] and plot.selection == "down" and [c[0] for c in plot.chips()] == ["down"]   # head, unpinned, is gone
    assert win.row == 0                                                     # a chip press is not a seek
    win.canvas.select(["head"])
    chips = plot.chips()
    mouse(plot, QEvent.MouseButtonPress, chips[0][2].center())           # the selection's own pin: it will stay
    mouse(plot, QEvent.MouseButtonRelease, chips[0][2].center())
    assert win.doc.pinned == ["down", "head"] and plot.pinned == ["down", "head"]
    win.canvas.select(["down"])
    assert [c[0] for c in plot.chips()] == ["down", "head"]
    win.canvas.select(["video"])
    assert [c[0] for c in plot.chips()] == ["down", "head"]              # no chip for a selection with no plot; the pinned stay
    mouse(plot, QEvent.MouseButtonPress, plot.chips()[0][2].center())    # down's pin, off
    mouse(plot, QEvent.MouseButtonRelease, plot.chips()[0][2].center())
    assert win.doc.pinned == ["head"] and [c[0] for c in plot.chips()] == ["head"]
    win.close()


def test_the_strip_is_handed_every_shown_series_with_the_selection_marked(tmp_path):
    QApplication.instance() or QApplication([])
    head, down = series("head", lambda v: np.arange(len(v), dtype=np.float64)), series("down", lambda v: np.arange(len(v) - 1, -1, -1, dtype=np.float64))
    doc = D.from_tools([gray, head, down], clip(tmp_path / "v.avi"))
    doc.pinned = ["head", "down"]
    D.save(doc, tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head, down])
    win.resize(900, 600)
    win.show()
    settle(win, "head", "down")
    win.canvas.select(["down"])
    strip = win.timeline.strip
    assert win.selection == "down" and list(strip.series) == D.shown("down", win.doc.pinned) == ["down", "head"] and strip.selection == "down"
    assert np.array_equal(strip.series["head"][0], win.results["head"]["signal"]) and strip.series["head"][1] == win.result_start
    win.plot.set_selection(None)                                            # the window reads nothing back from the plot
    win._show_pinned()
    assert list(strip.series) == ["down", "head"] and strip.selection == "down"
    win.canvas.select(["video"])
    assert win.selection == "video" and list(strip.series) == ["head", "down"] and strip.selection == "video"
    win.close()
