"""The measurement of docs/findings/2026-11-20-relinking-against-the-frames.md: over the crossings
clip, the frames through `blobs` computed a row at a time from a fresh graph, then `track` stepped
over those rows from the first, each timed per row.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-relinking-against-the-frames.py 2>NUL
"""
import os
import sys
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import computed, discover  # noqa: E402

CLIP_ROWS = 38100   # 00000.MTS's rows, as the held-runs finding read them

if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(os.path.join(ROOT, "video-tests", "purb-168-178.json"), tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n = g.count
    t = time.perf_counter()
    blobs = [g.compute("blobs", r) for r in range(n)]
    frames = time.perf_counter() - t
    track = tools["track"]
    params = computed(track, dict(doc.node("track").params))
    t = time.perf_counter()
    state = None
    for i, row in enumerate(blobs):
        state, _ = track.step(state, row, i, params)
    link = time.perf_counter() - t
    print(f"{n} rows, {np.mean([len(b) for b in blobs]):.1f} blobs a row")
    print(f"frames through blobs {frames / n * 1e3:.2f} ms a row; track.step {link / n * 1e3:.3f} ms a row; {frames / link:.0f}x")
    print(f"track stepped over {CLIP_ROWS} held rows: {link / n * CLIP_ROWS:.1f} s")
    g.close()
    g.decoder.close()
