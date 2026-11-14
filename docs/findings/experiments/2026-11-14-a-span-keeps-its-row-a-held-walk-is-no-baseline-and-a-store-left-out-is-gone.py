"""Three feeds through a Ledger and the catalogue: a walk whose node grows, told every row and
every thirty-second; a slowdown that stays, with and without a walk between in which the slowed
node was held; and a cache whose key a new plan changed. Prints what each shows and exits 1 where
the telling changes the growth found, the held walk hides the slowdown, or the old key is still a store.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-14-a-span-keeps-its-row-a-held-walk-is-no-baseline-and-a-store-left-out-is-gone.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sieve_player.catalogue import grows, slower, stores_at  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.stream import Event  # noqa: E402

T = [0.0]


def ev(kind, node=None, row=None, ms=0.0, length=None, keys=None, facts=None):
    e = Event(node, row, node, kind, 0, ms, T[0], "worker", ms, "walk", length, keys, None, "walk", node, "window", facts, None)
    T[0] += ms / 1000 + 1e-4
    return e


def plan(nodes):
    return {"walk": nodes[0], "chain": [], "pinned": [], "shown": None, "over": None,
            "nodes": {n: {"served": False, "static": False, "kind": "frame", "steps": False, "reads": {}} for n in nodes}}


def ledger(keys):
    T[0] = 0.0
    led = Ledger()
    led.event(ev("sync", keys=keys, facts=plan(list(keys))))
    return led


def walk(led, length, cost, every=1, caches=None):
    """One walk of `length` rows told every `every`; cost(row) is {node: ms}, a node not in it held."""
    led.event(ev("begin", row=0, length=length))
    for r in range(length):
        for n, ms in cost(r).items():
            led.event(ev("run", n, r, ms))
        if (r + 1) % every == 0 or r + 1 == length:
            led.event(ev("progress", row=r + 1, length=length, facts={"hits": {}, "caches": caches or {}}))


ok, counts = True, []
for every in (1, 32):
    led = ledger({"a": "ka"})
    walk(led, 64, lambda r: {"a": 1.0 + r}, every)
    walk(led, 8, lambda r: {"a": 1.0})
    v = led.view()
    counts.append(v.walks[0].nodes["a"].counts)
    print(f"told every {every}: spans along the range {counts[-1]}, grows found {len(grows(v))}")
    ok = ok and len(grows(v)) == 1
ok = ok and counts[0] == counts[1]

for held in (False, True):
    led = ledger({"f": "kf", "c": "kc"})
    walk(led, 16, lambda r: {"f": 1.0, "c": 1.0})
    if held:
        walk(led, 16, lambda r: {"c": 1.0})
    for _ in range(2):
        walk(led, 16, lambda r: {"f": 3.0, "c": 1.0})
    walk(led, 8, lambda r: {"c": 1.0})
    n = len(slower(led.view()))
    print(f"f three times slower in two walks, a walk that held f between {held}: slower found in {n}")
    ok = ok and n == 2

led = ledger({"a": "k1"})
walk(led, 8, lambda r: {"a": 1.0}, caches={"k1": {"bytes": 100, "limit": 200}})
led.event(ev("sync", keys={"a": "k2"}, facts=plan(["a"])))
walk(led, 8, lambda r: {"a": 1.0}, caches={"k2": {"bytes": 50, "limit": 200}})
print("the stores after the cache's key went from k1 to k2:", stores_at(led.view()))
ok = ok and set(stores_at(led.view())) == {"k2"}
sys.exit(0 if ok else 1)
