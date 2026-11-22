"""Three bare walks of one document and video, each its own process, over one folder of kept
results: what each took, how it exited, and whether the later walks' results equal the first's.

Run from the repo root: python docs/findings/experiments/bare_walk_thrice.py <document.json> <video> <work folder>.
It writes only under the work folder. The finding it serves is docs/findings/bare-walk-crashes-on-the-full-file.md.
"""
import json
import os
import pickle
import subprocess
import sys
import time

import numpy as np

doc_path, video, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), sys.argv[3]
os.makedirs(work, exist_ok=True)
with open(doc_path, encoding="utf-8") as f:
    document = json.load(f)
tools = os.path.abspath("tools")
env = {**os.environ, "SIEVE_RESULTS": os.path.join(work, "results"), "PYTHONFAULTHANDLER": "1"}
outs = []
for turn in range(3):
    out = os.path.join(work, f"out{turn}.pkl")
    job = os.path.join(work, f"job{turn}.json")
    with open(job, "w", encoding="utf-8") as f:
        json.dump({"document": document, "path": doc_path, "video": video, "roots": [tools], "out": out}, f)
    began = time.perf_counter()
    p = subprocess.run([sys.executable, "-m", "sieve_player.bare", job], env=env, capture_output=True, text=True)
    took = time.perf_counter() - began
    last = [line for line in p.stdout.splitlines() if line.strip()][-1:]
    print(f"walk {turn}: {took:.1f} s, exit {p.returncode}, last line {last}, stderr {p.stderr[-600:]!r}")
    outs.append(out)


def same(p, q):
    """Equal field by field: a table's contour column holds objects, whose bytes are addresses."""
    if isinstance(p, dict):
        return p.keys() == q.keys() and all(same(p[k], q[k]) for k in p)
    if isinstance(p, (list, tuple)):
        return len(p) == len(q) and all(same(x, y) for x, y in zip(p, q))
    if isinstance(p, np.ndarray):
        if not isinstance(q, np.ndarray) or p.dtype != q.dtype or p.shape != q.shape or p.dtype.metadata != q.dtype.metadata:
            return False
        if p.dtype.names:
            return all(same(p[n], q[n]) for n in p.dtype.names)
        if p.dtype == object:
            return all(same(x, y) for x, y in zip(p.ravel(), q.ravel()))
        return p.tobytes() == q.tobytes()
    return type(p) is type(q) and bool(p == q or (p != p and q != q))


loaded = [pickle.load(open(o, "rb")) for o in outs if os.path.exists(o)]
for i, got in enumerate(loaded[1:], 1):
    diff = [k for k in loaded[0][0] if not same({x: v for x, v in loaded[0][0][k].items() if x != "code"},
                                                {x: v for x, v in got[0].get(k, {}).items() if x != "code"})]
    print(f"walk {i} against walk 0: {len(loaded[0][0])} nodes, differing {diff}")
size = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(env["SIEVE_RESULTS"]) for f in fs)
print(f"folder holds {size / 1e6:.2f} MB")
