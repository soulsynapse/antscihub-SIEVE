"""One-off: what the Decoder's seeks cost with each landing numbered by the frame's time, against
the Decoder of a commit before that, loaded from git. Each workload runs on a fresh Decoder holding
one frame, the two decoders turn about, REPEATS times, and the median is given in ms:
  first    one seek to the middle row on a Decoder just opened, with the opening
  far      SEEKS seeks to rows drawn at random past row 61, per seek
  back     SEEKS rows from the middle, each one before the last, per seek
  top      rows 29 to 0, each one before the last, after a read of row 80, per seek
  walk     the first 200 rows in order, per row
Stops starting repeats at BUDGET seconds; `only` names the workloads to run, by commas. Run from the
repo root:
python docs/findings/experiments/2026-11-15-what-numbering-a-seek-by-its-time-costs.py <commit> <video> [seeks] [repeats] [only]"""
import os
import random
import statistics
import subprocess
import sys
import time
import types

sys.path.insert(0, os.getcwd())

from sieve_player import decoder as new  # noqa: E402

commit, path = sys.argv[1], sys.argv[2]
SEEKS = int(sys.argv[3]) if len(sys.argv) > 3 else 40
REPEATS = int(sys.argv[4]) if len(sys.argv) > 4 else 3
BUDGET = 30.0
began = time.perf_counter()

old = types.ModuleType("decoder_before")
exec(subprocess.run(["git", "show", f"{commit}:sieve_player/decoder.py"], check=True, capture_output=True).stdout.decode("utf-8"),
     old.__dict__)

count = new.probe(path)[3]
middle = count // 2
random.seed(0)
far_rows = [random.randrange(62, count - 600 if count > 1300 else count - 2) for _ in range(SEEKS)]


def first(m):
    t = time.perf_counter()
    d = m.Decoder(path, cache_bytes=1)
    d.read(middle)
    spent = time.perf_counter() - t
    d.close()
    return spent * 1000


def over(rows, before=None):
    def run(m):
        d = m.Decoder(path, cache_bytes=1)
        if before is not None:
            d.read(before)
        t = time.perf_counter()
        for r in rows:
            d.read(r)
        spent = time.perf_counter() - t
        d.close()
        return spent * 1000 / len(rows)
    return run


workloads = {
    "first": first,
    "far": over(far_rows),
    "back": over(range(middle + SEEKS, middle, -1), before=middle + SEEKS + 1),
    "walk": over(range(200)),
    "top": over(range(29, -1, -1), before=80),
}
only = sys.argv[5].split(",") if len(sys.argv) > 5 else list(workloads)
workloads = {k: v for k, v in workloads.items() if k in only}
print(f"{path}: {count} rows, {SEEKS} seeks a workload; ms, median of the repeats run, before then after")
for name, run in workloads.items():
    took = {"before": [], "after": []}
    for _ in range(REPEATS):
        if time.perf_counter() - began > BUDGET:
            break
        took["before"].append(run(old))
        took["after"].append(run(new))
    if took["after"]:
        b, a = statistics.median(took["before"]), statistics.median(took["after"])
        print(f"  {name}: {b:.2f} {a:.2f}  ({len(took['after'])} repeats, each {[round(x, 2) for x in took['before']]} "
              f"{[round(x, 2) for x in took['after']]})")
    else:
        print(f"  {name}: not run, out of time")
print(f"{time.perf_counter() - began:.0f} s")
