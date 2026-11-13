"""Experiment behind docs/findings/2026-11-12-what-a-walk-holds.md: what a clip walk of
video-tests/purb-settings.json holds against worker.STACK_BYTES, by node and a row, and what the series
tools that cannot step cost run whole over the walk's own tracks, fitted and summed over an hour's emits.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-what-a-walk-holds.py [saved | live] 2>NUL

`saved` is the document as it is saved and `live` every bake live. The Session is the cold-window
experiment's.
"""
import importlib.util
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cold", os.path.join(HERE, "2026-11-12-a-cold-window-and-the-clip.py"))
cold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cold)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series, nbytes  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import STACK_BYTES  # noqa: E402
from tools import csv, resolve, smooth, tracks_filter  # noqa: E402

HOUR = 3600
EVERY = 30


def held(live):
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(cold.ROOT, "tools")) if e.ok}
    st = store.current()
    doc = D.load(cold.DOC, tools)
    for node in doc.nodes:
        if live and node.tool == "bake":
            node.mode = D.LIVE
    s = cold.Session(Graph(doc, Decoder(doc.video), tools, open_bake=lambda bk, c: st.open_bake(bk, c)), EVERY)
    _, wall = s.clip()
    w, fps = s.worker._clip, s.graph.fps
    n = w.i
    hour = int(HOUR * fps)
    print(f"\n== purb-settings, {'every bake live' if live else 'as saved'}: {n} rows at {fps:.2f} fps walked in {wall:.1f} s; "
          f"the chain {', '.join(s.graph.chain)}; stepped {', '.join(w.stepped)}")
    print(f"   the walk's bytes {w.bytes / 2**20:.1f} MB of {STACK_BYTES / 2**20:.0f}, {w.bytes / n:.0f} a row; "
          f"at that the cap is reached at row {int(STACK_BYTES / (w.bytes / n))}, {STACK_BYTES / (w.bytes / n) / fps / 60:.1f} min, "
          f"and an hour's {hour} rows would be {w.bytes / n * hour / 2**30:.2f} GB")
    stack = 0 if w.stack is None else sum(nbytes(r) for r in w.stack[:n])
    print(f"   {'held':16} {'MB':>8} {'bytes a row':>12} {'largest row':>12}")
    if w.stack is not None:
        print(f"   {'the stack':16} {stack / 2**20:>8.1f} {stack / n:>12.0f} {max(nbytes(r) for r in w.stack[:n]):>12}")
    for nid, h in w.stepped.items():
        per = [sum(nbytes(a[r]) for a in h.fields.values()) for r in range(h.rows)]
        print(f"   {nid:16} {h.bytes / 2**20:>8.1f} {h.bytes / max(h.rows, 1):>12.0f} {max(per):>12}   {', '.join(h.fields)}")
    rows = w.stepped["track"].fields["rows"][:n]
    recs = np.array([len(t) for t in rows])
    flat = sum(t.nbytes for t in rows)
    whole = sum(nbytes(t) for t in rows)
    print(f"   track's tables: {recs.mean():.1f} records a row, {recs.max()} at most, {rows[0].dtype.itemsize} bytes a record; "
          f"{flat / n:.0f} bytes a row in records and {(whole - flat) / n:.0f} behind their contours")
    signal = np.array(w.stepped["count"].fields["signal"][:n], np.float32)
    s.close()
    return rows, signal, fps


def whole(rows, signal, fps):
    """Each whole-run tool timed over prefixes of the walk's own rows, the ms a run fitted against
    the rows and summed over the emits of the clip and of an hour."""
    n, hour = len(rows), int(HOUR * fps)
    cases = [("smooth mean 2", smooth, signal, {"kernel": "mean", "reach": 2}),
             ("smooth median 60", smooth, signal, {"kernel": "median", "reach": 60}),
             ("tracks-filter rows", tracks_filter, rows, {**tracks_filter.DEFAULTS}),
             ("tracks-filter path", tracks_filter, rows, {**tracks_filter.DEFAULTS, "property": "path"}),
             ("resolve, no reads", resolve, rows, {**resolve.DEFAULTS, "columns": ""}),
             ("csv over tracks", csv, rows, dict(csv.DEFAULTS)),
             ("csv over a signal", csv, signal, dict(csv.DEFAULTS))]
    sizes = [n // 8, n // 4, n // 2, n]
    print(f"   run whole over the first rows of the walk, ms a run; then every {EVERY} rows, in seconds")
    print(f"   {'tool':20}" + "".join(f"{k:>10}" for k in sizes) + f"{'ms a row':>10} {'the clip':>10} {'an hour':>10} {'once, an hour':>14}")
    for name, tool, data, params in cases:
        ms = []
        for k in sizes:
            t = time.perf_counter()
            tool.run(Series(data[:k], "k", 0, fps), params)
            ms.append((time.perf_counter() - t) * 1000)
        b, a = np.polyfit(sizes, ms, 1)
        total = lambda r: sum(a + b * EVERY * k for k in range(1, r // EVERY + 1)) / 1000  # noqa: E731
        print(f"   {name:20}" + "".join(f"{m:>10.1f}" for m in ms) + f"{b:>10.5f} {total(n):>10.1f} {total(hour):>10.0f} {(a + b * hour) / 1000:>14.1f}")


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    for name in sys.argv[1:] or ["saved"]:
        rows, signal, fps = held(name == "live")
        if name == "saved" or len(sys.argv) == 2:
            whole(rows, signal, fps)
