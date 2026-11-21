"""The one-off of docs/spec/a-cut-in-time.md's second box of Outside a cut is absent, over the
crossings clip: `count` and `smooth` below `track`, whose band shuts out the rows where fewer tracks
are seen than its median, walked by the clip lane; their results over the gated-out runs against
the same rows read as zero, and a `csv` below `count` writing no line for them.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-gated-out-row-is-absent.py 2>NUL

The band is this script's. Qt runs offscreen, so no window opens.
"""
import os
import sys
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")


def walked(app, g):
    """The clip walk's results once it reaches the clip's last row."""
    got = []
    w = Worker(g, every=1 << 30)
    w.clipReady.connect(lambda r, s, f: got.append(r), Qt.DirectConnection)
    w.walk_clip()
    t0 = time.perf_counter()
    w.start()
    while time.perf_counter() - t0 < 20 and not (got and len(got[-1].get("track", {}).get("signal", ())) == g.count):
        app.processEvents()
        time.sleep(0.01)
    w.stop()
    return got[-1]


def runs(mask):
    edges = np.flatnonzero(np.diff(np.concatenate(([0], mask.astype(np.int8), [0]))))
    return list(zip(edges[0::2], edges[1::2]))


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    t_all = time.perf_counter()

    doc = D.load(DOC, tools)
    for nid in [n.id for n in doc.nodes if n.tool in ("travel", "size", "count")]:
        doc.remove_node(nid)
    doc.node("track").band = None
    count = doc.add_node("count", (0.0, 0.0), defaults(tools["count"])).id
    smooth = doc.add_node("smooth", (0.0, 0.0), {**defaults(tools["smooth"]), "reach": 3}).id
    csv = doc.add_node("csv", (0.0, 0.0), defaults(tools["csv"])).id
    doc.connect("track", count)
    doc.connect(count, smooth)
    doc.connect(count, csv)
    g = Graph(doc, Decoder(doc.video), tools)
    open_ = walked(app, g)
    g.close()
    tracks = np.asarray(open_["track"]["signal"], np.float64)
    lo = float(np.median(tracks))
    print(f"{len(tracks)} rows; track's signal median {lo:g}, band ({lo:g}, inf)")

    doc.node("track").band = (lo, float("inf"))
    g = Graph(doc, Decoder(doc.video), tools)
    banded = walked(app, g)
    g.close()
    gate = np.asarray(banded["track"]["gate"], bool)
    out = runs(~gate)
    print(f"track's gate shuts out {int((~gate).sum())} rows in {len(out)} runs, the longest {max(b - a for a, b in out)} rows")

    c = np.asarray(banded[count]["signal"], np.float64)
    kept_same = np.array_equal(c[gate], np.array([len(t) for t in open_["track"]["rows"]], np.float64)[gate])
    print(f"count over the gated-out rows: NaN at every one: {bool(np.isnan(c[~gate]).all())}, "
          f"where an emptied table counted 0; over the kept rows the records track holds: {kept_same}")

    s = np.asarray(banded[smooth]["signal"], np.float64)
    zeroed = np.where(gate, c, 0.0)
    padded = np.concatenate((np.full(3, np.nan), zeroed, np.full(3, np.nan)))
    as_zero = np.nanmean(np.lib.stride_tricks.sliding_window_view(padded, 7), axis=1)
    edge = [a - 1 for a, _ in out if a > 0] + [b for _, b in out if b < len(c)]
    print(f"smooth over the gated-out rows NaN: {bool(np.isnan(s[~gate]).all())}; at the {len(edge)} kept rows beside a run, "
          f"the mean over present rows against the same read as zero, the largest difference {np.nanmax(np.abs(s[edge] - as_zero[edge])):.3f}, "
          f"smooth's the larger at {int((s[edge] > as_zero[edge] + 1e-6).sum())} of them")

    lines = tools["csv"].text(banded[csv], 0, g.fps, doc.video).splitlines()[2:]
    written = {int(line.split(",")[0]) for line in lines}
    print(f"csv below count: {len(written)} lines, one per kept row: {written == set(np.flatnonzero(gate).tolist())}")
    print(f"in {time.perf_counter() - t_all:.1f} s")
