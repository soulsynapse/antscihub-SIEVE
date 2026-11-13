"""Headless timings of the graph on one video. Runs the graph directly, no Qt.

    .venv\\Scripts\\python bench.py [video] [rows]

The first three lines are the probe's own cost: a cold fill with the callable unset, run twice for
the noise between runs, then a cold fill with a dump attached and the dump's size, each on a fresh
decoder and graph so all three decode. The rest is the player's story on the last graph.
"""
import os
import sys
import tempfile
import time

from sieve_player import Decoder, document
from sieve_player.graph import Graph
from sieve_player.stats import Stats
from sieve_player.trace import Dump
from tools import gray, motion, reduce, rescale, threshold

path = sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4"
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 600
tools = [gray, rescale, threshold, motion, reduce]


def fill(graph, n):
    t = time.perf_counter()
    for r in range(n):
        graph.walk_row(r)
        graph.progress(r + 1, n)
    return time.perf_counter() - t


def fresh():
    dec = Decoder(path)
    doc = document.from_tools(tools, path)
    return dec, doc, Graph(doc, dec, tools)


dec, doc, graph = fresh()
print(f"{path}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows; window {rows} rows")
t_bare = [fill(graph, rows)]
dec.close()
dec, doc, graph = fresh()
t_bare.append(fill(graph, rows))
dec.close()
dec, doc, graph = fresh()
stats = Stats(graph)
dump = Dump(graph, os.path.join(tempfile.gettempdir(), "sieve-bench.jsonl"))
t_dump = fill(graph, rows)
dump.close()
print(f"cold fill, probe unset:     {t_bare[0]:.2f} s, again {t_bare[1]:.2f} s")
print(f"cold fill, dump attached:   {t_dump:.2f} s; dump {os.path.getsize(dump.path) >> 10} KB")
print(f"fill {rows} rows (decode+gray+rescale+threshold+motion)  decodes={dec.decodes} seeks={dec.seeks} memo={graph.memo.bytes >> 20} MB")
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
print(f"rescale drag (stages 2+3 rerun; decoder cache holds {len(dec._cache)} rows): "
      f"{t_res:.2f} s  decodes={dec.decodes} seeks={dec.seeks}")

s = stats.snapshot()
print(f"\n{'node':<12}{'last ms':>9}{'mean ms':>9}{'runs':>7}")
for nid, v in sorted(s["nodes"].items(), key=lambda kv: -kv[1]["mean"]):
    print(f"{nid:<12}{v['last']:>9.2f}{v['mean']:>9.2f}{v['n']:>7}")
print(f"walk {s['walk_rows_s'] or 0:.1f} rows/s of {s['fps']:.1f} fps; step {s['step_ms'] or 0:.1f} ms x{s['decodes']}, "
      f"seek {s['seek_ms'] or 0:.0f} ms x{s['seeks']}; memo {s['memo_mb']:.0f} MB hit {s['memo_hit'] or 0:.0%} evicted {s['evictions']}, "
      f"cache {s['cache_mb']:.0f} MB hit {s['cache_hit'] or 0:.0%}")
