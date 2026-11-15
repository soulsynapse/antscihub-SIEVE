"""One-off: whether sieve_player's Decoder finds, of a file read in order, a stepped frame whose time
gives another row than the count. Reads the first ROWS rows in order, or to the stream's end, inside
BUDGET seconds, and says how many it read and whether the Decoder now numbers no seek on the file.
Run from the repo root:
python docs/findings/experiments/2026-11-15-whether-a-files-times-count-its-rows.py <video> [rows]"""
import os
import sys
import time

sys.path.insert(0, os.getcwd())

from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402

path = sys.argv[1]
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 600
BUDGET = 40.0
began = time.perf_counter()
d = Decoder(path, cache_bytes=1)
read = 0
try:
    for r in range(min(ROWS, d.count)):
        if time.perf_counter() - began > BUDGET:
            break
        d.read(r)
        read += 1
except EndOfStream:
    pass
print(f"{path}: {read} rows in order, {d.fps:.3f} rows a second by the container; "
      f"{'a time gave another row than the count' if d._counts_only else 'every time gave the count'}; "
      f"{time.perf_counter() - began:.0f} s")
d.close()
