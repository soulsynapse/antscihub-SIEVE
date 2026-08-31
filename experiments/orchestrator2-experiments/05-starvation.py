"""Does ranking for locality starve the node it ranks last, and does a deadline fix it?

Not one of the README's numbered questions — a defect and its repair, measured
because the repair is a scheduling mechanism and an unmeasured one is a story.

`Graph.pressure_queue` ranks by urgency, then by subsumption, then by span.
The subsumption rule is anticipatory scheduling (prior art: Iyer & Druschel,
SOSP 2001): a narrow DEFERRED need lying inside a wider one yields, because
the wide declaration is a producer sweeping toward that row and jumping the
queue buys by seek what a sequential read was about to deliver. That half was
carried from V1 and is measured — `2026.08.30-the-pressure-dispatcher-preempts-
into-seeks`.

**The half that was missing is the deadline.** Ranking for locality is exactly
what starves whoever ranks last, which is why every scheduler in that family
pairs the locality heuristic with an expiry queue: Linux's anticipatory
scheduler and its descendants (deadline, BFQ) guarantee a request eventually
runs however much better-ranked traffic keeps arriving. SIEVE's queue had the
heuristic and no guarantee, so a DEFERRED need behind a person who never stops
scrubbing was never picked at all.

`Mode.ORDERED` makes that visible rather than merely slow, which is why it is
the probe here: an ordered node runs the lowest row it has been armed for, so
one unserved row stops every later row of that node with their inputs pinned.
Under PARALLEL the same starvation is a node that quietly falls behind.

## The workload

Synthetic, and deliberately so — no footage, a fetcher that sleeps 2 ms per
frame. What is being measured is which declaration the scheduler picks, and a
real decoder would add a seek/step distribution on top of an effect that is
about ordering. The footage-backed version of this question is what the
explorer's legs are for.

  ordered node   60 rows armed at once, `Mode.ORDERED`, DEFERRED.
  the person     a wide INTERACTIVE declaration that keeps moving — 40 rows,
                 re-declared every 20 ms at a new position. It is always
                 unserved, always outranks, and is never subsumed, so it wins
                 every pick the ranking makes. This is a scrub that does not
                 stop, which is a real thing a person does.

## The arms

  no deadline    `deadline_s=0`, the expiry queue disabled. What the ranking
                 does unaided.
  deadline       `deadline_s` set, expiry measured against **last service**
                 and drained in a batch.

The deadline is measured from when a node was last served rather than from
when it declared. A first version aged the declaration itself, which is wrong
for a standing declaration over a window: a sweep declares once and is then
permanently older than any deadline, so it wins every pick and the expiry
queue replaces the ranking instead of rescuing it. That version took 976 of
1071 picks; this one takes about a twentieth as many and is reported so the
difference between a floor and a takeover is legible.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))

import harness

from dispatcher import Dispatcher, Mode, Reason
from graph import Graph, Need, Urgency
from pool import Pool

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 60              #: rows the ordered node arms up front
SECONDS = 3.0          #: how long each arm runs
FRAME_MS = 0.002       #: what the fake fetcher charges per frame
SCRUB_SPAN = 40        #: rows the person's declaration covers
SCRUB_EVERY = 0.02     #: how often it moves
DEADLINE_S = 0.3       #: short, so three seconds contains several expiries


class SlowFetcher:
    """A decoder that costs time and nothing else. No seeks, no footage:
    what varies here is which declaration is picked, not what a pick costs."""

    def __init__(self) -> None:
        self.n = 0

    def exact(self, idx: int):
        self.n += 1
        time.sleep(FRAME_MS)
        return np.full((4, 4), idx % 256, np.uint8), "step"

    def close(self) -> None:
        pass


def run_arm(deadline_s: float) -> dict:
    graph = Graph()
    pool = Pool(graph, budget_bytes=1 << 30)
    dispatcher = Dispatcher(graph, pool, "F", lambda _band: SlowFetcher(), recorders=2,
                            readers=1, deadline_s=deadline_s)
    dispatcher.set_mode("ord", Mode.ORDERED)
    dispatcher.start()
    computed: list[int] = []

    def activate(reason: Reason, ctx) -> None:
        if reason is Reason.INITIAL:
            ctx.request(ctx.row)
            return
        ctx.get(ctx.row)
        computed.append(ctx.row)
        ctx.release()

    for row in range(ROWS):
        dispatcher.get_frame("ord", row, activate, Urgency.DEFERRED, "F",
                             supersedes=False)

    stop = threading.Event()

    def scrub() -> None:
        step = 0
        while not stop.is_set():
            graph.declare(Need("gui", 10_000 + step * 7,
                               tuple(range(SCRUB_SPAN)), "F",
                               Urgency.INTERACTIVE))
            step += 1
            time.sleep(SCRUB_EVERY)

    hand = threading.Thread(target=scrub, daemon=True)
    hand.start()
    time.sleep(SECONDS)
    stop.set()
    hand.join(2)

    stats = dispatcher.stats()
    dispatcher.stop()
    return {"deadline_s": deadline_s,
            "ordered_rows_computed": len(computed),
            "ordered_rows_armed": ROWS,
            "expired_picks": stats["expired_picks"],
            "total_decodes": stats["served"],
            "expired_share": (round(stats["expired_picks"]
                                    / stats["served"], 4)
                              if stats["served"] else None),
            "dispatcher": stats}


def main() -> None:
    run = harness.Run(
        experiment="05-starvation",
        question="Does ranking for locality starve the node it ranks last, "
                 "and does an expiry deadline fix it without taking over?")
    run.note("synthetic: no footage, a fetcher charging "
             f"{FRAME_MS * 1000:.0f} ms a frame and nothing else. What is "
             "measured is which declaration the scheduler picks; a real "
             "decoder would lay a seek/step distribution over an effect "
             "that is about ordering.")
    run.note(f"topology: one ORDERED node arming {ROWS} rows at once at "
             f"DEFERRED, against a person scrubbing without pause — a "
             f"{SCRUB_SPAN}-row INTERACTIVE declaration re-stated every "
             f"{SCRUB_EVERY * 1000:.0f} ms at a new position, so it is always "
             f"unserved and always outranks. {SECONDS} s per arm.")
    run.note("prior art: the subsumption rule this starves under is "
             "anticipatory scheduling (Iyer & Druschel, SOSP 2001); the "
             "expiry queue that repairs it is the deadline family's "
             "anti-starvation half, drained in a batch after `fifo_batch`.")

    rows = []
    for deadline in (0.0, DEADLINE_S):
        got = run_arm(deadline)
        rows.append(got)
        label = "no deadline" if deadline == 0 else f"deadline {deadline}s"
        print(f"{label:<16} ordered {got['ordered_rows_computed']:>3}/{ROWS} "
              f"rows   expired_picks {got['expired_picks']:>4}   "
              f"decodes {got['total_decodes']:>5}   "
              f"expiry share {got['expired_share']}")
        run.note(f"arm {label}: the ordered node computed "
                 f"{got['ordered_rows_computed']} of {ROWS} armed rows; the "
                 f"expiry queue made {got['expired_picks']} of "
                 f"{got['total_decodes']} picks "
                 f"({got['expired_share']}).")
        run.cases.append(harness.Case(
            name=label.replace(" ", "-"), params=got, samples_ms=[],
            unit="see params",
            note=("the ranking unaided" if deadline == 0 else
                  "expiry measured against last service, drained in a batch")))

    without, with_ = rows[0], rows[1]
    run.note(f"result: {without['ordered_rows_computed']}/{ROWS} rows without "
             f"a deadline against {with_['ordered_rows_computed']}/{ROWS} "
             f"with one, and the expiry queue took "
             f"{with_['expired_share']} of picks doing it — a floor under "
             f"service, not a replacement for the ranking.")
    run.write()


if __name__ == "__main__":
    main()
