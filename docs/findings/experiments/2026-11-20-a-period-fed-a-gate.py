"""The one-off of docs/spec/a-cut-in-time.md's box of a `period` fed a series node's result on a
wire: `count` over the crossings clip, banded at its own median, wired into a `period`'s gate, and
the periods the plan gives the `period` against the runs of rows the gate keeps, counted here row
by row; and the `period`'s standing while no walk of `count` is held.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-period-fed-a-gate.py 2>NUL

The document is video-tests/purb-168-178.json with a `period` added under the video. The band is
this script's and not Kendrick's: a median makes periods of a count that chatters, which is what
the check wants and no more.
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
from sieve_player.graph import Graph, Series, gated  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from sieve_player.registry import computed, defaults, discover  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")


def runs_kept(gate):
    out, first = [], None
    for row, kept in enumerate(list(gate) + [False]):
        if kept and first is None:
            first = row
        elif not kept and first is not None:
            out.append((first, row))
            first = None
    return out


if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n, fps = g.count, g.fps
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    g.close()
    g.decoder.close()
    count = tools["count"]
    result = count.run(Series(blobs, "k", 0, fps), computed(count, defaults(count)))
    band = (float(np.median(result["signal"])), float(np.max(result["signal"])))
    doc.node("count").band = band
    period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"]))
    doc.connect("video", period.id)
    doc.connect("count", period.id, "gate")

    waiting = plan(doc, tools, "video key", cut_result=lambda nid, key, within: None).entries[period.id]
    print(f"no walk held: cuts {waiting.cuts}, fed {waiting.fed}, standing {waiting.standing!r}")

    asked = []

    def held(nid, key, within):
        asked.append((nid, key))
        return {**gated({**result, "key": key}, band, "signal")[0]}

    entries = plan(doc, tools, "video key", cut_result=held).entries
    cuts = [r.extent.rows for r in entries[period.id].cuts]
    gate = gated(result, band, "signal")[0]["gate"]
    expected = runs_kept(gate)
    print(f"{n} rows at {fps:.2f} fps; count banded at {band}, {int(gate.sum())} rows kept")
    print(f"asked of {asked[0][0]} under count's key {asked[0][1] == entries['count'].key}; standing {entries[period.id].standing!r}")
    print(f"periods: {len(cuts)}, against {len(expected)} runs the gate keeps: {'the same' if cuts == expected else 'DIFFER'}")
    print("first ten:", cuts[:10])
    touching = [(a, b) for (_, a), (b, _) in zip(cuts, cuts[1:]) if a >= b]
    print("periods that touch or overlap:", touching or "none")
