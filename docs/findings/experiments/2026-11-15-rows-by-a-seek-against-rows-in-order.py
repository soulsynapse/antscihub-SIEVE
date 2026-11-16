"""One-off: whether sieve_player's Decoder hands out by a seek the row it hands out in order. The
first ROWS rows are read in order on one Decoder; then on another, holding one frame, every one of
them from the last to the first, so each read is a seek, and each frame is compared with the row in
order. Says how many differ, which, the seeks and decodes spent and the mean of a seek. Stops at
BUDGET seconds and says how far it got. Run from the repo root:
python docs/findings/experiments/2026-11-15-rows-by-a-seek-against-rows-in-order.py <video> [rows]"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player.decoder import Decoder  # noqa: E402

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
BUDGET = 45.0
began = time.perf_counter()

walk = Decoder(path)
in_order = [walk.read(r)[::4, ::4].copy() for r in range(ROWS)]
walk.close()

d = Decoder(path, cache_bytes=1)
d.read(ROWS + 40)
off, read = {}, 0
for r in reversed(range(ROWS)):
    if time.perf_counter() - began > BUDGET:
        break
    f = d.read(r)[::4, ::4]
    read += 1
    if not np.array_equal(f, in_order[r]):
        off[r] = [k for k, g in enumerate(in_order) if np.array_equal(f, g)] or "no row"
print(f"{path}: {read} of the first {ROWS} rows by a seek, {len(off)} another row than in order {off or ''}; "
      f"{d.seeks} seeks, {d.decodes} decodes, a seek {d.seek_ms:.1f} ms in the mean, a step {d.step_ms:.1f} ms; "
      f"{time.perf_counter() - began:.0f} s")
d.close()
