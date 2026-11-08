"""Baking: a bake streams the node's input into the store on the worker with a scrub served between rows, lands a file and sidecar and marks the node baked, serves a key the store already has, leaves nothing on cancel or failure, survives a change elsewhere and goes on one upstream, refuses a kind with no writer, and what it wrote reads back: a clip the decoder opens through its luma path, tables and a signal equal."""
import os
import shutil
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
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="a bake's clip writer runs ffmpeg from PATH")


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
    return Graph(doc, Decoder(path), tools, open_bake=store.current().open_bake)


def run_bake(w, nid="bake", timeout=20.0):
    """Starts the worker on a bake and returns (done, refused) once one has been said; fails, with the
    node's standing and the worker's state, when neither is within `timeout`."""
    done, refused = [], []
    w.bakeDone.connect(lambda n, b: (done.append((n, b.key)), D.land(w.graph.doc.node(n), b)))   # as the window lands one
    w.bakeRefused.connect(lambda n, why: refused.append((n, why)))
    w.set_window(0, 2)
    w.bake(nid, os.path.basename(w.graph.doc.path or ""))     # as the window asks, naming the document
    if not w.isRunning():
        w.start()
    t = time.perf_counter()
    while not (done or refused) and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.005)
    if not (done or refused):
        state = f"worker running={w.isRunning()}, bake={w._bake}, standing={w.graph.standing(nid)!r}"
        w.stop()
        pytest.fail(f"bake {nid} said nothing in {timeout} s; {state}")
    return done, refused


def test_a_bake_lands_the_file_and_sidecar_and_marks_the_node_baked(tmp_path, in_store):
    g = graph(clip(tmp_path / "v.avi"), "gray", **{"from": "2", "to": "9", "increment": 2})
    w = Worker(g)
    done, refused = run_bake(w)
    key = g.key("bake")
    assert done == [("bake", key)] and not refused, refused
    side = store.Store(str(in_store)).sidecar(key)
    mp4 = store.Store(str(in_store)).place(key, ".mp4")
    assert os.path.exists(mp4) and not list(in_store.glob("*.part*"))
    assert side == store.Sidecar(key, "gray", "doc.json", "bake", [2, 8], 2, 30.0, 15.0, [H, W], "lossless", side.commit, side.written)
    assert side.bake(N) == g.doc.node("bake").baked and side.written
    assert g.doc.node("bake").mode == "baked" and g.doc.node("bake").baked.key == key and g.standing("bake") == ""
    # the store has the key: a second bake of the same chain serves the file rather than encoding it again
    g.sync()
    before = os.path.getmtime(mp4)
    g.doc.node("bake").mode = "live"
    g.sync()
    events = []
    g.on_event = events.append
    done, refused = run_bake(w)
    assert done == [("bake", key)] and not refused and os.path.getmtime(mp4) == before and g.doc.node("bake").mode == "baked"
    assert not [ev for ev in events if ev.serves == "bake"]
    # without its sidecar the file is not ours: baked again over it, which on Windows needs the reader sync() opened on it closed
    g.sync()
    assert g.compute("bake", 0) is not None
    os.remove(store.Store(str(in_store)).sidecar_path(key))
    g.doc.node("bake").mode = "live"
    g.sync()
    done, refused = run_bake(w)
    w.stop()
    assert done == [("bake", key)] and not refused, refused
    assert store.Store(str(in_store)).sidecar(key) is not None and os.path.getmtime(mp4) > before and not list(in_store.glob("*.part*"))
    g.close()
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
    def no_sidecar(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(store.Store, "write_sidecar", no_sidecar)
    g = graph(path, "gray")
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused[0][1].startswith("could not land the file: OSError: disk full")
    assert not list(in_store.iterdir())    # the clip had landed; without its sidecar it is not left
    g.decoder.close()
    monkeypatch.undo()
    (in_store.parent / "f").write_bytes(b"")
    monkeypatch.setattr(store, "folder", lambda: str(in_store.parent / "f" / "under"))
    g = graph(path, "gray")
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    assert not done and "cannot be written" in refused[0][1] and g.doc.node("bake").mode is None
    g.decoder.close()


def test_a_change_elsewhere_leaves_a_bake_writing_and_one_upstream_abandons_it(tmp_path, in_store):
    path = clip(tmp_path / "v.avi")
    tools = {**TOOLS, "slow": slow("slow", delay=0.03), "slowmask": slow("slowmask", "mask", "mask", delay=0.03)}
    g = graph(path, "gray", "slow", tools=tools)
    down = g.doc.add_node("threshold", params=threshold.DEFAULTS)
    g.doc.connect("bake", down.id)
    g.sync()
    w = Worker(g)

    def elsewhere(n, i, total):
        if i == 2:
            g.doc.node(down.id).params["thresh"] = 250
            g.sync()
            w.invalidate()
    w.baked.connect(elsewhere)
    done, refused = run_bake(w)
    w.stop()
    assert done == [("bake", g.key("bake"))] and not refused, refused
    g.close()
    g.decoder.close()
    g = graph(path, "gray", "threshold", "slowmask", tools=tools)
    w = Worker(g)

    def upstream(n, i, total):
        if i == 2:
            g.doc.node("threshold").params["thresh"] = 250
            g.sync()
            w.invalidate()
    w.baked.connect(upstream)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused == [("bake", "abandoned: a tool upstream changed")] and not list(in_store.glob("*.part*"))
    assert store.Store(str(in_store)).sidecar(g.key("bake")) is None and len(list(in_store.iterdir())) == 2    # the first bake's two alone
    g.decoder.close()


def test_a_series_bake_is_abandoned_when_the_chain_changes_under_its_walk(tmp_path, in_store):
    tools = {**TOOLS, "slowmask": slow("slowmask", "mask", "mask", delay=0.03)}
    g = graph(clip(tmp_path / "v.avi"), "gray", "threshold", "slowmask", "blobs", "count", tools=tools)
    w = Worker(g)

    def rerun(ci, clen):
        if ci == 3:
            g.doc.node("count").band = (0.0, 1.0)    # keyed like a param; the window reruns the chain for it
            g.sync()
            w.rerun_series()
    w.clipWalked.connect(rerun)
    done, refused = run_bake(w)
    w.stop()
    assert not done and refused == [("bake", "abandoned: a tool upstream changed")] and not list(in_store.iterdir())
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


def test_a_writer_that_cannot_open_refuses_the_bake_and_leaves_the_window_walk_alone(tmp_path, in_store, monkeypatch):
    """A raise while the bake starts is the bake's: it is refused naming the node, the window walks to its
    end and nothing is reported failed, where a walk closing at the bake's raise would stop it short."""
    class Shut:
        def __init__(self, *a, **k):
            raise OSError("the file is held")
    ext, _ = store.writer("gray")
    monkeypatch.setitem(store.WRITERS, "gray", (ext, Shut))
    g = graph(clip(tmp_path / "v.avi"), "gray")
    w = Worker(g)
    walked, failed = [], []
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.failed.connect(lambda r, nid: failed.append((r, nid)))
    done, refused = run_bake(w)          # asks a window of 2 beside the bake
    t = time.perf_counter()
    while (2, 2) not in walked and time.perf_counter() - t < 10:
        QApplication.processEvents()
        time.sleep(0.005)
    w.stop()
    assert not done and refused == [("bake", "did not start: OSError: the file is held")]
    assert (2, 2) in walked and not failed, (walked, failed)
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
        d = Decoder(store.Store(str(in_store)).place(g.key("bake"), ".mp4"))
        assert (d.count, d.fps, (d.height, d.width)) == (len(want), 10.0, (H, W)) and store.Store(str(in_store)).sidecar(g.key("bake")).kind == kind
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
    back = writers.read_tables(store.Store(str(in_store)).place(g.key("bake"), ".tables"))
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
            back = writers.read_tables(store.Store(str(in_store)).place(g.key("bake"), ext))
            assert len(back) == N and all(a.dtype == b.dtype and (a["id"] == b["id"]).all() and (a["cx"] == b["cx"]).all() for a, b in zip(back, want))
        else:
            assert writers.read_signal(store.Store(str(in_store)).place(g.key("bake"), ext)).tolist() == np.asarray(want, np.float32).tolist()
        assert store.Store(str(in_store)).sidecar(g.key("bake")).kind == ("tracks" if pick == "rows" else "signal")
        g.decoder.close()


def test_the_ladder_serves_a_scrub_then_a_bakes_start_then_its_rows_behind_the_window_then_the_clip(tmp_path, in_store):
    """With the walk held inside a tool at row 2, a scrub, a bake and a clip walk are asked; released,
    the row completes, the scrub is served, the bake says its first word, the walk resumes, the bake
    writes every row behind the finished window, and the clip walk runs behind the bake's landing."""
    import threading
    arrived, gate = threading.Event(), threading.Event()

    def held(frames, row, params):
        f = frames(row)
        if row == 2 and not arrived.is_set():
            arrived.set()
            gate.wait(5)
        return f
    tools = {**TOOLS, "held": Tool(NAME="held", KIND="frame", EXPECTS="gray", PRODUCES="gray", DEFAULTS={}, run=held)}
    g = graph(clip(tmp_path / "v.avi"), "gray", "held", tools=tools)
    w = Worker(g)
    served = []
    w.walked.connect(lambda d, n: served.append(("walked", d)))
    w.rowReady.connect(lambda r: served.append(("row", r)))
    w.baked.connect(lambda n, i, total: served.append(("baked", i)))
    w.bakeDone.connect(lambda n, b: served.append(("landed", n)))
    w.bakeRefused.connect(lambda n, why: served.append(("refused", why)))
    w.clipWalked.connect(lambda d, n: served.append(("clip", d)))
    w.set_window(0, 6)
    w.start()
    assert arrived.wait(5)
    w.request_row(11)
    w.bake("bake", "doc.json")
    w.walk_clip()
    gate.set()
    t = time.perf_counter()
    while ("clip", N) not in served and time.perf_counter() - t < 20:
        QApplication.processEvents()
        time.sleep(0.005)
    w.stop()
    assert ("landed", "bake") in served and ("clip", N) in served, served
    at = served.index
    assert at(("walked", 3)) < at(("row", 11)) < at(("baked", 0)) < at(("walked", 4)), served
    assert at(("walked", 6)) < at(("baked", 1)) and at(("baked", N)) < at(("landed", "bake")) < at(("clip", 1)), served
    g.decoder.close()
