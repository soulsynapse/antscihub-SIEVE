"""density: a measured plane folds to counts on a fixed log1p axis, every fed frame node gets one, and the plot crops to the bins the window occupies."""
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


def test_every_fed_frame_node_is_counted_a_branch_too():
    from test_graph import TOOLS, Dec, D, Graph, add, gray, same, tool

    head = tool("head", kind="series", produces="signal")
    doc = D.from_tools([gray, add, head])                     # video -> gray -> add -> head
    doc.add_node("same", (0, 300))
    doc.connect("gray", "same")                               # a branch the series never reads
    g = Graph(doc, Dec(), {**TOOLS, "head": head})
    assert g.walk == "add" and g.frame_nodes() == ["gray", "add", "same"]
    doc.disconnect("same")
    g.sync()
    assert g.frame_nodes() == ["gray", "add"]


def test_plot_crops_to_the_occupied_bins_and_paints():
    from PySide6.QtWidgets import QApplication

    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from sieve_player.widgets import Density

    QApplication.instance() or QApplication([])
    counts = np.zeros((3, density.BINS), np.uint32)
    counts[:, 40] = 100
    counts[2, 120] = 5
    w = Density()
    w.resize(300, 200)
    w.set_series(counts, 7)
    w.set_playhead(8)
    assert not w.grab().isNull()
    assert (w.lo, w.hi) == (40 - w.MARGIN, 120 + w.MARGIN)
    assert w._row(w._inner().left()) == 7
    # the handles start at the axis's ends and keep every shown bin; dragged in, they drop the bins outside
    assert w._kept().all()
    got, let_go = [], []
    w.levelDragged.connect(lambda i, v: got.append((i, v)))
    w.levelReleased.connect(lambda i, v: let_go.append((i, v)))
    w._drag_level(1, w._y(density.value_of(100)))
    assert got and got[0][0] == 1 and abs(density.pos_of(got[0][1]) - 100) < 0.5
    w._mode = 1
    QTest.mouseRelease(w, Qt.LeftButton)
    assert let_go == [got[-1]]                                      # released once, with the handle's final value
    kept = w._kept()
    assert kept[40 - w.lo] and not kept[120 - w.lo]
    w._drag_level(0, w._y(density.value_of(110)))             # lo above hi: inside out
    kept = w._kept()
    assert kept[40 - w.lo] and kept[120 - w.lo] and not kept[105 - w.lo]
    assert not w.grab().isNull()
