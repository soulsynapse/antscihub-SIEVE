"""What video-tests/GoPro-stress-test-periods.json asks to be made, four signals a row of the crop
`region` serves, each gating a `period`, and how fast those same numbers can be made seven ways:

  player    walk._Walk over the document as bare.py drives it, the memo and the plate's cache
            holding bare.HOLD each
  window's  the same walk over twice the rows with the memo and the cache at Graph's and
            Decoder's own limits, which are what a PlayerWindow's worker walks the clip under; run
            last, since what it leaves of the process's memory slows the ways run after it
  bare      the tools' own run() and reduce's fold() in a loop, no graph, each node timed
  fused     the same arithmetic written once: one float frame, one difference, cv2 in numpy's place
  threads   `fused`, a row a task over a pool, the frames decoded first on this thread
  sums      `threads` folding the sum alone, which is all reduce's `mean` reads of a fold
  processes `fused` over the clip cut into stretches of rows, a process each decoding its own

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-21-the-stress-documents-walk-against-its-floor.py [rows] 2>NUL

`rows` is how many of the clip's rows `player`, `bare` and `fused` walk, the next three walking the clip whole.
Each way's signals are set against the player's over the rows both have, by the largest difference
and by the rows whose gate differs under the document's bands. Then the whole clip's results are
held as a run, the plan is asked for the periods, and that is timed. The document is Kendrick's and
gitignored, and the crop is the store's: the script needs both where his machine has them.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.bare import HOLD, _Told  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, kept  # noqa: E402
from sieve_player.heldwalks import gate_result, held_chain  # noqa: E402
from sieve_player.registry import cut_by, discover  # noqa: E402
from sieve_player.walk import _Walk  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "GoPro-stress-test-periods.json")
NODES = ("reduce", "reduce_2", "reduce_3", "reduce_4")     # changeenergy's, motion's, speed's and changeenergy_3's
THREADS = 4             # past which a pool of threads made the clip no sooner on the machine this was written on
PROCESSES = max(1, (os.cpu_count() or 2) // 2)
DET_EPS = 1e-6


class Shim:
    """What a frame tool's run() reads, with no graph behind it: `read(row, input)`."""

    def __init__(self, read, fps, count):
        self.read, self.fps, self.count = read, fps, count

    def __call__(self, row, input="in"):
        return self.read(row, input)


def player(doc, tools, n, hold=None):
    """The clip's first `n` rows walked with the memo and the cache holding `hold` bytes each, their own limits with None."""
    g = Graph(doc, Decoder(doc.video), tools) if hold is None else Graph(doc, Decoder(doc.video, cache_bytes=hold), tools, memo_bytes=hold)
    p = g.snapshot()
    t = time.perf_counter()
    bg = g.compute("background", 0)
    t_bg = time.perf_counter() - t
    ready = _Told()
    walk = _Walk(g, name="clip", every=g.count, progress=_Told(), ready=ready, refused=_Told(), failed=_Told(), tell_every=0.1, plan=p)
    walk.begin(0, n)
    t = time.perf_counter()
    while walk.i < walk.length:
        walk.turn()
        if walk.i == n // 2:
            half = time.perf_counter() - t
    took = time.perf_counter() - t, half
    facts = p.entries["region"].file[0], g.fps, g.count, {nid: p.entries[nid].band for nid in NODES}, {nid: dict(p.entries[nid].computed) for nid in p.entries}
    signals = {nid: ready.last[0][nid]["signal"] for nid in NODES}
    held = g.memo.bytes, g.memo.limit
    g.close()
    g.decoder.close()
    return took, t_bg, bg, signals, facts, held


def decoded(path, n):
    d = Decoder(path)
    d.output = "luma"
    out = np.empty((n, d.height, d.width), np.uint8)
    for r in range(n):
        out[r] = d.read(r)
    d.close()
    return out


def bare(tools, frames, bg, fps, count, params):
    """The tools' run() over `frames` with nothing held but the row before, and what each node took."""
    ce, mo, fl, sp, bs = (tools[k] for k in ("changeenergy", "motion", "flow", "speed", "bg-subtract"))
    fold = tools["reduce"].fold
    took = dict.fromkeys(("changeenergy", "motion", "flow", "speed", "bg-subtract", "changeenergy_3", "fold x4"), 0.0)
    folds = {nid: np.empty((len(frames), 4)) for nid in NODES}
    d_before = None

    def timed(name, f, *a):
        t = time.perf_counter()
        out = f(*a)
        took[name] += time.perf_counter() - t
        return out

    for r in range(len(frames)):
        region = Shim(lambda row, i: frames[row] if row >= 0 else None, fps, count)
        a = timed("changeenergy", ce.run, region, r, params["changeenergy"])
        b = timed("motion", mo.run, region, r, params["motion"])
        field = timed("flow", fl.run, region, r, params["flow"])
        c = timed("speed", sp.run, Shim(lambda row, i: field, fps, count), r, params["speed"])
        d = timed("bg-subtract", bs.run, Shim(lambda row, i: bg if i == "bg" else frames[row], fps, count), r, params["bg-subtract"])
        was = d_before
        e = timed("changeenergy_3", ce.run, Shim(lambda row, i: d if row == r else was, fps, count), r, params["changeenergy_3"])
        d_before = d
        t = time.perf_counter()
        for nid, plane in zip(NODES, (a, b, c, e)):
            folds[nid][r] = fold(plane)
        took["fold x4"] += time.perf_counter() - t
    return folds, took


def fused_row(frames, bg, r, fps, sigma, whole):
    """The four folds of row `r`, [sum, max, nonzero, size] each, or the sums alone unless `whole`."""
    size = frames[r].size

    def fold(plane):
        if not whole:
            return (cv2.sumElems(plane)[0], 0.0, 0.0, size)
        return (cv2.sumElems(plane)[0], cv2.minMaxLoc(plane)[1], cv2.countNonZero(plane), size)

    if r == 0:
        return [(0.0, 0.0, 0.0, size)] * 4
    f8, p8 = frames[r], frames[r - 1]
    f, p = f8.astype(np.float32), p8.astype(np.float32)
    it = f - p
    energy = cv2.GaussianBlur(it * it, (0, 0), sigma)
    moved = cv2.absdiff(f8, p8)
    ix = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=1, scale=0.5, borderType=cv2.BORDER_REPLICATE)
    iy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=1, scale=0.5, borderType=cv2.BORDER_REPLICATE)
    ix[:, 0] *= 2       # numpy.gradient's edges are one-sided and whole, a replicated border's halved
    ix[:, -1] *= 2
    iy[0] *= 2
    iy[-1] *= 2
    xx, yy, xy, xt, yt = (cv2.GaussianBlur(a * b, (0, 0), sigma) for a, b in ((ix, ix), (iy, iy), (ix, iy), (ix, it), (iy, it)))
    det = xx * yy - xy * xy
    inv = np.zeros_like(det)
    np.divide(1.0, det, out=inv, where=np.abs(det) > DET_EPS)
    speed = cv2.magnitude((yy * xt - xy * yt) * inv, (xx * yt - xy * xt) * inv) * np.float32(fps)
    dt = cv2.absdiff(f8, bg).astype(np.float32) - cv2.absdiff(p8, bg).astype(np.float32)
    energy_3 = cv2.GaussianBlur(dt * dt, (0, 0), sigma)
    return [fold(energy), fold(moved), fold(speed), fold(energy_3)]


def fused(frames, bg, fps, sigma, whole=True, pool=None):
    rows = range(len(frames))
    one = lambda r: fused_row(frames, bg, r, fps, sigma, whole)  # noqa: E731
    got = np.array(list(map(one, rows)) if pool is None else list(pool.map(one, rows, chunksize=64)), np.float64)
    return {nid: got[:, i] for i, nid in enumerate(NODES)}


def stretch(crop, first, end, bg, fps, sigma):
    """The folds of rows [first, end) of the file at `crop`, decoded here from the row before."""
    cv2.setNumThreads(1)
    decmod.QUIET = True
    d = Decoder(crop)
    d.output = "luma"
    lead = max(0, first - 1)
    frames = np.stack([d.read(r) for r in range(lead, end)])
    d.close()
    got = [fused_row(frames, bg, r - lead, fps, sigma, True) if r else [(0.0, 0.0, 0.0, frames[0].size)] * 4 for r in range(first, end)]
    return np.array(got, np.float64)


def warm(_):
    return os.getpid()


def against(name, signals, truth, bands):
    for nid in NODES:
        n = min(len(signals[nid]), len(truth[nid]))
        a, b = np.asarray(signals[nid][:n], np.float64), np.asarray(truth[nid][:n], np.float64)
        flips = int((kept(signals[nid][:n], bands[nid]) != kept(truth[nid][:n], bands[nid])).sum())
        print(f"    {name} {nid}: over {n} rows the largest difference {np.abs(a - b).max():.3g} of a signal near {np.abs(b).mean():.3g}; gate differs at {flips} rows")


if __name__ == "__main__":
    decmod.QUIET = True
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    mean = lambda folds: {nid: (v[:, 0] / v[:, 3]).astype(np.float32) for nid, v in folds.items()}  # noqa: E731

    (took, _), t_bg, bg, truth, (crop, fps, count, bands, params), held_small = player(doc, tools, n, HOLD)
    sigma = params["changeenergy"]["sigma"]
    print(f"the crop {os.path.basename(crop)}, {count} rows at {fps:.2f} fps; player, bare and fused walk {n} of them")
    print(f"background, once: {1000 * t_bg:.0f} ms")
    line = lambda name, s, rows, note="": print(f"{name:9s} {1000 * s / rows:6.3f} ms a row, {rows / s:7.0f} rows/s, the clip in {count * s / rows:5.1f} s{note}")  # noqa: E731
    line("player", took, n, f"; the memo held {held_small[0] >> 20} MB of the {held_small[1] >> 20} it may")

    t = time.perf_counter()
    frames = decoded(crop, count)
    t_decode = time.perf_counter() - t
    print(f"decode alone, the clip whole: {t_decode:.2f} s, {1000 * t_decode / count:.3f} ms a row, {frames.nbytes >> 20} MB of luma")

    t = time.perf_counter()
    folds, each = bare(tools, frames[:n], bg, fps, count, params)
    took = time.perf_counter() - t
    line("bare", took, n, " without decode")
    for name, s in sorted(each.items(), key=lambda kv: -kv[1]):
        print(f"    {name:15s} {1000 * s / n:6.3f} ms a row, {100 * s / took:4.1f}%")
    against("bare", mean(folds), truth, bands)

    t = time.perf_counter()
    one = fused(frames[:n], bg, fps, sigma)
    line("fused", time.perf_counter() - t, n, " without decode")
    against("fused", mean(one), truth, bands)

    cv2.setNumThreads(1)        # the pool is the parallelism: OpenCV's own threads under it only contend
    with ThreadPoolExecutor(THREADS) as pool:
        t = time.perf_counter()
        whole = fused(frames, bg, fps, sigma, pool=pool)
        took = time.perf_counter() - t
        line("threads", took, count, f" without decode, {THREADS} threads; with it {took + t_decode:.1f} s")
        t = time.perf_counter()
        sums = fused(frames, bg, fps, sigma, whole=False, pool=pool)
        took = time.perf_counter() - t
        line("sums", took, count, f" without decode, {THREADS} threads; with it {took + t_decode:.1f} s")
    with ProcessPoolExecutor(PROCESSES) as pool:
        t = time.perf_counter()
        len(set(pool.map(warm, range(PROCESSES * 4))))
        t_up = time.perf_counter() - t
        edges = np.linspace(0, count, PROCESSES * 2 + 1).astype(int)
        t = time.perf_counter()
        parts = list(pool.map(stretch, *zip(*[(crop, int(a), int(b), bg, fps, sigma) for a, b in zip(edges, edges[1:])])))
        took = time.perf_counter() - t
        line("processes", took, count, f" with decode, {PROCESSES} processes, which took {t_up:.1f} s to start")
    apart = np.concatenate(parts)
    signals = mean(whole)
    against("processes", mean({nid: apart[:, i] for i, nid in enumerate(NODES)}), signals, bands)
    against("threads", signals, truth, bands)
    against("sums", mean(sums), signals, bands)

    runs = held.Runs(1 << 40, lambda nid, r: sum(getattr(v, "nbytes", 0) for v in r.values()))
    dec = Decoder(doc.video)
    dec.ends_at(count)

    def cut_result(nid, key, within):
        by = cut_by(tools.get(doc.node(nid).tool))
        w = by and doc.source(nid, by[0])
        return gate_result(runs, w.src, key, within, dec.count) if w else None

    g = Graph(doc, dec, tools, cut_result=cut_result)
    p = g.snapshot()
    results = {nid: {"signal": s, "gate": kept(s, bands[nid]), "key": p.entries[nid].key, "code": None} for nid, s in signals.items()}
    chain = held_chain(p, p.chain)
    runs.hold(0, count, results, chain, None, worth=chain)
    t = time.perf_counter()
    g.sync()
    t_sync = time.perf_counter() - t
    p = g.snapshot()
    print(f"the periods, of the whole clip's gates held as a run: one sync {1000 * t_sync:.0f} ms; timed walks {len(p.timed)}")
    for nid, e in p.entries.items():
        if e.tool is tools["period"]:
            lens = [b - a for a, b in (c.extent.rows for c in e.cuts)]
            print(f"    {nid}: {len(lens)} periods over {sum(lens)} rows, {sum(x == 1 for x in lens)} of one row, the median {int(np.median(lens))}, the longest {max(lens)}")
    g.close()
    dec.close()

    (took, half), _, _, same, _, held_big = player(D.load(DOC, tools), tools, 2 * n)
    line("window's", half, n, f" over its first {n} rows")
    line("window's", took - half, n, f" over its next {n}; the memo held {held_big[0] >> 20} MB of the {held_big[1] >> 20} it may")
    against("window's", same, truth, bands)
