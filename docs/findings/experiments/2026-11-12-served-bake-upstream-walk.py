"""Experiment behind docs/findings/2026-11-12-served-bake-upstream-walk.md: video-tests/purb-settings.json over
one window, its bake node live and then serving its file, read off the monitor and off the raw event stream.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-12-served-bake-upstream-walk.py [rows] 2>NUL

A fresh Graph, Decoder and Monitor per phase, twice over, so each walk is cold in every store; then one Graph
and one Monitor across the switch, as a session that toggles the node has them. The bake is read from the
current store and must be there already. Per phase: the monitor's summary and table, then the events summed
per (node, kind), the wall they leave unprobed, and the plate decoder's and the served reader's counters.
"""
import os
import sys
import time
from collections import defaultdict

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 600
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.monitor import Monitor, summary, table  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
EVENTS = []


def spin(done, timeout, what):
    t = time.perf_counter()
    while not done() and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.002)
    if not done():
        sys.exit(f"{what} did not finish in {timeout} s")
    return time.perf_counter() - t


def walk(g, length):
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.set_window(0, length)
    w.start()
    s = spin(lambda: walked and walked[-1][0] == walked[-1][1] and (series or not g.chain), 900, "the walk")
    w.stop()
    g.halt = False
    return s


def report(label, g, mon, s, length):
    snap = mon.snapshot()
    print(f"\n== {label}: {s:.2f} s wall for {length} rows, {s / length * 1000:.2f} ms/row, "
          f"{length / g.fps / s:.2f}x realtime measured")
    print("\n".join("   " + ln for ln in summary(snap).splitlines()))
    print("\n".join("   " + ln for ln in table(snap).splitlines()))
    by = defaultdict(lambda: [0, 0.0, 0.0])
    for ev in EVENTS:
        if ev.kind in ("sync", "progress"):
            continue
        b = by[(ev.node or "-", ev.kind, ev.serves)]
        b[0] += 1
        b[1] += ev.ms
        b[2] += ev.cpu_ms
    EVENTS.clear()
    print(f"   {'node':14} {'kind':8} {'serves':6} {'n':>6} {'ms sum':>9} {'ms/row':>7} {'cpu sum':>9}")
    total = 0.0
    for (node, kind, serves), (n, ms, cpu) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        total += ms
        print(f"   {node:14} {kind:8} {str(serves):6} {n:>6} {ms:>9.1f} {ms / length:>7.3f} {cpu:>9.1f}")
    print(f"   probed {total:.0f} ms of {s * 1000:.0f} wall: {s * 1000 - total:.0f} ms unprobed, {(s * 1000 - total) / length:.3f} ms/row")
    d = g.decoder
    print(f"   plate decoder: {d.decodes} decodes, {d.seeks} seeks, {d.reads} reads, {d.cache_hits} cached, step {d.step_ms or 0:.2f} ms")
    for key, r in g.readers._held.items():
        rd = getattr(r, "decoder", None)
        if rd is not None:
            print(f"   reader {key}: {rd.width}x{rd.height} luma={rd.luma} limited={rd._limited}, {rd.decodes} decodes, "
                  f"{rd.seeks} seeks, {rd.reads} reads, {rd.cache_hits} cached, step {rd.step_ms or 0:.3f} ms")
    print(f"   memo {g.memo.bytes >> 20} MB, {g.memo.hits} hits, {g.memo.misses} misses, {g.memo.evictions} evictions")


def build(tools, st, mode):
    doc = D.load(DOC, tools)
    doc.node("bake").mode = mode
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    g.on_event = EVENTS.append
    return g, dec, Monitor(g)


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    for mode in (D.LIVE, D.BAKED, D.LIVE, D.BAKED):
        g, dec, mon = build(tools, st, mode)
        n = min(ROWS, g.count)
        if mode == D.BAKED:
            print(f"\n   plan, baked: fed frame nodes {g.frame_nodes()}, walk {g.walk}, chain {g.chain}, stale {g.stale}")
        report(f"fresh graph, {mode}, cold", g, mon, walk(g, n), n)
        g.close()
        dec.close()

    g, dec, mon = build(tools, st, D.LIVE)
    n = min(ROWS, g.count)
    report("one session, live, cold", g, mon, walk(g, n), n)
    g.doc.node("bake").mode = D.BAKED
    g.sync()
    report("one session, switched to baked", g, mon, walk(g, n), n)
    g.close()
    dec.close()


if __name__ == "__main__":
    main()
