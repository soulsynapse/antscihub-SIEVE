"""Experiment behind docs/findings/2026-11-08-bake-window-fit.md: the window on the crossings clip with
rescale live, then baked, read off the monitor.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-08-bake-window-fit.py [document] [cache GB] [memo GB] [rows]

Loads the document (default video-tests/purb-168-178.json, whose format-1 scale becomes a rescale
node), splices a bake node after rescale, and runs the player's own Graph, Worker and Monitor
offscreen over a window of `rows`, the player's 10 s unless given: a cold walk and a rewalk live, the bake, then a cold walk
and a rewalk serving the file. Per phase it prints the monitor's summary, the read kinds, the plate
decoder's and the served reader's counters, and a line per node. The store is a fresh temp folder.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")     # the plugin warns per unconverted luma frame; the player hushes C stderr instead

from PySide6.QtWidgets import QApplication  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.monitor import Monitor, summary, walk_order  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "purb-168-178.json")
CACHE = int(float(sys.argv[2]) * 2**30) if len(sys.argv) > 2 else 4 << 30
MEMO = int(float(sys.argv[3]) * 2**30) if len(sys.argv) > 3 else 4 << 30
ROWS = int(sys.argv[4]) if len(sys.argv) > 4 else None
EVENTS = []     # the probe's stream, read per phase for the bake node's cost by read kind


def spin(done, timeout, what):
    t = time.perf_counter()
    while not done() and time.perf_counter() - t < timeout:
        QApplication.processEvents()
        time.sleep(0.005)
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
    s = spin(lambda: walked and walked[-1][0] == walked[-1][1] and (series or not g.chain), 600, "the walk")
    w.stop()
    g.halt = False
    return s


def bake(g, st, name):
    done, refused = [], []
    w = Worker(g, store=st)
    w.bakeDone.connect(lambda n, b: (done.append(b), D.land(g.doc.node(n), b)))
    w.bakeRefused.connect(lambda n, why: refused.append(why))
    w.set_window(0, 2)
    w.bake("bake", name)
    w.start()
    s = spin(lambda: done or refused, 1800, "the bake")
    w.stop()
    g.halt = False
    if refused:
        sys.exit(f"bake refused: {refused}")
    return s, done[0]


def bump(g, node, value):
    """Sets rescale's knob: a change upstream of everything the memo holds."""
    node.params["scale"] = value
    g.sync()


def report(label, g, mon, s, reader=None):
    snap = mon.snapshot()
    d = g.decoder
    print(f"\n== {label}: {s:.2f} s wall")
    print("\n".join("   " + ln for ln in summary(snap).splitlines()))
    print(f"   reads this walk: {dict(snap['nodes'][0]['kinds'] or {}) if snap['nodes'] and snap['nodes'][0]['kinds'] else '-'}")
    print(f"   plate decoder: {d.decodes} decodes, {d.seeks} seeks, {d.reads} reads of which {d.cache_hits} cached, "
          f"cache {d.cache_bytes / 2**20:.0f} MB; step {d.step_ms or 0:.2f} ms, seek {d.seek_ms or 0:.1f} ms")
    if reader is not None:
        r = reader.decoder
        print(f"   served reader: {r.width}x{r.height}, {r.decodes} decodes, {r.seeks} seeks, {r.reads} reads of which "
              f"{r.cache_hits} cached, cache {r.cache_bytes / 2**20:.0f} MB of {r.cache_limit >> 20} MB "
              f"({r.cache_limit / max(r.cache_bytes, 1):.1f} windows at this walk's rows); step {r.step_ms or 0:.2f} ms")
    print(f"   memo {snap['memo']['bytes'] / 2**20:.0f} MB held")
    by = {}
    for ev in EVENTS:
        if ev.node == "bake" and ev.kind in ("cache", "step", "seek", "read", "run"):
            n, ms = by.get(ev.kind, (0, 0.0))
            by[ev.kind] = (n + 1, ms + ev.ms)
    EVENTS.clear()
    if by:
        print("   bake node this phase: " + ", ".join(f"{n} {k} at {ms / n:.2f} ms" for k, (n, ms) in sorted(by.items())))
    print(f"   {'node':12} {'type':7} {'runs':>5} {'run ms':>7} {'MB/run':>7} {'share':>6} {'change s':>8}")
    for n in snap["nodes"]:
        share = f"{n['share']:.0%}" if n.get("share") is not None else "-"
        ch = f"{n['change_s']:.2f}" if n.get("change_s") is not None else "-"
        print(f"   {n['node']:12} {n['type']:7} {n['runs']:>5} {n['run_ms']:>7.2f} {n['run_bytes'] / 2**20:>7.2f} {share:>6} {ch:>8}")


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True                                            # as play() runs it: the luma plane read unconverted
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    rs = next(n for n in doc.nodes if n.tool == "rescale")
    b = doc.add_node("bake")
    for w in [w for w in doc.wires if w.src == rs.id]:
        doc.connect(b.id, w.dst, w.input)
    doc.connect(rs.id, b.id)
    folder = tempfile.mkdtemp(prefix="sieve-store-")
    st = store.Store(folder)
    st.probe()
    dec = Decoder(doc.video, cache_bytes=CACHE)
    g = Graph(doc, dec, tools, memo_bytes=MEMO, open_bake=lambda bk, c: st.open_bake(bk, c))
    g.on_event = EVENTS.append
    mon = Monitor(g)
    length = min(g.count, ROWS or round(10 * g.fps))     # the player's window on opening, 10 s
    b.params.update({"from": "0", "to": str(length - 1)})
    chain = " -> ".join(n for n in walk_order(doc) if n not in g.chain)
    print(f"{doc.video}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows, luma plane {'read' if dec.luma else 'converted'}; "
          f"rescale {rs.params}; window {length} rows; cache {CACHE >> 20} MB, memo {MEMO >> 20} MB; store {folder}")
    print(f"frame chain {chain}; series {g.chain}")
    print(f"a full-frame row is {dec.width * dec.height / 2**20:.2f} MB on the luma path, the window {dec.width * dec.height * length / 2**30:.2f} GB")

    report("live, cold", g, mon, walk(g, length))
    report("live, rewalk", g, mon, walk(g, length))
    scale = rs.params["scale"]
    bump(g, rs, scale * 1.02)
    report("live, rewalk after a change on rescale", g, mon, walk(g, length))
    bump(g, rs, scale)
    walk(g, length)         # back under the first key, which the memo still holds, before the bake

    s, bk = bake(g, st, os.path.basename(DOC))
    path = st.place(bk.key, ".mp4")
    print(f"\n== bake: {s:.1f} s for rows {bk.rows} every {bk.increment}, {os.path.getsize(path) / 2**20:.1f} MB on disk, "
          f"{bk.kind} {bk.shape} at quality {st.sidecar(bk.key).quality}; node mode {g.doc.node('bake').mode}")

    g.sync()
    print(f"   after sync: stale {g.stale}, chain {g.chain}, standing on bake {g.standing('bake')!r}")
    dec_before = (dec.decodes, dec.reads)
    s = walk(g, length)
    reader = g.readers.held(bk.key)
    report("baked, cold", g, mon, s, reader)
    print(f"   plate decoder moved by {dec.decodes - dec_before[0]} decodes, {dec.reads - dec_before[1]} reads during the baked walk")
    report("baked, rewalk", g, mon, walk(g, length), reader)
    bump(g, rs, scale * 1.02)
    print(f"   after the change: stale {g.stale}")
    report("baked, rewalk after a change on rescale", g, mon, walk(g, length), reader)

    g.close()
    dec.close()


if __name__ == "__main__":
    main()
