"""Experiment behind docs/findings/2026-11-13-sieve-against-the-trex-port.md: where a row's time goes in
video-tests/bg-subtract-compare.json beside the same steps done as the TRex 1.1.9 port does them.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-13-sieve-against-the-trex-port.py [word ...] 2>NUL

`stages` times each step alone on ROWS held rows, one OpenCV thread: the decoder's luma read, the
difference and threshold, blobs.find and runs.find, and the port's labeling, which crops each kept
component and cuts only the crop into runs. `gc` walks the document's first GC_ROWS rows twice in one
process and times the collector through gc.callbacks. `track` links ROWS rows of tables. `walk` is
Graph.walk_row over WALK_ROWS rows with nothing attached: the document as it is, then at the port's
threshold and least area, then with runs in place of blobs, then with the memo and the decoder cache
held small so a plane is dropped a few rows after it is made, then with tools/segment.py in place of
the three nodes; `same` holds segment's tables to theirs, and `ahead` reads the Decoder on a thread
of its own beside segment's work. `clip4` is the worker's clip walk of the whole clip on CASES[4], a
word alone in a process, and `clip4-inline` the same with no reading thread; `frames` holds what the
reading thread decodes to a decoder reading in line. `profile` is cProfile over the third of
those. `pool` runs difference, threshold and each labeling over POOL_ROWS held rows through a thread pool
of 1, 2, 4 and 8. `pipe` reads PIPE_ROWS rows through the Decoder on one thread with the tools on others.
`hold` is the walk of `walk`'s third case over ROWS rows with the memo and the decoder cache at each of
HOLDS, and at 16 MB with a ledger attached. `big` is that walk on the clips of BIG, larger frames, with
each store at a few rows of planes, at 64 and at a thousand. `churn` has no graph in it: arrays of each
plane's size made and kept, freed, made and dropped, made into a ring of eight, and one written again;
nor has `reuse`, cv2's read into new arrays against into held ones.
Every word is row-limited; run the words a few at a time to stay under a minute.
"""
import gc
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("tg", os.path.join(HERE, "2026-11-12-bg-subtract-against-tgrabs.py"))
tg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tg)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tools import blobs, runs, track  # noqa: E402

ROWS, GC_ROWS, WALK_ROWS, POOL_ROWS, PIPE_ROWS, BATCH, SAME_ROWS = 6000, 12000, 8000, 4000, 12000, 32, 2000
THRESH, MIN_AREA = 60, 137          # the port's run of this clip


def port_label(m, g):
    """The port's frame_record without the packing: label, then runs and pixels inside each kept box."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8, ltype=cv2.CV_16U)
    out = []
    if n > 1:
        area = stats[1:, cv2.CC_STAT_AREA]
        for i in np.flatnonzero(area >= MIN_AREA) + 1:
            x, y, w, h = stats[i, :4].tolist()
            inside = np.zeros((h, w + 2), np.bool_)
            inside[:, 1:-1] = labels[y:y + h, x:x + w] == i
            flat = inside.ravel()
            edge = np.flatnonzero(flat[1:] != flat[:-1])
            out.append((edge, g[y:y + h, x:x + w][inside[:, 1:-1]]))
    return out


def per_row(fn, items, repeat=3):
    best = 1e9
    for _ in range(repeat):
        t = time.perf_counter()
        for it in items:
            fn(*it)
        best = min(best, time.perf_counter() - t)
    return best / len(items) * 1000


def stages():
    doc, g = tg.graph()
    d = g.decoder
    t = time.perf_counter()
    luma = [d.read(r) for r in range(ROWS)]
    t_dec = (time.perf_counter() - t) / ROWS * 1000
    bg = g.compute("background", 0)
    g.close()
    d.close()
    cap = cv2.VideoCapture(doc.video)
    t = time.perf_counter()
    for _ in range(ROWS):
        cv2.extractChannel(cap.read()[1], 1)
    t_bgr = (time.perf_counter() - t) / ROWS * 1000
    cap.release()
    diff = [cv2.absdiff(f, bg) for f in luma]
    mask = [cv2.threshold(x, THRESH, 255, cv2.THRESH_BINARY)[1] for x in diff]
    print(f"\n== stages, ms a row over {ROWS} rows, least of three, one OpenCV thread; threshold {THRESH}, min_area {MIN_AREA}")
    print(f"   decode: the Decoder's luma read {t_dec:.3f}; cv2 read to BGR and one channel, as the port {t_bgr:.3f}")
    print(f"   absdiff {per_row(cv2.absdiff, [(f, bg) for f in luma]):.3f}; "
          f"threshold {per_row(lambda x: cv2.threshold(x, THRESH, 255, cv2.THRESH_BINARY), [(x,) for x in diff]):.3f}")
    print(f"   blobs.find {per_row(lambda m: blobs.find(m, MIN_AREA), [(m,) for m in mask]):.3f}; "
          f"runs.find {per_row(lambda m: runs.find(m, MIN_AREA), [(m,) for m in mask]):.3f}; "
          f"the port's label and crop {per_row(port_label, list(zip(mask, luma))):.3f}; "
          f"connectedComponentsWithStats alone {per_row(lambda m: cv2.connectedComponentsWithStats(m, connectivity=8, ltype=cv2.CV_16U), [(m,) for m in mask]):.3f}")
    kept = [len(blobs.find(m, MIN_AREA)) for m in mask[:1000]]
    print(f"   records a row {sum(kept) / len(kept):.2f}")
    return [blobs.find(m, MIN_AREA) for m in mask]


def collector():
    spent, began = {0: 0.0, 1: 0.0, 2: 0.0}, [0.0]

    def cb(phase, info):
        if phase == "start":
            began[0] = time.perf_counter()
        else:
            spent[info["generation"]] += time.perf_counter() - began[0]

    gc.callbacks.append(cb)
    print(f"\n== two walks of {GC_ROWS} rows in one process, the collector timed")
    for k in (1, 2):
        for s in spent:
            spent[s] = 0.0
        n0 = [s["collections"] for s in gc.get_stats()]
        doc, g = tg.graph()
        t = time.perf_counter()
        for r in range(GC_ROWS):
            g.walk_row(r)
        wall = time.perf_counter() - t
        n1 = [s["collections"] for s in gc.get_stats()]
        print(f"   walk {k}: {wall:.1f} s, {GC_ROWS / wall:.0f} rows a second; in the collector {sum(spent.values()):.1f} s, "
              f"by generation {[round(v, 2) for v in spent.values()]} over {[b - a for a, b in zip(n0, n1)]} collections; "
              f"memo {g.memo.bytes >> 20} MB, objects tracked {len(gc.get_objects())}")
        g.close()
        g.decoder.close()
    gc.callbacks.remove(cb)


def tracking(tables):
    t = time.perf_counter()
    track.link(tables, 20.0, 30, 3, 0.1)
    wall = time.perf_counter() - t
    print(f"\n== track.link over {len(tables)} rows of tables: {wall:.2f} s, {wall / len(tables) * 1000:.3f} ms a row, "
          f"{len(tables) / wall:.0f} rows a second")


def graph(thresh=None, min_area=None, tool=None, outline=None, hold=4 << 30, video=None, fused=False):
    from sieve_player import decoder as decmod, document as D, store
    from sieve_player.decoder import Decoder
    from sieve_player.graph import Graph
    from sieve_player.registry import discover
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(tg.cold.ROOT, "tools")) if e.ok}
    if tool is not None:
        tools["blobs"] = tool
    doc = D.load(tg.DOC, tools)
    if video is not None:
        doc.video = os.path.join(tg.cold.ROOT, "video-tests", video)
    for n in doc.nodes:
        if n.id == "threshold" and thresh is not None:
            n.params["thresh"] = thresh
        if n.id == "blobs" and min_area is not None:
            n.params["min_area"] = min_area
        if n.id == "blobs" and outline is not None:
            n.params["outline"] = outline
    if fused:       # segment in place of bg-subtract, threshold and blobs
        for nid in ("bg-subtract", "threshold", "blobs"):
            doc.remove_node(nid)
        n = doc.add_node("segment", params={"mode": "absolute", "thresh": thresh or 31, "min_area": min_area or 50,
                                             "max_area": 0, "outline": "box"})
        doc.connect("video", n.id)
        doc.connect("background", n.id, "bg")
        doc.display = n.id
    st = store.current()
    return Graph(doc, Decoder(doc.video, cache_bytes=hold), tools, memo_bytes=hold, open_bake=lambda bk, c: st.open_bake(bk, c))


CASES = (("the document as it is", {}),
         (f"threshold {THRESH}, min_area {MIN_AREA}", dict(thresh=THRESH, min_area=MIN_AREA)),
         ("the same, runs in place of blobs", dict(thresh=THRESH, min_area=MIN_AREA, tool=runs)),
         ("the same, the memo and the decoder cache held to 16 MB each", dict(thresh=THRESH, min_area=MIN_AREA, tool=runs, hold=16 << 20)),
         ("segment in place of bg-subtract, threshold and runs", dict(thresh=THRESH, min_area=MIN_AREA, fused=True)))


def walk():
    print(f"\n== Graph.walk_row over {WALK_ROWS} rows, nothing attached, a fresh graph each")
    for label, kw in CASES:
        g = graph(**kw)
        g.walk_row(0)
        g.decoder.empty()        # the background's samples are read at row 0 and on a short clip that caches every frame
        t = time.perf_counter()
        n = sum(len(g.walk_row(r)) for r in range(1, WALK_ROWS))
        wall = time.perf_counter() - t
        print(f"   {label}: {wall / (WALK_ROWS - 1) * 1000:.3f} ms a row, {(WALK_ROWS - 1) / wall:.0f} rows a second, "
              f"{n / (WALK_ROWS - 1):.2f} records a row")
        g.close()
        g.decoder.close()
        del g
        gc.collect()


def profile():
    import cProfile
    import pstats
    g = graph(**CASES[2][1])
    g.walk_row(0)
    g.decoder.empty()        # the background's samples are read at row 0 and on a short clip that caches every frame
    pr = cProfile.Profile()
    pr.enable()
    for r in range(1, ROWS):
        g.walk_row(r)
    pr.disable()
    print(f"\n== cProfile of {CASES[2][0]}, {ROWS} rows, by own time")
    pstats.Stats(pr).sort_stats("tottime").print_stats(18)


def pool():
    from concurrent.futures import ThreadPoolExecutor
    g = graph()
    luma = [g.decoder.read(r) for r in range(POOL_ROWS)]
    bg = g.compute("background", 0)
    g.close()
    g.decoder.close()
    labelings = {"blobs.find": lambda m, f: blobs.find(m, MIN_AREA), "runs.find": lambda m, f: runs.find(m, MIN_AREA),
                 "the port's label and crop": port_label}
    print(f"\n== difference, threshold and a labeling over {POOL_ROWS} held rows, rows a second at 1, 2, 4 and 8 pool threads")
    for name, fn in labelings.items():
        rates = []
        for workers in (1, 2, 4, 8):
            with ThreadPoolExecutor(workers) as ex:
                t = time.perf_counter()
                list(ex.map(lambda f: fn(cv2.threshold(cv2.absdiff(f, bg), THRESH, 255, cv2.THRESH_BINARY)[1], f), luma))
                rates.append(POOL_ROWS / (time.perf_counter() - t))
        print(f"   {name}: " + ", ".join(f"{v:.0f}" for v in rates))


def pipe():
    """The Decoder read on one thread and difference, threshold and a labeling on others, frames handed
    over BATCH at a time and the tables landing by row; nothing is kept but the tables."""
    import queue
    import threading
    from tools.bg_subtract import difference
    g0 = graph()
    bg = g0.compute("background", 0)
    g0.close()
    g0.decoder.close()
    labelings = (("runs.find", lambda m, f: runs.find(m, MIN_AREA), (0, 1)),
                 ("blobs.find", lambda m, f: blobs.find(m, MIN_AREA), (1, 2)),
                 ("the port's label and crop", port_label, (1, 2, 4)))
    print(f"\n== the Decoder on its own thread, the tools on others, {PIPE_ROWS} rows, {BATCH} frames a handover; rows a second")
    for name, fn, counts in labelings:
        rates = []
        for workers in counts:
            g = graph(hold=16 << 20)
            d = g.decoder
            out = [None] * PIPE_ROWS
            todo = queue.Queue(maxsize=8)

            def rows(start, frames):
                for i, f in enumerate(frames, start):
                    out[i] = fn(cv2.threshold(difference(f, bg, "absolute"), THRESH, 255, cv2.THRESH_BINARY)[1], f)

            def work():
                while (item := todo.get()) is not None:
                    rows(*item)

            pool = [threading.Thread(target=work) for _ in range(workers)]
            for t in pool:
                t.start()
            t0 = time.perf_counter()
            for start in range(0, PIPE_ROWS, BATCH):
                frames = [d.read(r) for r in range(start, min(start + BATCH, PIPE_ROWS))]
                if workers:
                    todo.put((start, frames))
                else:
                    rows(start, frames)
            for _ in pool:
                todo.put(None)
            for t in pool:
                t.join()
            rates.append(f"{workers} tool thread{'s' * (workers != 1)} {PIPE_ROWS / (time.perf_counter() - t0):.0f}")
            assert all(o is not None for o in out)
            g.close()
            d.close()
        print(f"   {name}: " + ", ".join(rates))


HOLDS = (1, 4, 16, 256)     # MB


def hold():
    from sieve_player.ledger import Ledger
    print(f"\n== Graph.walk_row over {ROWS} rows, {CASES[2][0]}, by what the memo and the decoder cache may each hold")
    for mb, ledger in [(mb, False) for mb in HOLDS] + [(16, True)]:
        g = graph(**CASES[2][1], hold=mb << 20)
        if ledger:
            g.on_event = Ledger().event
            g.sync()
        g.walk_row(0)
        g.decoder.empty()        # the background's samples are read at row 0 and on a short clip that caches every frame
        t = time.perf_counter()
        for r in range(1, ROWS):
            g.walk_row(r)
        wall = time.perf_counter() - t
        print(f"   {mb} MB{', a ledger attached' if ledger else ''}: {wall / (ROWS - 1) * 1000:.3f} ms a row, "
              f"{(ROWS - 1) / wall:.0f} rows a second")
        g.close()
        g.decoder.close()


BIG = (("rep3_intermittent_crop.MP4", 3000), ("00000_168-178.mp4", 590))      # the same chain on larger frames, and the rows walked
BIG_HOLDS = (8, 64, 1024)   # in rows of the chain's four planes, each store: a few rows, a store that fills early in the walk, one that never does


def big():
    for video, rows in BIG:
        g = graph(**CASES[2][1], video=video)
        w, h = g.decoder.width, g.decoder.height
        g.close()
        g.decoder.close()
        print(f"\n== {video}, {w} by {h}, a plane {w * h >> 10} KB: Graph.walk_row over {rows} rows, two runs of each")
        for held in BIG_HOLDS * 2:
            limit = held * 4 * w * h
            g = graph(**CASES[2][1], video=video, hold=limit)
            n = min(rows, g.count)
            g.walk_row(0)
            g.decoder.empty()        # the background's samples are read at row 0 and on a short clip that caches every frame
            t = time.perf_counter()
            for r in range(1, n):
                g.walk_row(r)
            wall = time.perf_counter() - t
            print(f"   each store at {held} rows of planes, {limit >> 20} MB: {wall / (n - 1) * 1000:.3f} ms a row, "
                  f"{(n - 1) / wall:.0f} rows a second; memo discards {g.memo.evictions}")
            g.close()
            g.decoder.close()


def ahead():
    """The Decoder read by one thread into a bounded queue and segment.regions on the calling thread, against
    both in line, at three GIL switch intervals; no graph."""
    import queue
    import threading
    from tools import segment
    g0 = graph()
    bg = g0.compute("background", 0)
    g0.close()
    g0.decoder.close()
    was = sys.getswitchinterval()
    print(f"\n== Decoder.read and segment.regions over {PIPE_ROWS} rows, rows a second")
    for interval, own in ((0.005, False), (0.005, True), (0.0005, True), (0.00005, True), (0.005, False), (0.0005, True)):
        sys.setswitchinterval(interval)
        g = graph(hold=16 << 20)
        d = g.decoder
        todo = queue.Queue(maxsize=64)

        def read():
            for r in range(PIPE_ROWS):
                todo.put(d.read(r))
            todo.put(None)

        t = time.perf_counter()
        if own:
            reader = threading.Thread(target=read)
            reader.start()
            while (f := todo.get()) is not None:
                segment.regions(f, bg, "absolute", THRESH, MIN_AREA)
            reader.join()
        else:
            for r in range(PIPE_ROWS):
                segment.regions(d.read(r), bg, "absolute", THRESH, MIN_AREA)
        print(f"   switch interval {interval * 1000:g} ms, the decode {'on its own thread' if own else 'in line'}: "
              f"{PIPE_ROWS / (time.perf_counter() - t):.0f}")
        g.close()
        d.close()
    sys.setswitchinterval(was)


def clip(case, inline):
    """The worker's clip walk of the whole clip under a ledger, as the 2026-11-12 experiment runs it, on
    CASES[case]; `inline` has the decoder start no reading thread."""
    from sieve_player import decoder
    if inline:
        decoder.AHEAD_ROWS = 0
    print(f"\n## {CASES[case][0]}, the decode {'in line' if inline else 'read ahead'}")

    def made():
        g = graph(**CASES[case][1])
        return g.doc, g

    tg.graph = made
    tg.clip()


def frames():
    """Rows read with the reading thread on against a second Decoder reading in line, some reads out of
    step, the cache large and at 1 MB; and the counters after."""
    import zlib
    from sieve_player import decoder
    decoder.QUIET = True
    video = os.path.join(tg.cold.ROOT, "video-tests", "03c2012ed6e61417.mp4")
    for limit in (4 << 30, 1 << 20):
        a, b = decoder.Decoder(video, limit), decoder.Decoder(video, limit)
        a.output = b.output = "gray"
        told = []
        a.on_evict = lambda r, n: told.append(r)
        a.ahead(0, ROWS)
        apart = 0
        for r in range(ROWS):
            for q in [r] + ([r - 1] if r % 7 == 3 else []) + ([r + 3000] if r % 1000 == 500 else []):
                apart += zlib.crc32(a.read(q)) != zlib.crc32(b.read(q))
        a.rest()
        print(f"   cache {limit >> 20} MB: {apart} frames apart; reads {a.reads}, decodes {a.decodes}, the thread's "
              f"{a.ahead_decodes}, hits {a.cache_hits}, seeks {a.seeks} and the thread's {a.ahead_seeks}; in line "
              f"decodes {b.decodes}, hits {b.cache_hits}, seeks {b.seeks}; discards {a.evictions}, told {len(told)}")
        a.close()
        b.close()


def same():
    """Whether segment's tables are the three nodes' with runs, row for row."""
    a, b = graph(**CASES[2][1]), graph(**CASES[4][1])
    rows = range(0, a.count, max(1, a.count // SAME_ROWS))
    apart = [r for r in rows if not (lambda p, q: p.dtype == q.dtype and len(p) == len(q) and all(
        np.array_equal(p[n], q[n], equal_nan=True) if n != "runs" else all(np.array_equal(u, v) for u, v in zip(p[n], q[n]))
        for n in p.dtype.names))(a.walk_row(r), b.walk_row(r))]
    print(f"\n== segment against bg-subtract, threshold and runs over {len(rows)} rows spread over the clip: "
          f"{len(apart)} rows apart" + (f", the first {apart[0]}" if apart else ""))
    for g in (a, b):
        g.close()
        g.decoder.close()


def churn():
    print("\n== what an array of a plane's size costs, us each")
    for kb in (71, 205, 480, 600, 2025):
        n = kb << 10
        reps = max(200, (400 << 20) // n)
        t = time.perf_counter()
        held = [np.ones(n, np.uint8) for _ in range(reps)]
        keep = (time.perf_counter() - t) / reps * 1e6
        t = time.perf_counter()
        del held
        freed = (time.perf_counter() - t) / reps * 1e6
        t = time.perf_counter()
        for _ in range(reps):
            np.ones(n, np.uint8)
        dropped = (time.perf_counter() - t) / reps * 1e6
        ring = [np.ones(n, np.uint8) for _ in range(8)]
        t = time.perf_counter()
        for i in range(reps):
            ring[i % 8] = np.ones(n, np.uint8)
        ringed = (time.perf_counter() - t) / reps * 1e6
        buf = np.empty(n, np.uint8)
        t = time.perf_counter()
        for _ in range(reps):
            buf.fill(1)
        again = (time.perf_counter() - t) / reps * 1e6
        print(f"   {kb} KB: made and kept {keep:.0f}; freed {freed:.0f}; made and dropped at once {dropped:.0f}; "
              f"made into a ring of 8 {ringed:.0f}; one buffer written again {again:.0f}")


def reuse():
    """cv2's read into a new array each row against into the arrays of a ring of 32, the luma plane and BGR."""
    print("\n== VideoCapture.read into new arrays and into a ring of 32 held ones, ms a row")
    for video, rows in (("00000_168-178.mp4", 560), ("03c2012ed6e61417.mp4", ROWS)):
        for luma in (True, False):
            took = []
            for held in (False, True, False, True):
                cap = cv2.VideoCapture(os.path.join(tg.cold.ROOT, "video-tests", video), cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_CONVERT_RGB, 0 if luma else 1)
                ring = [cap.read()[1]] + [None] * 31
                t = time.perf_counter()
                for i in range(1, rows):
                    buf = ring[i % 32] if held else None
                    ring[i % 32] = (cap.read() if buf is None else cap.read(buf))[1]
                took.append((time.perf_counter() - t) / (rows - 1) * 1000)
                cap.release()
            print(f"   {video}, {'luma' if luma else 'BGR'}, {ring[0].nbytes >> 10} KB: new {took[0]:.3f} and {took[2]:.3f}; "
                  f"the ring's {took[1]:.3f} and {took[3]:.3f}")


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    cv2.setNumThreads(1)
    words = sys.argv[1:] or ["stages", "track", "gc"]
    for w in words:
        if w.startswith("clip"):
            clip(int(w[4]), w.endswith("inline"))
    if "frames" in words:
        frames()
    if "ahead" in words:
        ahead()
    if "same" in words:
        same()
    if "churn" in words:
        churn()
    if "reuse" in words:
        reuse()
    tables = stages() if "stages" in words or "track" in words else None
    if "track" in words:
        tracking(tables)
    if "walk" in words:
        walk()
    if "profile" in words:
        profile()
    if "big" in words:
        big()
    if "hold" in words:
        hold()
    if "pipe" in words:
        pipe()
    if "pool" in words:
        pool()
    if "gc" in words:
        collector()
