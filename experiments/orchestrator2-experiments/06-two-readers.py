"""Does a second cursor let the fill and the person overlap, or only stop them fighting?

`2026.08.30-a-second-cursor-makes-preemption-free` established, on V1's
explorer, that the seek pair a preemption costs is one cursor being taken from
the sweep rather than the price of serving a person: given its own cursor, the
alternations still happen and stop mattering, and a live playhead costs what a
parked one costs. Its companion,
`2026.08.30-the-remaining-wall-is-decode-and-a-reader-that-does-not-overlap`,
then found the ceiling that result stopped at — **the wall is `fill + gui`, not
`max(fill, gui)`**, because V1 has one dispatcher thread and `exact()` blocks it
whichever container it is holding. That finding puts the unclaimed term at about
a third of a filled window and calls the overlap a lead rather than a result,
because nothing there ran two readers concurrently.

V2 can. `Dispatcher(readers=N)` gives each fetch thread its own `Fetcher` and
partitions the bands: reader 0 never touches an INTERACTIVE pick, so the
sequential cursor is never moved by a person, and readers 1 and above serve
only what a person is waiting on. Claims stop two readers decoding one row.
This is the experiment that says whether the overlap is really there.

## The workload

A window fill against a person who will not sit still — V1's `--live-playhead`
condition, headless, with the playhead scrubbing rather than advancing.
Advancing by one is the cheap case and the same finding says why: the fetcher
*steps*, so a smooth transport barely preempts. A gaussian random walk is what
makes the GUI's decodes seeks, which is what makes the two readers contend for
something.

    sweep      the whole window, attention-first from the anchor, DEFERRED
    playhead   one INTERACTIVE row at a time, re-declared on a random walk
               every `SCRUB_EVERY`, superseding its own previous request

## The arms

  readers=1   V2's default and V1's shape: one cursor, one thread, bands
              unpartitioned. The baseline the walls elsewhere in this folder
              were taken at.
  readers=2   a cursor per band. The sweep's is never taken; the person's
              never has to rejoin a sequential run.

## Pre-registered

- **If the fill wall falls toward what a parked playhead costs**, the overlap
  is real and the term the decode-budget finding priced is collectible. The
  second cursor stops the fighting *and* buys the concurrency, and V2's core
  shape should be two readers.
- **If the fill wall does not move but the GUI's wait does**, the second
  cursor is a latency mechanism and not a throughput one: the person is served
  sooner and the fill is no faster, which would mean the two readers still
  serialise somewhere — the pool lock, the graph lock, or the GIL — and the
  thing to find is where.
- **If neither moves**, the partition is doing nothing this workload can see,
  and `readers` is a parameter with one useful value until a workload that
  needs it turns up.

Both numbers are reported for both arms, because the second outcome is only
distinguishable from the first if the GUI's wait is measured beside the fill's
wall rather than instead of it.
"""

from __future__ import annotations

import random
import sys
import threading
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
from dispatcher import Dispatcher, Reason
from fetch import Fetcher
from graph import Graph, Urgency
from nodes import Sweep
from pool import Pool

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
WINDOW = 160
POOL_BUDGET = 12 << 30
SCRUB_EVERY = 0.05      #: how often the playhead moves
SCRUB_SIGMA = 8.0       #: the walk's step, in rows. V1's `_walk_scrub` shape.
SCRUB_JUMP = 0.12       #: chance of re-anchoring somewhere else entirely
COVER_TIMEOUT_S = 240.0
REPS = 3
SEED = 7                #: the same walk for every arm, so the person is not
                        #: a variable


def _open_total():
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
        return total - GOP, stream.width, stream.height, float(
            stream.average_rate)


def _seeks_by_role(trace) -> dict[str, int]:
    out: dict[str, int] = {}
    for _t, role, _row, how, _ms in trace:
        if how == "seek":
            out[role] = out.get(role, 0) + 1
    return out


def run_arm(readers: int, width: int, height: int, start: int, end: int,
            parked: bool) -> dict:
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    form_key = source_form.key()
    dispatcher = Dispatcher(graph, pool, form_key, lambda _band: Fetcher(BIG),
                            recorders=2, readers=readers)

    waits: list[float] = []
    shown = {"n": 0}
    lock = threading.Lock()

    def activate(reason: Reason, ctx) -> None:
        if reason is Reason.INITIAL:
            ctx.request(ctx.row)
            return
        ctx.get(ctx.row)
        with lock:
            waits.append(ctx.wait_ms)
            shown["n"] += 1
        #: the viewer does not release: its declaration is the hold on the
        #: frame it is showing, until it declares somewhere else.

    stop = threading.Event()

    def playhead() -> None:
        rng = random.Random(SEED)
        anchor = rng.randrange(start, end)
        while not stop.is_set():
            if rng.random() < SCRUB_JUMP:
                anchor = rng.randrange(start, end)
            row = max(start, min(end - 1,
                                 round(rng.gauss(anchor, SCRUB_SIGMA))))
            dispatcher.get_frame("gui", row, activate, Urgency.INTERACTIVE,
                                 form_key, supersedes=True)
            time.sleep(SCRUB_EVERY)

    dispatcher.start()
    anchor = start + (end - start) // 2
    sweep = Sweep(start, end, anchor, form_key, graph)
    hand = None
    t0 = time.perf_counter()
    sweep.declare()
    if not parked:
        hand = threading.Thread(target=playhead, daemon=True)
        hand.start()
    covered = False
    deadline = time.perf_counter() + COVER_TIMEOUT_S
    while time.perf_counter() < deadline:
        if len(pool.covered(start, end, form_key)) >= end - start:
            covered = True
            break
        time.sleep(0.01)
    wall = time.perf_counter() - t0
    stop.set()
    if hand is not None:
        hand.join(2)
    stats = dispatcher.stats()
    seeks = _seeks_by_role(dispatcher.trace)
    ordered = sorted(waits)
    dispatcher.stop()
    return {
        "readers": readers,
        "parked": parked,
        "covered": covered,
        "fill_wall_s": round(wall, 3),
        "decodes": stats["served"],
        "seeks_total": stats["seeks"],
        "seeks_by_role": seeks,
        "by_pressure": stats["by_pressure"],
        "stale": stats["stale"],
        "superseded": stats["superseded"],
        "gui_shown": shown["n"],
        "gui_wait_ms_p50": (round(ordered[len(ordered) // 2], 2)
                            if ordered else None),
        "gui_wait_ms_p95": (round(ordered[int(len(ordered) * 0.95)], 2)
                            if ordered else None),
        "expired_picks": stats["expired_picks"],
    }


def _med(values):
    ordered = sorted(v for v in values if v is not None)
    return ordered[len(ordered) // 2] if ordered else None


def main() -> None:
    total, width, height, fps = _open_total()
    start = total // 3
    end = min(start + WINDOW, total)

    run = harness.Run(
        experiment="06-two-readers",
        question="Does a second cursor let the fill and the person overlap, "
                 "or only stop them fighting?")
    run.add_footage(BIG)
    run.note(f"topology: source -> pool -> {{sweep declaring rows "
             f"{start}..{end} attention-first from the midpoint at DEFERRED; "
             f"a playhead declaring one INTERACTIVE row at a time on a "
             f"gaussian random walk (sigma {SCRUB_SIGMA} rows, "
             f"{SCRUB_JUMP:.0%} chance of re-anchoring) every "
             f"{SCRUB_EVERY * 1000:.0f} ms, superseding its own previous "
             f"request}}. Seed {SEED}, so the person is the same in every "
             f"arm.")
    run.note("core shape: the reader count is the arm; 2 recorder threads, "
             "request depth not used (no step), DropAll replacement. With "
             "two readers the bands partition — reader 0 never takes an "
             "INTERACTIVE pick, so the sequential cursor is never moved by a "
             "person.")
    run.note("a parked arm at each reader count gives the floor: what the "
             "fill costs with nobody declaring, which is what the second "
             "cursor is trying to get back to.")
    run.note(f"{REPS} interleaved repeats; this machine drifts by more than "
             f"small differences and one run per arm has misread that twice "
             f"in this folder.")

    arms = [(1, True), (2, True), (1, False), (2, False)]
    collected: dict[str, list[dict]] = {}
    for _rep in range(REPS):
        for readers, parked in arms:
            key = f"readers{readers}-{'parked' if parked else 'live'}"
            collected.setdefault(key, []).append(
                run_arm(readers, width, height, start, end, parked))

    print(f"\n{'arm':<20} {'fill_s':>7} {'decodes':>8} {'seeks':>6} "
          f"{'gui_p50':>8} {'gui_p95':>8} {'shown':>6} {'stale':>6}")
    for key, runs in collected.items():
        walls = [r["fill_wall_s"] for r in runs]
        print(f"{key:<20} {_med(walls):>7} "
              f"{_med([r['decodes'] for r in runs]):>8} "
              f"{_med([r['seeks_total'] for r in runs]):>6} "
              f"{str(_med([r['gui_wait_ms_p50'] for r in runs])):>8} "
              f"{str(_med([r['gui_wait_ms_p95'] for r in runs])):>8} "
              f"{_med([r['gui_shown'] for r in runs]):>6} "
              f"{_med([r['stale'] for r in runs]):>6}   walls {walls}")
        run.note(
            f"arm {key}: fill wall {walls} s; decodes "
            f"{[r['decodes'] for r in runs]}; seeks by role "
            f"{[r['seeks_by_role'] for r in runs]}; GUI wait p50 "
            f"{[r['gui_wait_ms_p50'] for r in runs]} ms p95 "
            f"{[r['gui_wait_ms_p95'] for r in runs]} ms over "
            f"{[r['gui_shown'] for r in runs]} shown; stale "
            f"{[r['stale'] for r in runs]}, superseded "
            f"{[r['superseded'] for r in runs]}.")
        run.cases.append(harness.Case(
            name=key,
            params={"repeats": REPS, "runs": runs, "window": WINDOW},
            samples_ms=[], unit="see params",
            note="fill wall is the headline; the GUI wait is what "
                 "distinguishes a latency win from a throughput one"))

    run.write()


if __name__ == "__main__":
    main()
