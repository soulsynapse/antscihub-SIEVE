"""What a held file costs to write and to read, on one written as a single pickle of (stamp, runs),
the layout before held.VERSION 4:

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-what-the-held-file-costs.py FILE
    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-what-the-held-file-costs.py FILE --convert

The first times that layout's read and write against held.File's on a copy: the file written
first, a run added, a run let go, and the file read. The second writes FILE again as held.File
does, under its own footage and tool files, the old beside it as FILE.v3, so a walk held before the
layout changed is not walked again.
"""
import io
import os
import pickle
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import held  # noqa: E402

CLIP = 345595       # rows of square-1.mp4, the clip the bare walk of the finding was over


def ms(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000


def same(v, w):
    if isinstance(v, np.ndarray) and v.dtype == object:
        return len(v) == len(w) and all(np.array_equal(a, b) and a.dtype == b.dtype for a, b in zip(v, w))
    return np.array_equal(v, w) if isinstance(v, np.ndarray) else v == w


def main(path, convert=False):
    with open(path, "rb") as f:
        was, read = ms(lambda: pickle.load(f))
    if len(was) == 2:
        stamp, runs = (held.VERSION, *was[0][1:]), was[1]
    else:       # a file of records already: its first run repeated to CLIP rows stands for a clip run
        stamp = was
        (_, n, results, size), *rest = held.File(path, stamp).load()
        k = -(-CLIP // n)
        clip = {nid: {f: np.concatenate([v] * k)[:CLIP] if isinstance(v, np.ndarray) and len(v) == n else v for f, v in r.items()}
                for nid, r in results.items()}
        runs = [(0, CLIP, clip, size * k), *rest]
        _, read = ms(lambda: pickle.loads(pickle.dumps((stamp, runs), protocol=pickle.HIGHEST_PROTOCOL)))
    if convert:
        shutil.copy(path, f"{path}.v3")
        held.File(path, stamp).write(runs)
        print(f"{path}: {len(runs)} runs written as records, the old at {path}.v3")
        return 0
    buffer = io.BytesIO()
    _, wrote = ms(lambda: pickle.dump((stamp, runs), buffer, protocol=pickle.HIGHEST_PROTOCOL))
    print(f"{len(runs)} runs, the longest {max(run[1] for run in runs)} rows; as one pickle {buffer.tell() / 1e6:.1f} MB")
    if len(was) == 2:
        print(f"one pickle: read {read:.0f} ms, written {wrote:.0f} ms, at every write")
    else:
        print("one pickle: not timed, a repeated row being one object to pickle and written once")
    file = held.File(os.path.join(tempfile.mkdtemp(prefix="sieve-held-costs-"), "x.series"), stamp)
    _, first = ms(lambda: file.write(runs))
    size = os.path.getsize(file.path)
    short = min(runs, key=lambda run: run[1])
    more = [*runs, tuple(short)]
    more[-1] = (*short[:3], short[3] + 0)
    _, added = ms(lambda: file.write(more))
    fewer = [run for run in more if run is not short]
    _, let_go = ms(lambda: file.write(fewer))
    back, loaded = ms(lambda: held.File(file.path, stamp).load())
    print(f"records: first written {first:.0f} ms and {size / 1e6:.1f} MB; a run of {short[1]} rows added {added:.2f} ms; "
          f"one let go and the file made again {let_go:.0f} ms; read {loaded:.0f} ms")
    ok = len(back) == len(fewer) and all(a[:2] == b[:2] and all(same(a[2][nid][f], b[2][nid][f]) for nid in a[2] for f in a[2][nid])
                                         for a, b in zip(fewer, back))
    print("read back equal to what was written" if ok else "FAILED: read back differs")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--convert" in sys.argv[2:]))
