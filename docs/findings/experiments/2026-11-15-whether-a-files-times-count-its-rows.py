"""One-off: whether sieve_player's Decoder finds, of a file read in order, a stepped frame whose time
is not that of the packet its count names. Reads one row far on, so the Decoder has sought and holds
the file's frame times, then the first ROWS rows in order, or to the stream's end, inside BUDGET
seconds, and says how many it read and whether the Decoder now numbers no seek on the file.
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
    d.read(min(ROWS, d.count) - 1)
    for r in range(min(ROWS, d.count)):
        if time.perf_counter() - began > BUDGET:
            break
        d.read(r)
        read += 1
except EndOfStream:
    pass
said = "a time was not its row's packet's" if d._counts_only else "every time was its row's packet's"
print(f"{path}: {read} rows in order after {d.seeks} seeks, {len(d._times)} frame times; {said}; {time.perf_counter() - began:.0f} s")
d.close()
