"""Cold fill of bench.py's graph, one consumer a process, every fill's time printed; for
docs/findings/2026-11-12-probe-cost-with-the-stream-facts.md. Run from the root of the tree under test, so two
trees are compared by running it in each in turn:

    .venv\\Scripts\\python docs\\findings\\experiments\\2026-11-12-probe-cost-with-the-stream-facts.py <video> <bare|list|dump|stats|both>
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.getcwd())

from sieve_player import Decoder, document
from sieve_player.graph import Graph
from sieve_player.stats import Stats
from sieve_player.trace import Dump
from tools import gray, motion, reduce, rescale, threshold

path, how, rows, fills = sys.argv[1], sys.argv[2], 600, 4
tools = [gray, rescale, threshold, motion, reduce]


def fill():
    dec = Decoder(path)
    g = Graph(document.from_tools(tools, path), dec, tools)
    dump = None
    if how == "list":
        g.on_event = [].append
    if how in ("stats", "both"):
        Stats(g)
    if how in ("dump", "both"):
        dump = Dump(g, os.path.join(tempfile.gettempdir(), f"sieve-probe-cost-{os.getpid()}.jsonl"))
    t = time.perf_counter()
    for r in range(rows):
        g.walk_row(r)
        g.progress(r + 1, rows)
    t = time.perf_counter() - t
    if dump:
        dump.close()
        os.remove(dump.path)
    dec.close()
    return t


print(f"{how:5} " + " ".join(f"{fill() * 1000:4.0f}" for _ in range(fills)) + "  ms")
