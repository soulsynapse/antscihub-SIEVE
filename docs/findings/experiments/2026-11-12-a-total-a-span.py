"""What the ledger's fold of one span costs with a run's total a tuple made anew at each span, the
working tree's, against the list written in place of the commit named, default HEAD: the same events
through each ledger, the commit's modules read out of git into a temporary package, the two timed
in turn over ROUNDS rounds. The events are a walk's: each row a decode, three runs and a progress.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-a-total-a-span.py [commit]
"""
import importlib
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
ROWS, ROUNDS = 20000, 15

with tempfile.TemporaryDirectory() as tmp:
    pkg = Path(tmp) / "committed"
    pkg.mkdir()
    (pkg / "__init__.py").write_bytes(b"")
    for name in ("stream", "trace", "ledger"):
        (pkg / f"{name}.py").write_bytes(subprocess.run(["git", "show", f"{COMMIT}:sieve_player/{name}.py"], cwd=ROOT,
                                                        capture_output=True, check=True).stdout)
    sys.path.insert(0, tmp)
    sides = {"committed": importlib.import_module("committed.ledger"), "working": importlib.import_module("sieve_player.ledger")}
    streams = {"committed": importlib.import_module("committed.stream"), "working": importlib.import_module("sieve_player.stream")}


def events(Event):
    def ev(kind, t, ms=0.0, node=None, row=None, **more):
        d = dict(node=node, row=row, key=node and "k" + node, kind=kind, bytes=1000, ms=ms, t=t, thread="w", cpu_ms=ms, serves="walk",
                 length=None, keys=None, reader=None, demand="walk", asked="c", lane="window", facts=None, shape=None)
        return Event(**d | more)
    out = [ev("begin", 0.0, row=0, length=ROWS)]
    for r in range(ROWS):
        t = r * 0.004
        out += [ev("decode", t + 0.0002, 0.5, "video", r, reader="a"), ev("run", t + 0.0001, 0.5, "a", r, reader="b"),
                ev("run", t, 1.0, "b", r, reader="c"), ev("run", t - 0.0001 if r else 0.0, 1.0, "c", r),
                ev("progress", t + 0.0035, row=r + 1, length=ROWS, facts={})]
    return out


took, spans = {name: [] for name in sides}, ROWS * 4
fed = {name: events(streams[name].Event) for name in sides}
views = {}
for _ in range(ROUNDS):
    for name, module in sides.items():
        led = module.Ledger()
        for e in fed[name]:
            led._q.append(e)
        t = time.perf_counter()
        views[name] = led.view()
        took[name].append((time.perf_counter() - t) / spans * 1e9)
a, b = (views[n].walks[0] for n in ("committed", "working"))
assert {n: [tuple(r) for r in x.runs.values()] for n, x in a.nodes.items()} == {n: [tuple(r) for r in x.runs.values()] for n, x in b.nodes.items()}
print(f"{spans} spans and {ROWS} progresses folded in one view, {ROUNDS} rounds in turn, ns a span, {COMMIT} against the working tree")
for name, ns in took.items():
    q = statistics.quantiles(ns, n=4)
    print(f"   {name:<10} least {min(ns):6.0f}  quartiles {q[0]:6.0f} {q[1]:6.0f} {q[2]:6.0f}  most {max(ns):6.0f}")
print(f"   the working tree's median less the commit's: {statistics.median(took['working']) - statistics.median(took['committed']):+.0f} ns a span")
