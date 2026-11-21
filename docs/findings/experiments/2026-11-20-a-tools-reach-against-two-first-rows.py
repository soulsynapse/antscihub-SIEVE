"""The one-off of docs/spec/a-cut-in-time.md's A tool's reach in rows: each tool that says a reach
other than its own row, and each that says none, run from two first rows over the crossings clip,
and the rows past the later first row at which the two runs differ, against what the tool says.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-tools-reach-against-two-first-rows.py 2>NUL

The document is video-tests/purb-168-178.json. A run from a first row is the caveman way: the tool
handed the footage from that row on as a clip of its own, a frame tool reading clip rows and a
series tool the series from there. What each reads is fixed, the gray plate, the document's blobs,
`track` from row 0 and `count`'s signal, so the tool under test alone begins twice. A tool keeps
to its reach where no row at or past its reach before, counted from the later first row, differs.
A reach after is not looked at: both runs end at the clip's last row.
"""
import os
import sys

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series  # noqa: E402
from sieve_player.registry import computed, defaults, discover, kind, reach_of  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
LATER = 100     # the later first row; the earlier is 0
FRAMES = 12     # rows past the later first row a frame tool is run at


def same(a, b):
    if isinstance(a, np.ndarray) and a.dtype.names:
        names = [n for n in a.dtype.names if a.dtype[n] != object]
        return len(a) == len(b) and a.dtype == b.dtype and all(np.array_equal(a[n], b[n], equal_nan=a.dtype[n].kind == "f") for n in names)
    return np.allclose(np.asarray(a, np.float64), np.asarray(b, np.float64), equal_nan=True)


def rows_of(result):
    return result["rows"] if "rows" in result else result["signal"]


if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n, fps = g.count, g.fps
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    plate = [g.compute("video", row) for row in range(LATER + FRAMES)]
    gray = [f if f.ndim == 2 else tools["gray"].run(lambda r, f=f: f, 0, {}) for f in plate]
    g.close()
    g.decoder.close()

    def ran(name, data, first):
        tool = tools[name]
        return rows_of(tool.run(Series(data[first:], "k", first, fps), computed(tool, defaults(tool))))

    tracks = ran("track", blobs, 0)
    signal = ran("count", blobs, 0)
    reads = {"tracks": tracks, "blobs": blobs, "signal": signal}
    print(f"{n} rows at {fps:.2f} fps, first rows 0 and {LATER}; a frame tool over {FRAMES} rows from {LATER}")
    print(f"{'tool':<14} {'says':<12} {'differ':>6} {'last':>5}  verdict")
    for name, tool in sorted(tools.items()):
        params = computed(tool, defaults(tool))
        before, _ = said = reach_of(tool, params)
        if said == (0, 0) or kind(tool) not in ("frame", "series"):
            continue
        try:
            if kind(tool) == "frame":
                if not {"gray"} & set(np.atleast_1d(tool.EXPECTS)) or tool.__dict__.get("STATIC") or tool.__dict__.get("INPUTS"):
                    print(f"{name:<14} {str(said):<12} not run: reads no gray plate alone")
                    continue
                a = [tool.run(lambda r: gray[r], LATER + k, params) for k in range(FRAMES)]
                b = [tool.run(lambda r: gray[LATER + r], k, params) for k in range(FRAMES)]
            else:
                data = next((reads[t] for t in np.atleast_1d(tool.EXPECTS) if t in reads), None)
                if data is None:
                    print(f"{name:<14} {str(said):<12} not run: reads none of {sorted(reads)}")
                    continue
                a, b = ran(name, data, 0)[LATER:], ran(name, data, LATER)
        except Exception as exc:
            print(f"{name:<14} {str(said):<12} not run: {type(exc).__name__}: {exc}")
            continue
        differ = [k for k, (x, y) in enumerate(zip(a, b)) if not same(x, y)]
        last = differ[-1] if differ else None
        verdict = "no bound said" if before is None else "kept" if last is None or last < before else "PAST ITS REACH"
        print(f"{name:<14} {str(said):<12} {len(differ):>6} {'-' if last is None else last:>5}  {verdict}")
