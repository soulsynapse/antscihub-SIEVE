"""crop: the frame cut to the roi's box at row 0 plus a border, the same at every row under one key, a mask cut
against itself meeting the frame, an empty roi said on the node, the cut shown at its shape and baked at it."""
import os
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sieve_player import document as D  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from tests.test_graph import Dec, tool  # noqa: E402
from tools import crop, gray, threshold  # noqa: E402


def roi_tool(at):
    """A mask with one 2x2 blob whose top-left is `at(row)`; None from `at` is an empty mask."""
    def run(frames, row, params):
        m = np.zeros(frames(row).shape[:2], np.uint8)
        if (p := at(row)) is not None:
            m[p[0]:p[0] + 2, p[1]:p[1] + 2] = 255
        return m
    t = tool("roi", "bgr", "mask")
    t.run = run
    return t


def build(at, border=0):
    doc = D.from_tools([crop])
    doc.add_node("roi", (0, 500))
    doc.connect("video", "roi")
    doc.connect("roi", "crop", "roi")
    doc.node("crop").params["border"] = border
    return doc, Graph(doc, Dec(), {"crop": crop, "roi": roi_tool(at)})


def test_the_cut_is_the_roi_box_at_row_0_grown_clipped_and_held_a_mask_cuts_itself_and_an_empty_roi_is_said():
    doc, g = build(lambda r: (1, 2) if r == 0 else (0, 0))
    out = g.compute("crop", 0)
    assert out.shape == (2, 2, 3) and np.array_equal(out, g.compute("video", 0)[1:3, 2:4])
    assert g.compute("crop", 5).shape == (2, 2, 3) and np.array_equal(g.compute("crop", 5), g.compute("video", 5)[1:3, 2:4])
    doc.node("crop").params["border"] = 10
    g.sync()
    assert g.compute("crop", 3).shape == (4, 6, 3)                     # grown past the frame's edge: the whole frame
    assert crop.rect(g.compute("roi", 0), 1) == (0, 4, 1, 5)
    doc.node("crop").params["border"] = 0
    doc.add_node("crop", (0, 600), crop.DEFAULTS, id="crop_2")
    doc.connect("roi", "crop_2")
    doc.connect("roi", "crop_2", "roi")
    g.sync()
    frame, mask = g.compute("crop", 0), g.compute("crop_2", 0)
    assert frame.shape[:2] == mask.shape == (2, 2) and (mask == 255).all()
    doc, g = build(lambda r: None)
    with pytest.raises(ValueError):
        g.compute("crop", 0)
    assert "roi has no nonzero pixel" in g.standing("crop")


def clip(path, n=6, h=48, w=64):
    import cv2

    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (w, h))
    for r in range(n):
        f = np.full((h, w, 3), 30, np.uint8)
        f[10:31, 20:51] = 220                                  # a bright plate the threshold finds, odd on both sides
        wr.write(f)
    wr.release()
    return str(path)


def cropped_doc(path):
    """video -> gray -> threshold -> crop(roi=threshold), with the display on the crop."""
    doc = D.from_tools([gray, threshold, crop], path)
    doc.connect("gray", "crop")
    doc.connect("threshold", "crop", "roi")
    doc.display = "crop"
    return doc


def test_a_displayed_crop_shows_the_cut_at_its_shape_and_the_plan_lists_it(tmp_path):
    from PySide6.QtWidgets import QApplication
    from sieve_player.window import PlayerWindow
    from sieve_player.plan import base_key, plan

    QApplication.instance() or QApplication([])
    doc = cropped_doc(clip(tmp_path / "v.avi"))
    D.save(doc, tmp_path / "doc.json")
    tools = [gray, threshold, crop]
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", tools)
    t = time.perf_counter()
    while win.display._pix is None and time.perf_counter() - t < 10:
        QApplication.processEvents()
        time.sleep(0.005)
    assert (win.display._pix.height(), win.display._pix.width()) == (21, 31) and win.count == 6
    e = plan(win.doc, {t.NAME: t for t in tools}, base_key(win.doc.video_path(), "bgr")).entries["crop"]
    assert e.kind == "frame" and e.standing == "" and win.graph.standing("crop") == ""
    win.close()


@pytest.mark.skipif(__import__("shutil").which("ffmpeg") is None, reason="a bake's clip writer runs ffmpeg from PATH")
def test_a_bake_after_a_crop_writes_and_serves_the_cut(tmp_path, in_store):
    from PySide6.QtWidgets import QApplication
    from sieve_player import store
    from sieve_player.decoder import Decoder
    from sieve_player.worker import Worker
    from tests.test_baking import run_bake
    from tools import bake

    QApplication.instance() or QApplication([])
    path = clip(tmp_path / "v.avi")
    doc = cropped_doc(path)
    doc.add_node("bake")
    doc.connect("crop", "bake")
    doc.path = str(tmp_path / "doc.json")
    g = Graph(doc, Decoder(path), {t.NAME: t for t in (gray, threshold, crop, bake)}, open_bake=store.current().open_bake)
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    g.halt = False
    assert done and not refused, refused
    assert store.Store(str(in_store)).sidecar(done[0][1]).shape == [21, 31] and doc.node("bake").baked.shape == (21, 31)
    g.sync()
    assert g.compute("bake", 2).shape == (21, 31)       # the writer pads an odd side; the served row is the cut's
    g.close()
    g.decoder.close()
