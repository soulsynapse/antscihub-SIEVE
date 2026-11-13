"""Left as 4203efbc added it, over the tree its finding names, 50d07ce7, and run from there: the monitor
it imports, sieve_player/dev/monitor.py, is gone from the tree since docs/spec/monitor.md.

Experiment behind docs/findings/2026-11-09-crop-cold-walk.md: the crossings window with the blobs
chain after a crop to a drawn region, against the same window uncropped, read off the monitor.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-09-crop-cold-walk.py [shape|none] [geometry] [document] [rows]

Loads the document (default video-tests/purb-168-178.json) and, unless `none`, splices video ->
region(geometry) -> blobs-to-mask -> crop.roi and video -> crop -> rescale, the region narrowed to
`shape` (default dish, from video-tests/00000_168-178.nest.geometry.json); the geometry lands on the
region's params as the window's loader would. Runs the player's own Graph, Worker and Monitor
offscreen over the window: a cold walk, a rewalk, a rewalk after a change on rescale, then a
lossless bake after rescale and a cold walk serving it. Per phase it prints the monitor's summary, the
plate decoder's counters and a line per node. The store is a fresh temp folder.
"""
import os
import sys
import tempfile
import time

import numpy as np

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

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

SHAPE = sys.argv[1] if len(sys.argv) > 1 else "dish"
GEOMETRY = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "video-tests", "00000_168-178.nest.geometry.json")
DOC = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "video-tests", "purb-168-178.json")
ROWS = int(sys.argv[4]) if len(sys.argv) > 4 else None


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
    s = spin(lambda: walked and walked[-1][0] == walked[-1][1] and (series or not g.chain), 120, "the walk")
    w.stop()
    g.halt = False
    return s, series[-1] if series else {}


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


def report(label, g, mon, s):
    snap = mon.snapshot()
    d = g.decoder
    print(f"\n== {label}: {s:.2f} s wall")
    print("\n".join("   " + ln for ln in summary(snap).splitlines()))
    print(f"   plate decoder: {d.decodes} decodes, {d.seeks} seeks, {d.reads} reads of which {d.cache_hits} cached, "
          f"cache {d.cache_bytes / 2**20:.0f} MB; step {d.step_ms or 0:.2f} ms")
    print(f"   memo {snap['memo']['bytes'] / 2**20:.0f} MB held")
    print(f"   {'node':14} {'type':7} {'runs':>5} {'run ms':>7} {'MB/run':>7} {'share':>6}")
    for n in snap["nodes"]:
        share = f"{n['share']:.0%}" if n.get("share") is not None else "-"
        print(f"   {n['node']:14} {n['type']:7} {n['runs']:>5} {n['run_ms']:>7.2f} {n['run_bytes'] / 2**20:>7.2f} {share:>6}")


def splice_crop(doc, tools, shape):
    from tools import crop as cropmod
    from tools import blobs_to_mask, region

    video = doc.video_node().id
    rs = next(n for n in doc.nodes if n.tool == "rescale")
    geometry = region.load_geometry(GEOMETRY)
    rg = doc.add_node("region", params={**geometry, "choice": shape})
    bm = doc.add_node("blobs-to-mask")
    cr = doc.add_node("crop")
    doc.connect(video, rg.id)
    doc.connect(rg.id, bm.id)
    doc.connect(video, cr.id)
    doc.connect(bm.id, cr.id, "roi")
    doc.connect(cr.id, rs.id)
    roi = blobs_to_mask.mask(region.table(geometry["plate"], geometry["shapes"], shape))
    y0, y1, x0, x1 = cropmod.rect(roi)
    h, w = geometry["plate"]
    print(f"crop to {shape}: x {x0}-{x1}, y {y0}-{y1}, {x1 - x0}x{y1 - y0} of {w}x{h}, "
          f"{(x1 - x0) * (y1 - y0) / (w * h):.1%} of the plate's pixels")


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    rs = next(n for n in doc.nodes if n.tool == "rescale")
    if SHAPE != "none":
        splice_crop(doc, tools, SHAPE)
    b = doc.add_node("bake")
    for w in [w for w in doc.wires if w.src == rs.id]:
        doc.connect(b.id, w.dst, w.input)
    doc.connect(rs.id, b.id)
    doc.resolve(tools)      # the spliced nodes' params over their DEFAULTS, as load does
    folder = tempfile.mkdtemp(prefix="sieve-store-")
    st = store.Store(folder)
    st.probe()
    dec = Decoder(doc.video, cache_bytes=4 << 30)
    g = Graph(doc, dec, tools, memo_bytes=4 << 30, open_bake=lambda bk, c: st.open_bake(bk, c))
    mon = Monitor(g)
    length = min(g.count, ROWS or round(10 * g.fps))
    b.params.update({"from": "0", "to": str(length - 1)})
    chain = " -> ".join(n for n in walk_order(doc) if n not in g.chain)
    print(f"{doc.video}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows; rescale {rs.params}; "
          f"window {length} rows; store {folder}")
    print(f"frame chain {chain}; series {g.chain}")

    s, series = walk(g, length)
    report("live, cold", g, mon, s)
    count = series.get("count")
    if count is not None:
        sig = np.asarray(count["signal"], np.float64)
        print(f"   count: {sig.mean():.1f} blobs a row over {len(sig)} rows, {sig.sum():.0f} records")
    report("live, rewalk", g, mon, walk(g, length)[0])
    scale = rs.params["scale"]
    rs.params["scale"] = scale * 1.02
    g.sync()
    report("live, rewalk after a change on rescale", g, mon, walk(g, length)[0])
    rs.params["scale"] = scale
    g.sync()
    walk(g, length)

    s, bk = bake(g, st, os.path.basename(DOC))
    path = st.place(bk.key, ".mp4")
    print(f"\n== bake: {s:.1f} s for rows {bk.rows} every {bk.increment}, {os.path.getsize(path) / 2**20:.1f} MB on disk, "
          f"{bk.kind} {bk.shape} at quality {st.sidecar(bk.key).quality}")
    g.sync()
    report("baked, cold", g, mon, walk(g, length)[0])
    g.close()
    dec.close()


if __name__ == "__main__":
    main()
