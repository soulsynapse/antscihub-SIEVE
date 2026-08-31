"""Does the fill fall progressively further behind a playhead, and does a second cursor break the loop?

A driven session reported lag that **got worse the longer it played**, which is
a different complaint from lag and has a different cause. Steady lag is a cost;
lag that grows is a feedback loop, and this measures whether there is one.

The loop the log suggests: with one cursor, a playhead that misses preempts the
fill, which costs a seek out and a seek back
(`2026.08.30-the-pressure-dispatcher-preempts-into-seeks`). While the fill is
seeking it delivers nothing, so the playhead — advancing at the frame rate
regardless — gets further ahead of the frontier, so the next tick misses too.
More misses steal the cursor more often, the fill delivers less, and the gap
widens. Nothing in that story is about a slow path; every part of it is about
the fill never being allowed to get in front.

The evidence it came from: a twenty-second hand-driven session
(`explorer-logs/orchestrator2-20260831T003948Z.json`) spent 11.2 s of 19.8 in
seek latency, took 21 fill seeks against 15 the GUI caused — the seek-pair
signature — and ended with **25 frames resident** against a 480-row
declaration, having decoded 422 for the fill.

## What is measured

Not a wall. The wall for a fill is `2026.08.30-a-second-cursor-that-overlaps-
costs-a-scrub-nothing`'s question and is answered. What matters here is a
*trajectory*: at every sample, how far the resident frontier is ahead of the
playhead, and whether the playhead's own row is resident. Reported per
five-second bucket, because a number that is fine at the start and bad at the
end is the whole claim.

  hit rate     of the playhead's ticks in this bucket, how many found their
               row already resident. Falling across buckets is the loop.
  ahead        resident rows between the playhead and the end of the window —
               how much runway the fill has built. Going to zero and staying
               there is the loop having closed.

## The arms

  readers=1    one cursor, bands unpartitioned. The explorer's old default and
               what the driven session ran.
  readers=2    a cursor per band; the fill's is never taken.

Pre-registered: if the one-reader hit rate falls across buckets while the
two-reader one does not, the complaint is the feedback loop and the partition
is the fix. If both fall, the fill is simply too slow for the frame rate here
and the answer is a smaller window or a coarser form, not a cursor. If neither
falls, this is not the mechanism and the driven session's lag is still
unexplained — which would be worth knowing before anything else is changed.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import av

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
WINDOW = 480            #: the explorer's full-size window
POOL_BUDGET = 12 << 30
SECONDS = 30.0          #: long enough for several buckets
BUCKET_S = 5.0
FPS = 23.976
REPS = 2


def _open_total():
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
        return total - GOP, stream.width, stream.height


def run_arm(readers: int, width: int, height: int, start: int,
            end: int) -> dict:
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    form_key = source_form.key()
    dispatcher = Dispatcher(graph, pool, form_key, lambda _band: Fetcher(BIG),
                            recorders=2, readers=readers)

    ticks: list[tuple[float, int, bool, int]] = []
    lock = threading.Lock()
    stop = threading.Event()

    def activate(reason: Reason, ctx) -> None:
        if reason is Reason.INITIAL:
            ctx.request(ctx.row)
            return
        ctx.get(ctx.row)
        #: no release: a viewer's declaration is the hold on what is on
        #: screen, exactly as in the explorer.

    def playhead() -> None:
        """Advance one row per frame period, wrapping. The cheap case — a
        transport that moves smoothly is what the fetcher can *step* for, so
        any trouble here is not the hand being erratic."""
        row = start
        t0 = time.perf_counter()
        while not stop.is_set():
            resident = pool.has(row, form_key)
            #: runway: resident rows from the playhead to the window's end
            ahead = 0
            while pool.has(row + ahead, form_key) and row + ahead < end:
                ahead += 1
            with lock:
                ticks.append((time.perf_counter() - t0, row, resident, ahead))
            dispatcher.get_frame("gui", row, activate, Urgency.INTERACTIVE,
                                 form_key, supersedes=True)
            row = row + 1 if row + 1 < end else start
            time.sleep(1.0 / FPS)

    dispatcher.start()
    sweep = Sweep(start, end, start, form_key, graph)
    sweep.declare()
    hand = threading.Thread(target=playhead, daemon=True)
    hand.start()
    time.sleep(SECONDS)
    stop.set()
    hand.join(2)
    stats = dispatcher.stats()
    covered = len(pool.covered(start, end, form_key))
    dispatcher.stop()

    buckets: dict[int, list[tuple[bool, int]]] = {}
    for when, _row, resident, ahead in ticks:
        buckets.setdefault(int(when // BUCKET_S), []).append((resident, ahead))
    per_bucket = []
    for index in sorted(buckets):
        rows = buckets[index]
        per_bucket.append({
            "bucket_s": index * BUCKET_S,
            "ticks": len(rows),
            "hit_rate": round(sum(1 for r, _a in rows if r) / len(rows), 3),
            "ahead_p50": sorted(a for _r, a in rows)[len(rows) // 2],
        })
    return {"readers": readers, "buckets": per_bucket,
            "covered_at_end": covered, "window": WINDOW,
            "dispatcher": stats}


def main() -> None:
    total, width, height = _open_total()
    start = total // 3
    end = start + WINDOW

    run = harness.Run(
        experiment="07-playback-divergence",
        question="Does the fill fall progressively further behind a playhead, "
                 "and does a cursor per band break the loop?")
    run.add_footage(BIG)
    run.note(f"topology: source -> pool -> {{sweep declaring a {WINDOW}-row "
             f"window from its start; a playhead advancing one row per frame "
             f"period at {FPS} fps, wrapping, superseding its own previous "
             f"request}}. The reader count is the arm. {SECONDS} s per arm, "
             f"bucketed at {BUCKET_S} s.")
    run.note("the playhead advances by one rather than scrubbing, which is "
             "the cheap case: a smooth transport is what the fetcher can step "
             "for, so trouble here is not the hand being erratic.")
    run.note("this measures a trajectory and not a wall. A hit rate that "
             "falls across buckets is a feedback loop; one that is merely low "
             "is a fill too slow for the frame rate, which is a different "
             "problem with a different fix.")

    for rep in range(REPS):
        for readers in (1, 2):
            got = run_arm(readers, width, height, start, end)
            line = "  ".join(
                f"{b['bucket_s']:>4.0f}s hit {b['hit_rate']:<5} ahead "
                f"{b['ahead_p50']:>4}" for b in got["buckets"])
            print(f"rep{rep} readers={readers} covered "
                  f"{got['covered_at_end']}/{WINDOW}")
            print(f"        {line}")
            run.note(
                f"rep{rep} readers={readers}: covered "
                f"{got['covered_at_end']}/{WINDOW} at the end; per bucket "
                + "; ".join(f"{b['bucket_s']:.0f}s hit={b['hit_rate']} "
                            f"ahead={b['ahead_p50']}"
                            for b in got["buckets"])
                + f"; seeks {got['dispatcher']['seeks']}, stale "
                f"{got['dispatcher']['stale']}.")
            run.cases.append(harness.Case(
                name=f"rep{rep}-readers{readers}", params=got,
                samples_ms=[], unit="see params",
                note="hit_rate per bucket is the result; a falling series is "
                     "the feedback loop"))

    run.write()


if __name__ == "__main__":
    main()
