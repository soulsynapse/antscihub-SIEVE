"""Experiment behind docs/findings/2026-11-12-bg-subtract-against-tgrabs.md: how fast
video-tests/bg-subtract-compare.json parses its clip, beside TGrabs 1.1.9 converting the same file.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-bg-subtract-against-tgrabs.py [word ...] 2>NUL

The words run in order. `bare` calls Graph.walk_row at every row on one thread with nothing attached,
`probed` with a ledger attached and `threaded` on a second thread; `clip` is the worker's clip walk under
a ledger, with each node's ms a row; `tgrabs` runs the conda env track119's tgrabs with the document's
threshold, size filter and sample count, writing under the system's temp folder. A number sets OpenCV's
threads, `nogc` turns the collector off, and `P`, `E` and `any` hold the process to those cores, for the
runs after it. The Session is the cold-window experiment's.
"""
import gc
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cold", os.path.join(HERE, "2026-11-12-a-cold-window-and-the-clip.py"))
cold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cold)

import cv2  # noqa: E402
import psutil  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.machine import Machine  # noqa: E402
from sieve_player.registry import discover  # noqa: E402

DOC = os.path.join(cold.ROOT, "video-tests", "bg-subtract-compare.json")
ENV = "track119"
CORES = {"P": list(range(16)), "E": list(range(16, 32)), "any": list(range(32))}   # an i9-14900KF's: 8 performance cores of two threads, then 16 efficiency cores


def cores(m, child=""):
    mine, rest, n = m.read()["cores"]
    m.close()
    return f"cores busy over it: this process {mine:.1f}, everything else{child} {rest:.1f}, of {n}"


def graph():
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(cold.ROOT, "tools")) if e.ok}
    st = store.current()
    doc = D.load(DOC, tools)
    return doc, Graph(doc, Decoder(doc.video), tools, open_bake=lambda bk, c: st.open_bake(bk, c))


def bare(probed=False, threaded=False):
    doc, g = graph()
    if probed:
        g.on_event = Ledger().event
    g.sync()
    if threaded:
        t = threading.Thread(target=_bare, args=(doc, g, "on a second thread, the first asleep in join"))
        t.start()
        t.join()
    else:
        _bare(doc, g, "a ledger attached" if probed else "nothing attached")


def _bare(doc, g, label):
    n = g.count
    m = Machine()
    t0 = time.perf_counter()
    blobs = [len(g.walk_row(0))]
    t1 = time.perf_counter()
    for r in range(1, n):
        blobs.append(len(g.walk_row(r)))
    t2 = time.perf_counter()
    print(f"\n== bare, {label}, {os.path.basename(doc.video)}: {g.decoder.width}x{g.decoder.height}, {n} rows at {g.fps:.2f} fps")
    print(f"   the first row, the background in it: {(t1 - t0) * 1000:.0f} ms")
    print(f"   the rest: {t2 - t1:.1f} s, {(n - 1) / (t2 - t1):.0f} rows a second, {(t2 - t1) / (n - 1) * 1000:.3f} ms a row; "
          f"whole {t2 - t0:.1f} s, {n / (t2 - t0):.0f} rows a second")
    print(f"   blobs a row: {sum(blobs) / n:.2f}, {max(blobs)} at most; decodes {g.decoder.decodes}, seeks {g.decoder.seeks}")
    print(f"   {cores(m)}; resident {psutil.Process().memory_info().rss >> 20} MB, gc's collections {[s['collections'] for s in gc.get_stats()]}, "
          f"objects it tracks {len(gc.get_objects())}")
    g.close()
    g.decoder.close()


def clip():
    doc, g = graph()
    s = cold.Session(g, 30)
    m = Machine()
    view, wall = s.clip()
    busy = cores(m)
    w = view.walks[-1]
    n = w.done
    print(f"\n== the worker's clip walk under a ledger: {n} rows in {wall:.1f} s, {n / wall:.0f} rows a second, {wall / n * 1000:.3f} ms a row")
    print(f"   {'node':14} {'kind':8} {'demand':8} {'count':>7} {'ms':>9} {'ms a row':>9}")
    total = 0.0
    for nid, x in w.nodes.items():
        for (kind, demand, _), r in sorted(x.runs.items()):
            total += r[1]
            print(f"   {nid:14} {kind:8} {demand:8} {r[0]:>7} {r[1]:>9.0f} {r[1] / n:>9.4f}")
    print(f"   the spans sum to {total / 1000:.1f} s of the {wall:.1f}; no span covers {(wall * 1000 - total) / n:.4f} ms a row")
    print(f"   {busy}")
    s.close()


def tgrabs():
    doc, g = graph()
    video, width = os.path.abspath(doc.video), g.decoder.width
    p = {n.id: n.params for n in doc.nodes}
    g.close()
    g.decoder.close()
    out = tempfile.mkdtemp(prefix="sieve-tgrabs-")
    cmd = ["conda", "run", "-n", ENV, "tgrabs", "-i", video, "-o", "bgcompare", "-d", out, "-nowindow", "-reset_average",
           "-threshold", str(p["threshold"]["thresh"]), "-average_samples", str(p["background"]["samples"]),
           "-averaging_method", "mode", "-meta_real_width", str(width), "-blob_size_range", f"[{p['blobs']['min_area']},500000]"]
    m = Machine()
    t = time.perf_counter()
    log = subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout
    wall = time.perf_counter() - t
    busy = cores(m, ", tgrabs in it,")
    rates = [float(m) for m in re.findall(r"@ ([\d.]+)fps", log)]
    stamp = lambda pat: next((ln[1:9] for ln in log.splitlines() if pat in ln), "?")  # noqa: E731
    print(f"\n== tgrabs under {ENV}: {wall:.1f} s for the process; the queue made at {stamp('Creating queue')} and the program ending at "
          f"{stamp('Ending the program')}")
    print(f"   its own rate, a line a second: {min(rates):.0f} to {max(rates):.0f} fps, median {sorted(rates)[len(rates) // 2]:.0f}")
    print(f"   {os.path.getsize(os.path.join(out, 'bgcompare.pv')) / 2**20:.1f} MB written to {out}")
    print(f"   {busy}")


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    for name in sys.argv[1:] or ["bare", "clip", "tgrabs"]:
        if name in CORES:
            psutil.Process().cpu_affinity(CORES[name])
            print(f"\n-- held to the {name} cores, logical {CORES[name][0]} to {CORES[name][-1]}; a child inherits it")
            continue
        if name == "nogc":
            gc.disable()
            print("\n-- gc.disable()")
            continue
        if name.isdigit():
            cv2.setNumThreads(int(name))
            print(f"\n-- cv2.setNumThreads({name}); cv2 now reports {cv2.getNumThreads()}")
            continue
        {"bare": bare, "probed": lambda: bare(probed=True), "threaded": lambda: bare(threaded=True),
         "clip": clip, "tgrabs": tgrabs}[name]()
