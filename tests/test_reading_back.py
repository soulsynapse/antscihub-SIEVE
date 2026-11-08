"""Reading back: a served node is a source keyed by its bake, the document's row space is the file's behind an unaligned bake and the plate's upstream of it, nothing above a served node runs or decodes, a served series node heads the chain, an upstream change marks it stale with live and a rebake as the ways out, a document reopens baked or live as the store has the file, and a baked clip opens as a video."""
import os
import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from sieve_player import document as D
from sieve_player import store, writers
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.plan import _key, base_key, plan
from sieve_player.worker import Worker
from tests.test_baking import H, N, W, TOOLS as BASE, clip, pytestmark, run_bake, slow  # noqa: F401  pytestmark skips without ffmpeg
from tools import bake, csv, rescale, reduce, smooth, threshold

TOOLS = {**BASE, **{t.NAME: t for t in (csv, rescale, reduce, smooth)}}


def build(path, *chain, tools=TOOLS, **params):
    """video -> chain, in list order with `bake` where named, the bake carrying `params`."""
    QApplication.instance() or QApplication([])
    doc = D.from_tools([tools[n] for n in chain], path)
    doc.node("bake").params.update(params)
    doc.path = os.path.join(os.path.dirname(path), "doc.json")
    return Graph(doc, Decoder(path), tools, open_bake=store.open_bake)


def baked(g):
    w = Worker(g)
    done, refused = run_bake(w)
    w.stop()
    g.halt = False      # stop() halts the graph for good, as a window closes it; here the graph outlives its worker
    return done, refused


def walk(g, start, length, timeout=10.0):
    """One window walk: the chain's results and every probe event it raised. The walk is over when the
    worker says it walked every row and, with a chain, the chain's result is in, which a walk headed by a
    served series node says without a probe progress event; fails when that is not within `timeout`."""
    events, series, walked = [], [], []
    g.on_event = events.append
    w = Worker(g)
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.walked.connect(lambda done, total: walked.append((done, total)))
    w.set_window(start, length)
    w.start()
    t = time.perf_counter()
    while time.perf_counter() - t < timeout:
        QApplication.processEvents()
        if walked and walked[-1][0] == walked[-1][1] and (series or not g.chain):
            break
        time.sleep(0.005)
    else:
        w.stop()
        pytest.fail(f"the walk from {start} over {length} did not finish in {timeout} s: walked={walked[-3:]}, "
                    f"series={bool(series)}, chain={g.chain}")
    w.stop()
    g.halt, g.on_event = False, None
    return series[-1] if series else None, events


def test_the_row_space_is_the_files_behind_a_bake_and_the_plates_upstream(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "bake", "threshold", "reduce", "csv", increment=3)
    assert g.doc.display == "threshold" and (g.count, g.fps) == (N, 30.0)
    done, refused = baked(g)
    assert done and not refused, refused
    g.sync()
    assert (g.axis, g.count, g.fps, g.plate) == ("bake", 4, 10.0, (0, 3)) and g.off == {"gray"}
    assert g.standing("gray") == "in the plate's row space; the display is behind bake" and g.standing("threshold") == ""
    results, events = walk(g, 0, 4)
    assert results["csv"]["plate"] == (0, 3) and len(results["csv"]["signal"]) == 4
    assert "plate=0:3" in csv.text(results["csv"], 0, g.fps, "v.avi").splitlines()[0]
    assert {ev.row for ev in events if ev.node == "threshold" and ev.kind == "run"} == {0, 1, 2, 3}
    g.doc.display = "gray"
    g.sync()
    assert (g.axis, g.count, g.fps, g.plate) == (None, N, 30.0, None) and g.off == {"bake", "threshold", "reduce", "csv"}
    assert g.standing("threshold") == "in bake's row space; the display is in the plate's" and not g.fed("csv")
    g.close()
    g.decoder.close()


def test_a_served_node_is_fed_unwired_keyed_by_its_bake_and_produces_the_sidecars_kind(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "bake", "threshold")
    done, refused = baked(g)
    assert done and not refused, refused
    g.sync()
    key, down = g.key("bake"), g.key("threshold")
    assert key == _key("served", g.doc.node("bake").baked.key) and g.axis is None      # increment 1 over the whole clip: aligned, one row space
    g.doc.disconnect("bake")
    g.sync()
    assert g.fed("bake") and g.fed("threshold") and (g.key("bake"), g.key("threshold")) == (key, down)
    assert D.produces(g.doc, TOOLS, "bake") == "gray" and g.standing("bake") == ""
    g.doc.connect("video", "bake")         # bgr into a served gray node: it still hands out the file's gray
    g.sync()
    assert D.produces(g.doc, TOOLS, "bake") == "gray" and (g.key("bake"), g.key("threshold")) == (key, down) and g.fed("threshold")
    assert g.compute("bake", 2).shape == (H, W) and (g.compute("bake", 2) == g.compute("threshold", 2) * 0 + g.compute("bake", 2)).all()
    g.close()
    g.decoder.close()


def test_the_plan_is_the_same_with_the_store_present_and_absent(tmp_path, in_store, monkeypatch):
    g = build(clip(tmp_path / "v.avi"), "gray", "bake", "threshold", increment=2)
    done, refused = baked(g)
    assert done and not refused, refused
    base = base_key(g.decoder.path, "bgr")
    with_store = plan(g.doc, TOOLS, base)
    monkeypatch.setattr(store, "folder", lambda: str(tmp_path / "nowhere"))
    without = plan(g.doc, TOOLS, base)
    assert with_store == without and with_store.axis == "bake" and with_store.rows == (6, 15.0)
    g.close()
    g.decoder.close()


def test_baked_mode_decodes_no_video_row_and_runs_nothing_upstream(tmp_path, in_store):
    tools = {**TOOLS, "up": slow("up")}
    g = build(clip(tmp_path / "v.avi"), "gray", "up", "bake", "threshold", tools=tools)
    live = [g.compute("threshold", r).copy() for r in range(N)]
    done, refused = baked(g)
    assert done and not refused, refused
    g.sync()
    _, events = walk(g, 0, N)
    assert not [ev for ev in events if ev.node in ("video", "gray", "up") and ev.kind in ("run", "cache", "step", "seek")]
    assert {ev.row for ev in events if ev.node == "bake" and ev.kind in ("cache", "step", "seek")} == set(range(N))
    assert {ev.row for ev in events if ev.node == "threshold" and ev.kind == "run"} == set(range(N))
    assert all((g.compute("threshold", r) == live[r]).all() for r in range(N))
    g.close()
    g.decoder.close()


def test_a_served_series_node_heads_the_chain_on_the_files_rows(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "threshold", "blobs", "count", "bake", "smooth")
    done, refused = baked(g)
    assert done and not refused, refused
    g.doc.node("threshold").params["thresh"] = 250
    g.sync()
    assert g.stale == {"bake"} and g.doc.node("bake").mode == "baked" and g.walk is None and g.heads == ["bake"] and g.chain == ["bake", "smooth"]
    results, events = walk(g, 2, 6)
    signal = writers.read_signal(store.place(g.doc.node("bake").baked.key, ".csv"))
    assert results["bake"]["signal"].tolist() == signal[2:8].tolist() and len(results["smooth"]["signal"]) == 6
    assert not [ev for ev in events if ev.node in ("video", "gray", "threshold", "blobs", "count") and ev.serves == "walk"]
    g.close()
    g.decoder.close()


def test_an_upstream_change_marks_stale_live_takes_the_live_key_and_a_rebake_lands_beside(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "rescale", "bake", "threshold")
    done, refused = baked(g)
    assert done and not refused, refused
    g.sync()
    key, down = g.key("bake"), g.key("threshold")
    g.doc.node("rescale").params["scale"] = 0.75
    g.sync()
    assert g.stale == {"bake"} and g.doc.node("bake").mode == "baked"     # stale is the plan's verdict; the saved mode is the choice
    assert (g.key("bake"), g.key("threshold")) == (key, down) and g.compute("threshold", 0).shape == (H // 2, W // 2)
    assert "mode" in D.Document.from_dict(g.doc.to_dict()).node("bake").__dict__ and D.Document.from_dict(g.doc.to_dict()).node("bake").mode == "baked"
    g.doc.node("bake").mode = "live"
    g.sync()
    assert not g.stale and g.key("bake") != key and g.key("threshold") != down and g.compute("threshold", 0).shape == (36, 48)
    done, refused = baked(g)
    assert done and not refused, refused
    g.sync()
    assert not g.stale and g.doc.node("bake").mode == "baked" and g.doc.node("bake").baked.key != key
    assert sorted(p.suffix for p in in_store.iterdir()) == [".json", ".json", ".mp4", ".mp4"]
    second = g.doc.add_node("bake", id="bake2")        # a bake after a served bake was baked under the served key, and is not stale for it
    g.doc.connect("threshold", second.id)
    g.sync()
    D.land(second, D.Bake(g.key(second.id), "mask", False, (0, N - 1), 1, 30.0, 30.0, (36, 48), N))
    g.sync()
    assert not g.stale
    g.doc.node("rescale").params["scale"] = 0.5
    g.sync()
    assert g.stale == {"bake"}
    g.close()
    g.decoder.close()


def test_a_document_reopens_baked_or_live_as_the_store_has_the_file(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "bake", "threshold", increment=2)
    done, refused = baked(g)
    assert done and not refused, refused
    key = g.doc.node("bake").baked.key
    D.save(g.doc, g.doc.path)
    g.close()
    g.decoder.close()
    again = D.load(g.doc.path, TOOLS)
    g2 = Graph(again, Decoder(again.video_path()), TOOLS, open_bake=store.open_bake)
    assert again.node("bake").mode == "baked" and g2.key("bake") == _key("served", key) and (g2.count, g2.fps) == (6, 15.0)
    g2.close()
    g2.decoder.close()
    os.remove(store.place(key, ".mp4"))
    gone = D.load(g.doc.path, TOOLS)
    missing = store.missing(gone)          # as the window asks where the document opens, then sets the node live and notes why
    assert list(missing) == ["bake"] and missing["bake"].startswith(f"bake {key} is not in the store") and missing["bake"].endswith("serving live")
    gone.node("bake").mode = D.LIVE
    g3 = Graph(gone, Decoder(gone.video_path()), TOOLS, open_bake=store.open_bake)
    g3.note("bake", missing["bake"])
    assert g3.key("bake") == key and (g3.count, g3.fps) == (N, 30.0) and g3.standing("bake") == missing["bake"]   # live again, under the key it was baked under
    g4 = Graph(again, Decoder(again.video_path()), TOOLS, open_bake=store.open_bake)   # a file gone under a document still serving: the read says so
    with pytest.raises(IOError):
        g4.compute("bake", 0)
    assert g4.standing("bake").startswith(f"bake {key} is not in the store")
    g4.decoder.close()
    g3.decoder.close()


def test_a_baked_clip_opens_as_another_documents_video(tmp_path, in_store):
    g = build(clip(tmp_path / "v.avi"), "gray", "bake", "threshold", increment=3)
    g.doc.node("bake").params["to"] = "10"
    g.sync()
    done, refused = baked(g)
    assert done and not refused, refused
    path = store.place(g.doc.node("bake").baked.key, ".mp4")
    g.close()
    g.decoder.close()
    doc = D.from_tools([threshold], path)
    doc.video_node().params["output"] = "gray"
    doc.connect("video", "threshold")      # wired by hand: the list build saw a bgr video and nothing threshold reads
    g2 = Graph(doc, Decoder(path), TOOLS)
    assert (g2.count, g2.fps) == (4, 10.0) and g2.compute("video", 3).shape == (H, W) and g2.compute("threshold", 3).shape == (H, W)
    g2.decoder.close()
