"""Baking: a bake streams the node's input into the store on the worker with a scrub served between rows, lands a file and sidecar and marks the node baked, leaves nothing on cancel or failure, refuses a kind with no writer, and what it wrote reads back: a clip the decoder opens through its luma path, tables and a signal equal."""
import os
import time
from types import SimpleNamespace as Tool

import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sieve_player import decoder as decoder_mod
from sieve_player import document as D
from sieve_player import store, writers
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.worker import Worker
from tools import bake, blobs, count, flow, gray, threshold, track

H, W, N = 48, 64, 12


def clip(path):
    """A clip of N rows: a smooth ramp that drifts a row at a time, with a bright square walking across it."""
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    y, x = np.mgrid[:H, :W]
    for r in range(N):
        f = ((x * 2 + y + 5 * r) % 180).astype(np.uint8)
        b = cv2.merge((f, f // 2, 255 - f))
        b[10:22, 4 + 4 * r: 16 + 4 * r] = 255
        w.write(b)
    w.release()
    return str(path)


def slow(name, expects="gray", produces="gray", delay=0.0, boom=None):
    """A frame pass-through that waits `delay` a row and raises at row `boom`."""
    def run(frames, row, params):
        f = frames(row)
        time.sleep(delay)
        if row == boom:
            raise RuntimeError("boom")
        return f
    return Tool(NAME=name, KIND="frame", EXPECTS=expects, PRODUCES=produces, DEFAULTS={}, run=run)


TOOLS = {t.NAME: t for t in (bake, blobs, count, flow, gray, threshold, track)}


def graph(path, *chain, tools=TOOLS, **params):
    """video -> chain..., with a bake node after the last, carrying `params`."""
    QApplication.instance() or QApplication([])
    doc = D.from_tools([tools[n] for n in chain] + [bake], path)
    doc.node("bake").params.update(params)
    doc.path = os.path.join(os.path.dirname(path), "doc.json")
    return Graph(doc, Decoder(path), tools)


def run_bake(w, nid="bake", timeout=20.0):
    """Starts the worker on a bake and returns (done, refused) once one has been said."""
    done, refused = [], []
    w.bakeDone.connect(lambda n, k: done.append((n, k)))
    w.bakeRefused.connect(lambda n, why: refused.append((n, why)))
    w.set_window(0, 2)
    w.bake(nid)
    if not w.isRunning():
        w.start()
    t = time.perf_counter()
    while not (done or refused) and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.005)
    return done, refused


@pytest.fixture
def in_store(tmp_path, monkeypatch):
    folder = tmp_path / "store"
    monkeypatch.setattr(store, "folder", lambda: str(folder))
    return folder


def test_a_bake_lands_the_file_and_sidecar_and_marks_the_node_baked(tmp_path, in_store):
    g = graph(clip(tmp_path / "v.avi"), "gray", **{"from": "2", "to": "9", "increment": 2})
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert done == [("bake", g.key("bake"))] and not refused, refused
    side = store.sidecar(g.key("bake"), str(in_store))
    assert os.path.exists(store.place(g.key("bake"), ".mp4", str(in_store))) and not list(in_store.glob("*.part*"))
    assert {k: side[k] for k in ("kind", "document", "node", "rows", "increment", "fps", "written_fps", "shape", "quality")} == \
        {"kind": "gray", "document": "doc.json", "node": "bake", "rows": [2, 8], "increment": 2, "fps": 30.0, "written_fps": 15.0,
         "shape": [H, W], "quality": "lossless"}
    assert g.doc.node("bake").mode == "baked" and g.doc.node("bake").baked == g.key("bake") and g.standing("bake") == ""
    g.decoder.close()


def test_a_scrub_is_served_between_rows_and_the_bake_holds_one_row(tmp_path, in_store):
    tools = {**TOOLS, "slow": slow("slow", delay=0.03)}
    g = graph(clip(tmp_path / "v.avi"), "gray", "slow", tools=tools)
    events = []
    g.on_event = events.append
    w = Worker(g)
    held = []
    w.baked.connect(lambda n, i, total: held.append(w.bake_bytes) if 0 < i < total else None)
    w.baked.connect(lambda n, i, total: w.request_row(11) if i == 4 else None)
    done, refused = run_bake(w)
    w.stop()
    assert done and not refused, refused
    baked = [ev.t for ev in events if ev.serves == "bake" and ev.node == "slow"]
    scrubbed = [ev.t for ev in events if ev.serves == "scrub" and ev.node == "slow" and ev.row == 11]
    assert scrubbed and baked[0] < scrubbed[0] < baked[-1]
    assert held and max(held) <= H * W
    g.decoder.close()


def test_cancel_a_raise_and_a_refusing_store_leave_nothing_and_say_why(tmp_path, in_store, monkeypatch):
    path = clip(tmp_path / "v.avi")
    tools = {**TOOLS, "slow": slow("slow", delay=0.05)}
    g = graph(path, "gray", "slow", tools=tools)
    w = Worker(g)
    w.baked.connect(lambda n, i, total: w.cancel_bake() if i == 2 else None)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused == [("bake", "cancelled")] and g.standing("bake") == "cancelled"
    assert not list(in_store.iterdir()) and g.doc.node("bake").mode is None
    g.decoder.close()
    tools = {**TOOLS, "boom": slow("boom", boom=5)}
    g = graph(path, "gray", "boom", tools=tools)
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused[0][1].startswith("boom raised at row 5") and g.standing("bake") == refused[0][1]
    assert not list(in_store.iterdir())
    g.decoder.close()
    (in_store.parent / "f").write_bytes(b"")
    monkeypatch.setattr(store, "folder", lambda: str(in_store.parent / "f" / "under"))
    g = graph(path, "gray")
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert not done and "cannot be written" in refused[0][1] and g.doc.node("bake").mode is None
    g.decoder.close()


def test_a_kind_with_no_writer_is_refused_by_what_the_store_says(tmp_path, in_store):
    g = graph(clip(tmp_path / "v.avi"), "gray", "flow")
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused == [("bake", f"no writer for flow; a bake writes {', '.join(store.kinds())}")]
    assert g.standing("bake") == refused[0][1] and "flow" not in store.kinds() and "hsv" not in store.kinds()
    assert not in_store.exists()      # refused before the store was touched
    g.decoder.close()


@pytest.mark.parametrize("quality", ["lossless", "standard"])
def test_a_frame_kind_writes_a_clip_the_video_node_opens(tmp_path, in_store, quality, monkeypatch):
    monkeypatch.setattr(decoder_mod, "QUIET", True)
    path = clip(tmp_path / "v.avi")
    for chain, kind in ((("gray",), "gray"), ((), "bgr"), (("gray", "threshold"), "mask")):
        g = graph(path, *chain, quality=quality, increment=3)
        g.doc.node("bake").params["to"] = "10"
        g.sync()
        w = Worker(g)
        done, refused = run_bake(w)
        w.stop()
        assert done and not refused, refused
        want = [g.compute(chain[-1] if chain else "video", r) for r in range(0, 11, 3)]
        d = Decoder(store.place(g.key("bake"), ".mp4", str(in_store)))
        assert (d.count, d.fps, (d.height, d.width)) == (len(want), 10.0, (H, W)) and store.sidecar(g.key("bake"), str(in_store))["kind"] == kind
        if kind != "bgr":
            d.output = "gray"
            assert d.luma, "a baked gray is read through the luma path"
        got = [d.read(i) for i in range(len(want))]
        d.close()
        g.decoder.close()
        if kind == "mask":
            assert all(((a > 127) == (b > 127)).all() for a, b in zip(got, want))
        elif quality == "lossless":
            assert all((a == b).all() for a, b in zip(got, want)), kind
        else:
            assert max(np.abs(a.astype(int) - b.astype(int)).mean() for a, b in zip(got, want)) < 4.0, kind


def test_tables_and_a_signal_read_back_equal(tmp_path, in_store):
    path = clip(tmp_path / "v.avi")
    g = graph(path, "gray", "threshold", "blobs")
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert done and not refused, refused
    back = writers.read_tables(store.place(g.key("bake"), ".tables", str(in_store)))
    want = [g.compute("blobs", r) for r in range(N)]
    assert len(back) == N and all(len(t) for t in want)
    for a, b in zip(back, want):
        assert a.dtype == b.dtype and a.dtype.metadata == b.dtype.metadata
        for name in b.dtype.names:
            if name == "contour":
                assert all(np.array_equal(p, q) for p, q in zip(a[name], b[name]))
            else:
                np.testing.assert_array_equal(a[name], b[name])
    g.decoder.close()
    for chain, ext, pick in ((("gray", "threshold", "blobs", "track"), ".tables", "rows"), (("gray", "threshold", "blobs", "count"), ".csv", "signal")):
        g = graph(path, *chain)
        w = Worker(g)
        clips = []
        w.clipReady.connect(lambda r, s, fps: clips.append(r))
        done, refused = run_bake(w)
        w.stop()
        assert done and not refused, refused
        want = [r for r in clips if "bake" in r][-1]["bake"][pick]
        if pick == "rows":
            back = writers.read_tables(store.place(g.key("bake"), ext, str(in_store)))
            assert len(back) == N and all(a.dtype == b.dtype and (a["id"] == b["id"]).all() and (a["cx"] == b["cx"]).all() for a, b in zip(back, want))
        else:
            assert writers.read_signal(store.place(g.key("bake"), ext, str(in_store))).tolist() == np.asarray(want, np.float32).tolist()
        assert store.sidecar(g.key("bake"), str(in_store))["kind"] == ("tracks" if pick == "rows" else "signal")
        g.decoder.close()
