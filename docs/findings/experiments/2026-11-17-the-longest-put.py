"""The longest single Memo.put once the memo is full of <entries> image entries, under the graph's
own order where the tree has one, a window of 600 rows held and a walk going on past it: what one
thread holds the memo's lock for while it lets go. <tree> is a checkout of the repository, this
one or another commit's (`git archive <commit> | tar -x -C <dir>`), so two can be set side by side.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-the-longest-put.py <tree> <entries> <a document with motion and coarsegrain nodes>"""
import os
import sys
import time

tree, N, docpath = os.path.abspath(sys.argv[1]), int(sys.argv[2]), os.path.abspath(sys.argv[3])
sys.path.insert(0, tree)
os.chdir(tree)

import numpy as np

from sieve_player import document
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.registry import discover

SIZE = 64
tools = {e.name: e.module for e in discover("tools") if e.ok}
doc = document.load(docpath, tools)
g = Graph(doc, Decoder(doc.video_path(), cache_bytes=32 << 20), tools, memo_bytes=N * SIZE)
g.sync()
p = g.snapshot()
keys = [p.entries["motion"].raw_key, p.entries["coarsegrain"].raw_key]
if hasattr(g, "holds"):
    g.holds(0, 600)
    g.looks_at(10)


def walk_at(row):
    """The clip lane's walk is at `row`, said as walk_row says it in whichever tree this is."""
    if hasattr(g, "_walks_at"):
        g._walks_at = {**g._walks_at, "clip": row}
    elif hasattr(g, "_at"):
        g._at = {**g._at, "clip": row}


plane = np.zeros((8, 8), np.uint8)
longest, total, over = 0.0, 0.0, 0
rows = int(N * 0.75)      # two entries a row: the memo fills at N / 2 rows, and half as many again are put past it
for r in range(rows):
    if r % 100 == 0:
        walk_at(r)
    for k in keys:
        t = time.perf_counter()
        g.memo.put((k, r), plane)
        dt = time.perf_counter() - t
        total += dt
        longest = max(longest, dt)
        over += dt > 0.001
print(f"{os.path.basename(tree):<24} {N:>7} entries at the limit: longest put {1000 * longest:8.2f} ms, puts over 1 ms {over:4d}, "
      f"mean put {1e6 * total / (2 * rows):6.2f} us, discards {g.memo.evictions}, "
      f"window rows held {sum(g.memo.get((k, r), count=False) is not None for k in keys for r in range(600))} of 1200", flush=True)
os._exit(0)
