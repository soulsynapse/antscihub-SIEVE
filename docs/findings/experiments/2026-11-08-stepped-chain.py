"""Experiment behind the second half of docs/findings/2026-11-08-bake-window-fit.md: the crossings
window once the chain's prefix steps, read off the monitor.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-08-stepped-chain.py [document] [rows]

Loads the document (default video-tests/purb-168-178.json) and runs the player's own Graph, Worker
and Monitor offscreen over a window of `rows`, the player's 10 s unless given: a cold walk and a
rewalk at the default cadence, rewalks at shorter cadences, then tracks-filter and resolve spliced
under track and a cold walk and a rewalk with them. Per phase it prints the monitor's summary and a
line per node with the plan's verdict beside it; a stepping node's runs are its steps.
"""
import os
import sys
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

from PySide6.QtWidgets import QApplication  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.monitor import Monitor, summary  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "purb-168-178.json")
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else None
EVENTS = []


def spin(done, timeout, what):
    t = time.perf_counter()
    while not done() and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.005)
    if not done():
        sys.exit(f"{what} did not finish in {timeout} s")
    return time.perf_counter() - t


def walk(g, length, every=30):
    walked, series = [], []
    w = Worker(g, every=every)
    w.walked.connect(lambda d, n: walked.append((d, n)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.set_window(0, length)
    w.start()
    s = spin(lambda: walked and walked[-1][0] == walked[-1][1] and (series or not g.chain), 600, "the walk")
    w.stop()
    g.halt = False
    return s, len(series)


def report(label, g, mon, s, emits):
    snap = mon.snapshot()
    print(f"\n== {label}: {s:.2f} s wall, {emits} emits")
    print("\n".join("   " + ln for ln in summary(snap).splitlines()))
    by = {}
    for ev in EVENTS:
        if ev.kind in ("run", "step") and ev.node in g.chain:
            n, ms = by.get((ev.node, ev.kind), (0, 0.0))
            by[(ev.node, ev.kind)] = (n + 1, ms + ev.ms)
    EVENTS.clear()
    print(f"   {'node':14} {'type':7} {'verdict':8} {'runs':>5} {'run ms':>7} {'MB/run':>7} {'share':>6}   chain this phase")
    for n in snap["nodes"]:
        e = g.entry(n["node"])
        verdict = "-" if e is None or e.kind != "series" else "step" if e.steps else f"whole{' by ' + e.whole_by if e.whole_by else ''}"
        share = f"{n['share']:.0%}" if n.get("share") is not None else "-"
        chain = ", ".join(f"{c} {k} at {ms / c:.2f} ms, {ms / 1000:.2f} s" for (nid, k), (c, ms) in sorted(by.items()) if nid == n["node"])
        print(f"   {n['node']:14} {n['type']:7} {verdict:8} {n['runs']:>5} {n['run_ms']:>7.2f} {n['run_bytes'] / 2**20:>7.2f} {share:>6}   {chain}")


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools)
    g.on_event = EVENTS.append
    mon = Monitor(g)
    length = min(g.count, ROWS or round(10 * g.fps))
    print(f"{doc.video}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows; window {length} rows; series {g.chain}")

    report("live, cold, every 30", g, mon, *walk(g, length))
    report("live, rewalk, every 30", g, mon, *walk(g, length))
    for every in (10, 3, 1):
        report(f"live, rewalk, every {every}", g, mon, *walk(g, length, every))

    track = next(n for n in doc.nodes if n.tool == "track")
    below = [w for w in doc.wires if w.src == track.id]
    tf = doc.add_node("tracks-filter", params={**tools["tracks-filter"].DEFAULTS, "lo": "3"})
    # the tables carry no tag column; area is a read that never agrees twice, so the pass does its whole work
    rs = doc.add_node("resolve", params={**tools["resolve"].DEFAULTS, "columns": "area"})
    doc.connect(track.id, tf.id)
    doc.connect(tf.id, rs.id)
    for w in below:
        doc.connect(rs.id, w.dst, w.input)
    g.sync()
    print(f"\nseries now {g.chain}")
    report("with tracks-filter and resolve, cold, every 30", g, mon, *walk(g, length))
    report("with tracks-filter and resolve, rewalk, every 30", g, mon, *walk(g, length))

    g.close()
    dec.close()


if __name__ == "__main__":
    main()
