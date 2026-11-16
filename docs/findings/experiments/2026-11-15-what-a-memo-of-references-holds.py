"""One-off: what the memo and the process hold over a walk of video -> region with no shape chosen ->
rescale at 1.0 -> gray, with a result that is another store's array held as a reference; with
`as-handed` for a third argument, held as the run handed it, which is what the memo did before,
graph.to_hold replaced by one that hands back its result; and with `as-copies`, held as a copy of
its own, to_hold told every result is to be pinned. Says the ms a run of each node, the
memo's bytes and discards, the cache's bytes, the process's memory and how many of the rows walked
each node still answers without a run. Run from the repo root, once each way, a process each:
python docs/findings/experiments/2026-11-15-what-a-memo-of-references-holds.py <video> <geometry> [as-handed | as-copies]"""
import os
import sys
import time

import psutil

sys.path.insert(0, os.getcwd())

from sieve_player import document as D  # noqa: E402
from sieve_player import graph as G  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from tools import gray, region, rescale  # noqa: E402

ROWS, LIMIT = 200, 2 << 30
video, geometry = sys.argv[1], sys.argv[2]
how = sys.argv[3] if len(sys.argv) > 3 else "by reference"
to_hold = G.to_hold
if how == "as-handed":
    G.to_hold = lambda v, handed, pinned: v
elif how == "as-copies":
    G.to_hold = lambda v, handed, pinned: to_hold(v, handed, True)

doc = D.from_tools([region, rescale, gray], video)
doc.node("region").params.update(region.load_geometry(geometry))
doc.node("rescale").params["scale"] = 1.0
g = G.Graph(doc, Decoder(video, cache_bytes=LIMIT), [region, rescale, gray], memo_bytes=LIMIT)
ms = {}
g.on_event = lambda ev: ms.setdefault(ev.node, []).append(ev.ms) if ev.kind in ("run", "decode", "seek") else None
before = psutil.Process().memory_info().rss
t = time.perf_counter()
for r in range(ROWS):
    g.compute("gray", r)
took = time.perf_counter() - t
rss = psutil.Process().memory_info().rss
print(f"{os.path.basename(video)}, {ROWS} rows, results held {how}: {took / ROWS * 1000:.2f} ms a row")
for nid in ("video", "region", "rescale", "gray"):
    print(f"  {nid}: {sum(ms[nid]) / len(ms[nid]):.3f} ms a run over {len(ms[nid])} runs; "
          f"{sum(g.peek(r, nid) is not None for r in range(ROWS))} of {ROWS} rows answered without a run")
print(f"  memo {g.memo.bytes / 2**20:.0f} MB of {LIMIT >> 20}, {g.memo.evictions} discards; cache {g.decoder.cache_bytes / 2**20:.0f} MB of {LIMIT >> 20}; "
      f"the process grew {(rss - before) / 2**20:.0f} MB over the walk")
g.decoder.close()
