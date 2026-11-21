"""The one-off of docs/spec/a-cut-in-time.md's box of each period walked alone and held, and a table
below a `period` holding every period's rows: over the crossings clip, the document of
2026-11-20-stepped-nodes-of-two-extents.py with a `csv` below `track`, opened in the player, Walk
clip clicked once, and the walk run until every period is held, the window's own walk holding the
gate's run and so cutting the periods while the clip walk is under way; then the rows each node was
stepped over against the periods', and the file the csv card's Write would write, read back, its
lines against each period's rows and the records `track`'s held run of that period has.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-table-of-every-period.py 2>NUL

Qt runs offscreen, so no window opens, and the worker's turns are taken on this thread.
"""
import os
import sys
import tempfile
import threading
import time
import traceback
from collections import Counter

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402
from sieve_player.graph import Cancelled, Graph, Series  # noqa: E402
from sieve_player.registry import computed, defaults, discover  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402
from tools import _csvfile  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")


TURNS = 1_000_000


def turned(w, between=None):
    """Takes the Worker `w`'s turns on this thread, as its loop takes them, until no rung is due,
    calling `between` after each; the turns taken."""
    threading.current_thread().name = "worker"     # as Worker.run names its thread: the probe and Readers.reap read it
    for turns in range(TURNS):
        with w._cv:
            turn = w._turn()
        if turn is None:
            return turns
        serves, steps = turn
        w.graph.readers.reap()
        job = None
        try:
            for job, act in steps:
                w.graph.serving(serves, job.name)
                act()
        except Cancelled:
            job.cancelled()
        except EndOfStream:
            w.shortened.emit(w.graph.count)
            job.ended()
        except Exception as e:
            traceback.print_exc()
            job.raised(e)
        if between is not None:
            between()
    raise RuntimeError(f"still turning after {TURNS} turns")


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    entries = [e for e in discover(os.path.join(ROOT, "tools")) if e.ok]
    tools = {e.name: e.module for e in entries}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n, fps = g.count, g.fps
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    g.close()
    g.decoder.close()
    count = tools["count"]
    result = count.run(Series(blobs, "k", 0, fps), computed(count, defaults(count)))
    doc.node("count").band = (float(np.median(result["signal"])), float(np.max(result["signal"])))
    period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    below = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
    doc.disconnect("track", "in")
    doc.connect("threshold", period)
    doc.connect(period, below)
    doc.connect(below, "track")
    doc.connect("count", period, "gate")
    table = doc.add_node("csv", (0.0, 0.0), defaults(tools["csv"])).id
    doc.connect("track", table)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "doc.json")
        D.save(doc, path)
        Worker.start = lambda self: None      # the window's worker turns on this thread, not its own
        win = PlayerWindow(path, "t", entries)
        win.resize(1280, 720)
        win.show()
        if win.playing:
            win.toggle_play()
        stepped = {}

        def on_event(ev, was=win.graph.on_event):
            if ev.kind == "step" and ev.lane == "clip":
                stepped.setdefault(ev.node, []).append(ev.row)
            if was is not None:
                was(ev)

        win.graph.on_event = on_event
        win._toggle_clip()
        cuts = lambda: [c.extent.rows for c in win.graph.entry(table).cuts] if win.graph.entry(table) else []
        card = lambda: win.pane.widget(table)
        held = lambda: len({r for r, *_ in (card().result or {}).get("periods", [])}) if card() is not None else 0
        t = time.perf_counter()
        turned(win.worker, between=app.processEvents)
        took = time.perf_counter() - t
        periods = cuts()
        print(f"{n} rows; one click of Walk clip, {took:.1f} s; {len(periods)} periods, {held()} held on the csv card")
        print(f"runs of a cut held: {sum(1 for r in win.runs if r.cut)}; rows stepped a node: {({k: len(v) for k, v in stepped.items()})}")

        within = [r for a, b in periods for r in range(a, b)]
        for nid in ("track", "travel"):
            rows = stepped.get(nid, [])
            print(f"{nid:<6} stepped over each period's rows alone, once, in order: {rows == within}; "
                  f"over a row outside every period: {sorted(set(rows) - set(within))[:5] or 'none'}")

        out = os.path.join(tmp, tools["csv"].default_name(win.decoder.path, 0, 0, card().result))
        tools["csv"].write(out, card().result, 0, fps, win.decoder.path)
        key, start, rows, header, lines, kind = _csvfile.read(out)
        print(f"{os.path.basename(out)}: kind {kind}, rows {start}-{start + rows - 1}, header {header[:5]}")
        at = {c: header.index(c) for c in ("row", "period_first", "period_end")}
        said = Counter((int(p[at["period_first"]]), int(p[at["period_end"]])) for p in lines)
        outside = [p for p in lines if not int(p[at["period_first"]]) <= int(p[at["row"]]) < int(p[at["period_end"]])]
        chain = win._chain(next(w.chain for w in win.graph.snapshot().timed if "track" in w.chain))
        want = {}
        for c in win.graph.entry("track").cuts:
            lst = win.runs.listed("track", chain, c, n)
            want[c.extent.rows] = sum(len(t) for _, part in lst.parts for t in part["rows"] if t is not None)
        print(f"every line's row inside the period it says: {not outside}")
        print(f"each period's lines the records track's held run of it has: {all(said.get(p, 0) == want[p] for p in periods)}; "
              f"periods with records {sum(1 for p in periods if want[p])}, lines {len(lines)}")
        print(f"the key line is track's key under csv: {key.split()[2] == 'key=' + win.graph.entry(table).key}")
        win.close()
