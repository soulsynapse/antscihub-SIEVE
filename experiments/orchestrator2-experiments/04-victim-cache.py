"""Does a victim cache beat dropping everything unreferenced, and which rule?

README question 4. `pool.py` is a buffer pool with the pinning half done and
the replacement half missing: `drop_unreferenced` discards every unpinned key,
so unreferenced means deleted. This asks whether retaining some of them helps,
and refuses to answer it by picking the textbook policy and asserting the fit.

## The shape

The walk's leg 5 — *"returning to A: the graph released it when B declared, so
this is a cold refill"* — run headlessly. Three landings, a ceiling above one
window and below two, so B's arrival forces eviction and what survives of A is
the policy's decision:

    land A  ->  land B  ->  land A again      (the metric is the third)

and a second shape where the return is offset by half a window, because a
person does not come back to the frame they left. Under the exact return every
evicted row is wanted again at the same moment, so nothing can rank them; under
the offset return only half of what was kept is useful, and which half a policy
kept is visible.

## The arms

`replacement.py` carries the rules and the argument for measuring rather than
choosing: GreedyDual-Size is the textbook answer for items differing in cost
and size, and SIEVE breaks its independence, online and random-access
assumptions. So: `drop-all` (V1), `lru`, `gdsize`, `contiguous`, and `belady`
as an oracle that is handed the script.

**The oracle is here to bound the question before the policies are argued
about.** If it wins little over `drop-all`, no ranking matters and the answer
is that the ceiling is the only lever.

## What is read, and why not just decodes

Decodes are the obvious metric and are not sufficient. A policy that retains a
*scattered* half of window A hands the sweep a window it has to seek through,
and the wall is a sequential term plus about a third of a second per seek
(`2026.08.30-the-pressure-dispatcher-preempts-into-seeks`). So fewer decodes
can cost more wall, and **seeks on the return leg are reported beside the
decode count**. A row where decodes fall while seeks rise is the policy being
wrong for this workload rather than the idea being wrong — and it is the
outcome pre-registered for GreedyDual-Size, whose ranking treats items as
independent when their costs are not.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from harness import FOOTAGE

import forms as forms_mod
from dispatcher import Dispatcher
from fetch import Fetcher
from graph import Graph
from nodes import Sweep
from pool import Pool
from replacement import Belady, Contiguous, DropAll, GreedyDualSize, LRU

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
WINDOW = 120
#: above one window and below two, so B's arrival forces eviction and what
#: survives of A is a decision rather than an accident of sizing. 1.5 leaves
#: room for half a window of victims, which is the most any policy can keep.
CEILING_WINDOWS = 1.5
COVER_TIMEOUT_S = 180.0
#: interleaved, for the reason every timed arm in this folder is: this machine
#: drifts by more than small differences, and one run per arm read that drift
#: as an effect once already.
REPS = 3


def _open_total():
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
        return total - GOP, stream.width, stream.height


def _wait_covered(pool: Pool, start: int, end: int, form_key: str) -> bool:
    deadline = time.perf_counter() + COVER_TIMEOUT_S
    while time.perf_counter() < deadline:
        if len(pool.covered(start, end, form_key)) >= end - start:
            return True
        time.sleep(0.01)
    return False


POLICIES = ("drop-all", "lru", "gdsize", "contiguous", "belady")


def _med(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def _runs(rows: list[int]) -> int:
    """How many contiguous runs a set of rows forms. One is a single band."""
    if not rows:
        return 0
    ordered = sorted(rows)
    return 1 + sum(1 for a, b in zip(ordered, ordered[1:]) if b != a + 1)


def run_arm(policy_name: str, width: int, height: int,
            windows: list[tuple[int, int]], ceiling: int) -> dict:
    graph = Graph()
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    form_key = source_form.key()

    step = {"i": 0}
    row_sets = [set(range(a, b)) for a, b in windows]

    def next_use(key):
        """Which future landing wants this row, or None. Belady's input, and
        the reason it is an oracle rather than a policy."""
        row, _fk = key
        for index in range(step["i"] + 1, len(row_sets)):
            if row in row_sets[index]:
                return index
        return None

    policy = {"drop-all": DropAll, "lru": LRU,
              "gdsize": GreedyDualSize, "contiguous": Contiguous}.get(
                  policy_name)
    policy = Belady(next_use) if policy_name == "belady" else policy()

    pool = Pool(graph, budget_bytes=ceiling, policy=policy)
    dispatcher = Dispatcher(graph, pool, form_key, lambda _band: Fetcher(BIG),
                            recorders=2, readers=1)
    dispatcher.start()

    legs = []
    try:
        for index, (start, end) in enumerate(windows):
            step["i"] = index
            before = (dispatcher.served, dispatcher.seeks, pool.victim_hits)
            resident_before = sorted(
                r for r in pool.covered(start, end, form_key))
            anchor = start + (end - start) // 2
            sweep = Sweep(start, end, anchor, form_key, graph)
            sweep.declare()
            if policy_name == "drop-all":
                #: V1's explorer swept at every landing, which is what
                #: `drop_unreferenced` is. The other arms let the byte
                #: ceiling decide, which is what makes them victim caches.
                pool.drop_unreferenced()
            t0 = time.perf_counter()
            covered = _wait_covered(pool, start, end, form_key)
            wall = time.perf_counter() - t0
            legs.append({
                "leg": index,
                "window": [start, end],
                "covered": covered,
                "wall_s": round(wall, 3),
                "decodes": dispatcher.served - before[0],
                "seeks": dispatcher.seeks - before[1],
                "victim_hits": pool.victim_hits - before[2],
                "resident_on_arrival": len(resident_before),
                "runs_on_arrival": _runs(resident_before),
                "pool_gb": pool.stats()["gb"],
            })
    finally:
        dispatcher.stop()
    return {"policy": policy_name, "legs": legs}


def main() -> None:
    total, width, height = _open_total()
    frame_bytes = width * height
    ceiling = int(WINDOW * frame_bytes * CEILING_WINDOWS)

    a = total // 3
    b = min(a + 2 * WINDOW, total - WINDOW)
    shapes = {
        "exact-return": [(a, a + WINDOW), (b, b + WINDOW), (a, a + WINDOW)],
        "offset-return": [(a, a + WINDOW), (b, b + WINDOW),
                          (a + WINDOW // 2, a + WINDOW // 2 + WINDOW)],
    }

    run = harness.Run(
        experiment="04-victim-cache",
        question="Does retaining unpinned keys beat dropping them, and does "
                 "any ranking beat any other?")
    run.add_footage(BIG)
    run.note(f"topology: source -> pool -> one sweep declaring a "
             f"{WINDOW}-frame window attention-first from its midpoint. "
             f"Three landings per shape; the third is the metric. Ceiling "
             f"{CEILING_WINDOWS} windows = {ceiling / (1 << 30):.2f} GB at "
             f"{frame_bytes / (1 << 20):.1f} MB a frame, so half a window of "
             f"victims is the most any policy can keep.")
    run.note("core shape: 1 fetch thread, 1 reader, 2 recorders, no step and "
             "no interactive consumer — this measures retention, and a "
             "second consumer would make the decode counts a statement "
             "about scheduling as well.")
    run.note("`drop-all` calls drop_unreferenced at each landing, which is "
             "V1's explorer. Every other arm lets the byte ceiling decide, "
             "which is what makes it a victim cache; the ceiling never fired "
             "in any V1 run, per the derived-eviction finding.")
    run.note("seeks are reported beside decodes because a scattered remnant "
             "must be seeked through: fewer decodes at more seeks is the "
             "pre-registered way a per-item ranking fails here, since "
             "GreedyDual-Size treats items as independent and a frame's cost "
             "depends on whether its neighbour is resident.")

    for shape, windows in shapes.items():
        print(f"\n=== {shape}: "
              + " -> ".join(f"{s}..{e}" for s, e in windows) + " ===")
        print(f"{'policy':<12} {'decodes':>8} {'seeks':>6} {'wall_s':>7} "
              f"{'resident':>9} {'runs':>5}   (medians)")
        collected = {name: [] for name in POLICIES}
        for _rep in range(REPS):
            for name in POLICIES:
                collected[name].append(
                    run_arm(name, width, height, windows, ceiling))
        for name in POLICIES:
            finals = [got["legs"][-1] for got in collected[name]]
            walls = [f["wall_s"] for f in finals]
            decodes = [f["decodes"] for f in finals]
            seeks = [f["seeks"] for f in finals]
            resident = [f["resident_on_arrival"] for f in finals]
            runs_ = [f["runs_on_arrival"] for f in finals]
            print(f"{name:<12} {_med(decodes):>8} {_med(seeks):>6} "
                  f"{_med(walls):>7} {_med(resident):>9} {_med(runs_):>5}   "
                  f"walls {walls}")
            run.note(
                f"{shape} / {name}: return leg decoded {decodes} of {WINDOW} "
                f"rows over {REPS} repeats, walls {walls} s, seeks {seeks}; "
                f"rows already resident on arrival {resident}, in {runs_} "
                f"contiguous run(s).")
            run.cases.append(harness.Case(
                name=f"{shape}-{name}",
                params={"shape": shape, "policy": name, "repeats": REPS,
                        "return_decodes": decodes, "return_seeks": seeks,
                        "return_wall_s": walls,
                        "resident_on_arrival": resident,
                        "runs_on_arrival": runs_,
                        "legs": [g["legs"] for g in collected[name]],
                        "window": WINDOW, "ceiling_bytes": ceiling},
                samples_ms=[], unit="see params",
                note="the third leg is the result; the first two set it up"))

    run.write()


if __name__ == "__main__":
    main()
