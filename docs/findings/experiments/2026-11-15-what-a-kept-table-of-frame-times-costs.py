"""One-off: what sieve_player's decoder.frame_times takes on a file with its table read off the
packets, and with the table kept in a store. The store is a folder made for the run and removed
after. Says the seconds of the first, the seconds of a second with the process's own copy dropped,
and the kept file's bytes. Run from the repo root:
python docs/findings/experiments/2026-11-15-what-a-kept-table-of-frame-times-costs.py <video>"""
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.getcwd())

from sieve_player import decoder  # noqa: E402

path = sys.argv[1]
folder = tempfile.mkdtemp()
decoder.STORE = lambda: folder
try:
    t = time.perf_counter()
    first = decoder.frame_times(path)
    read = time.perf_counter() - t
    decoder._times.clear()
    t = time.perf_counter()
    again = decoder.frame_times(path)
    kept = time.perf_counter() - t
    file = decoder._times_file(path)
    print(f"{path}: {len(first)} frame times off the packets in {read:.2f} s; from the kept table in {kept * 1000:.1f} ms, "
          f"{os.path.getsize(file)} bytes, {'the same' if (first == again).all() else 'ANOTHER'} table")
finally:
    shutil.rmtree(folder, ignore_errors=True)
