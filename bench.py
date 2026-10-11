"""Headless numbers for README STATUS. Runs the chain directly, no Qt.

    .venv\\Scripts\\python bench.py [video] [rows]
"""
import sys
import time

from sieve_player import Chain, Decoder
from tools import motion, rescale, threshold

path = sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4"
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 600


def fill(chain, n):
    t = time.perf_counter()
    for r in range(n):
        chain.compute(chain.last, r)
    return time.perf_counter() - t


dec = Decoder(path)
chain = Chain(dec, [rescale, threshold, motion])
print(f"{path}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps, {dec.count} rows; window {rows} rows")

t_fill = fill(chain, rows)
print(f"fill {rows} rows (decode+rescale+threshold): {t_fill:.2f} s  "
      f"decodes={dec.decodes} seeks={dec.seeks} memo={chain.memo.bytes >> 20} MB")
assert dec.decodes == rows, "decodes != rows walked"

t_refill = fill(chain, rows)
print(f"re-walk, nothing changed: {t_refill * 1000:.1f} ms  decodes={dec.decodes}")

chain.set_params(1, {"thresh": 90, "invert": False})
t_thr = fill(chain, rows)
print(f"threshold drag (stage 2 only reruns): {t_thr * 1000:.1f} ms  decodes={dec.decodes}")

chain.set_params(0, {"scale": 0.4})
t_res = fill(chain, rows)
print(f"rescale drag (stage 1+2 rerun; decoder cache holds {dec._cache_rows} rows): "
      f"{t_res:.2f} s  decodes={dec.decodes} seeks={dec.seeks}")
