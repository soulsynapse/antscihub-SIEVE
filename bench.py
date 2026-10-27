"""Headless numbers for README STATUS. Runs the graph directly, no Qt.

    .venv\\Scripts\\python bench.py [video] [rows]
"""
import sys
import time

from sieve_player import Decoder, document
from sieve_player.graph import Graph
from tools import gray, motion, rescale, threshold

path = sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4"
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 600


def fill(graph, n):
    t = time.perf_counter()
    for r in range(n):
        graph.compute(graph.walk, r)
    return time.perf_counter() - t


dec = Decoder(path)
tools = [gray, rescale, threshold, motion]
doc = document.from_tools(tools, path)
graph = Graph(doc, dec, tools)
print(f"{path}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows; window {rows} rows")

t_fill = fill(graph, rows)
print(f"fill {rows} rows (decode+gray+rescale+threshold): {t_fill:.2f} s  "
      f"decodes={dec.decodes} seeks={dec.seeks} memo={graph.memo.bytes >> 20} MB")
assert dec.decodes == rows, "decodes != rows walked"

t_refill = fill(graph, rows)
print(f"re-walk, nothing changed: {t_refill * 1000:.1f} ms  decodes={dec.decodes}")

doc.node("threshold").params.update(thresh=90)
graph.sync()
t_thr = fill(graph, rows)
print(f"threshold drag (stage 3 only reruns): {t_thr * 1000:.1f} ms  decodes={dec.decodes}")

doc.node("rescale").params.update(scale=0.4)
graph.sync()
t_res = fill(graph, rows)
print(f"rescale drag (stages 2+3 rerun; decoder cache holds {dec._cache_rows} rows): "
      f"{t_res:.2f} s  decodes={dec.decodes} seeks={dec.seeks}")
