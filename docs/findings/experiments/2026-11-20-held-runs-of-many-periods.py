"""What `held.Runs` and `held.File` do with a run a period where they hold a run a walk today.
The one run of video-tests/purb-settings.json.series, the clip's, is read as it lies. Its signals
are thresholded at three of their own quantiles to count the periods a band would make of them.
The run is then cut into N runs of equal length, one a period, and each of Runs' loops and File's
writes is timed at N; the limit is set to half of what they take, and a run of the whole clip is
held before and after them. No player and no window.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-20-held-runs-of-many-periods.py"""
import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import held  # noqa: E402

SERIES = "video-tests/purb-settings.json.series"
COUNTS = (100, 300, 1000, 3000)
BUDGET = 45.0       # s: no count is begun past it
BEGAN = time.perf_counter()


def ms(f, *a):
    t = time.perf_counter()
    out = f(*a)
    return out, (time.perf_counter() - t) * 1e3


def periods_of(signal, lo):
    """(first, end) of each run of rows where `signal` is at or over `lo`."""
    kept = np.asarray(signal, np.float64) >= lo
    d = np.diff(np.r_[0, kept.astype(np.int8), 0])
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def what_a_band_makes(clip):
    print(f"periods a band at a quantile of each signal would make over {clip.rows} rows")
    print("signal   quantile  periods  rows kept  shortest  median  longest  of one row")
    for nid in ("count", "travel", "smooth"):
        signal = clip.results[nid]["signal"]
        for q in (0.5, 0.75, 0.9):
            lo = float(np.quantile(np.asarray(signal, np.float64), q))
            ps = periods_of(signal, lo)
            lengths = np.array([b - a for a, b in ps]) if ps else np.zeros(1, int)
            print(f"{nid:8s} {q:8.2f} {len(ps):8d} {int(lengths.sum()):10d} {int(lengths.min()):9d} "
                  f"{float(np.median(lengths)):7.0f} {int(lengths.max()):8d} {int((lengths == 1).sum()):11d}")


def cut(clip, n):
    """`clip` as n runs of equal length, in row order, each sized as its share of the clip's."""
    edges = np.linspace(0, clip.rows, n + 1).round().astype(int).tolist()
    return [(a, b - a, {nid: held.rows_of(r, clip.rows, a, b - a) for nid, r in clip.results.items()})
            for a, b in zip(edges[:-1], edges[1:]) if b > a]


def at(clip, n, chain, size_of):
    pieces = cut(clip, n)
    runs = held.Runs(1 << 40, size_of)
    t = time.perf_counter()
    for start, rows, results in pieces[:-1]:
        runs.hold(start, rows, results, chain)
    all_ms = (time.perf_counter() - t) * 1e3
    start, rows, results = pieces[-1]
    _, last_ms = ms(runs.hold, start, rows, results, chain)
    _, over_ms = ms(runs.over, start, rows, chain)
    _, part_ms = ms(runs.part, start, rows, chain)
    _, spans_ms = ms(runs.spans, chain)
    _, beside_ms = ms(runs.beside, "count", chain.keys["count"], 0, 600)
    total = sum(run.size for run in runs)

    folder = tempfile.mkdtemp()
    f = held.File(os.path.join(folder, "many.series"))
    _, first_ms = ms(f.write, list(runs)[:-1])
    _, added_ms = ms(f.write, list(runs))
    _, gone_ms = ms(f.write, list(runs)[1:])
    size = os.path.getsize(f.path)
    _, load_ms = ms(held.File(f.path).load)
    os.remove(f.path)
    os.rmdir(folder)

    half = held.Runs(total // 2, size_of)
    for start, rows, results in pieces:
        half.hold(start, rows, results, chain)
    left = sorted(run.start for run in half)
    first_gone = half.over(pieces[0][0], pieces[0][1], chain) is None

    under = held.Runs(1 << 40, size_of)
    under.hold(clip.start, clip.rows, clip.results, chain)
    taken = sum(under.hold(start, rows, results, chain) for start, rows, results in pieces)
    over_clip = held.Runs(1 << 40, size_of)
    for start, rows, results in pieces:
        over_clip.hold(start, rows, results, chain)
    over_clip.hold(clip.start, clip.rows, clip.results, chain)

    print(f"{len(pieces):6d} {clip.rows // len(pieces):6d} {all_ms + last_ms:9.0f} {last_ms:8.2f} {over_ms:8.2f} {part_ms:8.2f} "
          f"{spans_ms:8.2f} {beside_ms:8.2f} {first_ms:9.0f} {added_ms:8.1f} {gone_ms:8.1f} {load_ms:8.0f} {size / 2**20:7.1f} "
          f"{len(left):6d} {left[0] if left else -1:7d} {str(first_gone):>6s} {taken:6d} {len(over_clip):6d}")


def main():
    (clip,) = held.File(SERIES).load()
    chain = held.Chain({nid: r["key"] for nid, r in clip.results.items()}, frozenset(clip.results) - {"smooth"})
    share = clip.size / clip.rows / len(clip.results)

    def size_of(nid, result):
        return int(share * len(result["signal"]))

    print(f"{SERIES}: one run, {clip.rows} rows from {clip.start}, {clip.size} bytes as it was held, "
          f"{clip.size / clip.rows:.0f} a row, nodes {list(clip.results)}")
    what_a_band_makes(clip)
    print()
    print("the clip's run cut into N runs, ms unless said")
    print("     N   rows  hold all hold one     over     part    spans   beside write all  add one drop one     load    MB "
          "  left  first   gone  taken  after")
    for n in COUNTS:
        if time.perf_counter() - BEGAN > BUDGET:
            print(f"{n:6d} not begun: {BUDGET:.0f} s were spent")
            continue
        at(clip, n, chain, size_of)
    print()
    print("left, first, gone: with the limit half of what the N take, the runs left, the earliest row any begins at, "
          "and whether the first period is then served by none")
    print("taken: of the N, those held when the clip's run is held already; after: the runs held once the clip's run is held after the N")
    print(f"{time.perf_counter() - BEGAN:.1f} s in all")


if __name__ == "__main__":
    main()
