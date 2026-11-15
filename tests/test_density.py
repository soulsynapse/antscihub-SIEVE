"""density: a measured plane folds to counts on a fixed log1p axis, the walk folds one for each fed frame node the plot shows, and the plot crops to the bins the window occupies."""
import os

import numpy as np

from sieve_player import density

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_fold_counts_every_pixel_on_the_fixed_axis():
    plane = np.zeros((4, 8), np.float32)
    plane[0, :3] = 255.0**2                                   # three pixels at the top of a gray-squared measure
    plane[1, 0] = -5.0                                        # below zero: with the zeros
    counts = density.fold(plane)
    assert counts.shape == (density.BINS,) and counts.dtype == np.uint32 and counts.sum() == plane.size
    b = density.bin_of(255.0**2)
    assert counts[b] == 3 and counts[0] == plane.size - 3 and b < density.BINS - 1
    assert abs(density.value_of(b) - 255.0**2) / 255.0**2 < 0.05   # a bin's value is within its width
    assert density.is_plane(plane) and density.is_plane(plane.astype(np.uint8))
    assert not density.is_plane(plane > 0) and not density.is_plane(np.zeros((2, 2, 2), np.float32)) and not density.is_plane(None)


def test_an_integer_plane_leaves_no_empty_bin_between_its_values():
    """A gray image or a difference holds integers: on the axis the bins they land in are consecutive,
    and the float path agrees with the uint8 table."""
    ramp = np.arange(256, dtype=np.uint8).reshape(16, 16)
    occupied = np.flatnonzero(density.fold(ramp))
    assert occupied[0] == 0 and (np.diff(occupied) == 1).all() and len(occupied) == len({density.bin_of(v) for v in range(256)})
    assert (density.fold(ramp) == density.fold(ramp.astype(np.float32))).all()
    assert [density.value_of(b) for b in range(5)] == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_the_walk_folds_what_the_plot_shows_a_branch_too_and_no_other_node():
    from PySide6.QtWidgets import QApplication
    from sieve_player.worker import Worker
    from test_graph import TOOLS, Dec, D, Graph, add, gray, same, tool

    QApplication.instance() or QApplication([])

    head = tool("head", kind="series", produces="signal")
    head.run = lambda series, params: {"signal": np.asarray(series.data, np.float64).reshape(len(series.data), -1)[:, 0]}
    doc = D.from_tools([gray, add, head])                     # video -> gray -> add -> head
    doc.add_node("same", (0, 300))
    doc.connect("gray", "same")                               # a branch the series never reads
    g = Graph(doc, Dec(), {**TOOLS, "head": head})
    assert g.walk == "add" and g.folded() == []
    g.watch(["same", "head", "nowhere"])
    assert g.folded() == ["same"]                             # of what the plot shows, the fed frame nodes
    w, fields, begun = Worker(g, every=3), [], []
    w.densityReady.connect(lambda f, start: fields.append({nid: len(c) for nid, c in f.items()}))
    g.on_event = lambda ev: ev.kind == "begin" and begun.append(ev.row)

    def turns():
        while True:
            with w._cv:
                turn = w._turn()
            if turn is None:
                return
            for job, act in turn[1]:
                g.serving(turn[0], job.name)
                act()

    w.set_window(2, 4)
    turns()
    assert fields[-1] == {"same": 4}
    stack = w._win.stack
    w.watch(["add", "same"])                                  # shown once the window is walked: folded from its first row, the chain's rows standing
    turns()
    assert fields[-1] == {"same": 4, "add": 4} and w._win.stack is stack is not None and w._win.i == 4
    assert begun == [2, 2] and not w._win.refolding
    doc.disconnect("same")
    g.sync()
    assert g.folded() == ["add"]


def test_plot_crops_to_the_occupied_bins_and_paints():
    from PySide6.QtWidgets import QApplication

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from sieve_player.plot import Plot

    QApplication.instance() or QApplication([])
    counts = np.zeros((3, density.BINS), np.uint32)
    counts[:, 40] = 100
    counts[2, 120] = 5
    w = Plot()
    w.resize(300, 200)
    w.set_window(7, 3, 30.0)
    w.set_fields({"a": counts}, 7)
    w.set_selection("a")
    w.set_playhead(8)
    f = w.fields["a"]
    assert (f.lo, f.hi) == (40 - f.MARGIN, 120 + f.MARGIN)        # cropped on arrival, before any paint
    assert not w.grab().isNull()
    drawn = w._still
    w.set_playhead(9)
    w.set_hover(8)
    assert not w.grab().isNull() and w._still is drawn            # a cursor that moves draws no row again
    w.set_fields({"a": counts}, 7)
    assert w._still is None
    assert w._row(w._inner().left()) == 7
    # the handles start at the axis's ends and keep every shown bin; dragged in, they drop the bins outside
    assert f.kept(w.levels("a")).all()
    got, let_go = [], []
    w.bandDragged.connect(lambda nid, lv: (got.append((nid, list(lv))), w.set_bands({nid: lv})))   # the window: writes it and hands it back
    w.bandReleased.connect(lambda nid, lv: let_go.append((nid, list(lv))))
    w._drag_level(1, w._y(density.value_of(100), "a"))
    assert got == [("a", w.levels("a"))]                            # a proposal; the plot draws the band it was handed
    assert abs(density.pos_of(w.levels("a")[1]) - 100) < 0.5
    w._mode = 1
    QTest.mouseRelease(w, Qt.LeftButton)
    assert let_go == [("a", w.levels("a"))]
    kept = f.kept(w.levels("a"))
    assert kept[40 - f.lo] and not kept[120 - f.lo]
    w._drag_level(0, w._y(density.value_of(110), "a"))        # lo above hi: inside out
    kept = f.kept(w.levels("a"))
    assert kept[40 - f.lo] and kept[120 - f.lo] and not kept[105 - f.lo]
    w._drag_level(1, w._inner().top() - 20)                   # above the field: infinity
    assert w.levels("a")[1] == float("inf") and w._y(float("inf"), "a") == w._inner().top()
    assert not w.grab().isNull()
