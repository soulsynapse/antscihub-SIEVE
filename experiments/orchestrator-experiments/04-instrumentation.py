"""Is the timing envelope cheap enough to leave on in the interactive loop?

Two questions:

1. **Wrapping overhead.** An Envelope open/close/record around a simulated
   frame serve, against the same serve with no envelope. The serve itself
   is a dict lookup (the hot path in the store), so the envelope's cost is
   measured against the cheapest thing it would wrap.

2. **Duration bar accuracy.** A three-node graph where each node does a
   known amount of work (sleep for a controlled duration). The duration
   bars should recover each node's fraction of the total to within the
   timer's resolution. The unattributed remainder — wall time minus the
   sum of all envelopes — should be small and stable.

The experiment uses `time.perf_counter` rather than real decode because it
tests the instrumentation, not the decode. What matters is the overhead of
the bookkeeping against a real operation's cost, and whether the bars add
up.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))

import harness
from graph import Envelope, Graph, Need, Urgency

harness.RESULTS = Path(__file__).resolve().parent / "results"

SWEEP = 2000


def time_wrapping_overhead(run: harness.Run) -> None:
    """Envelope open/close/record vs bare dict lookup."""
    g = Graph()
    store: dict[int, bytes] = {i: b"x" for i in range(SWEEP)}

    def with_envelope():
        for i in range(SWEEP):
            env = Envelope("test", i, "gray", "held").open()
            _ = store.get(i)
            env.close()
            g.record(env)
            yield i

    harness.time_case(
        run, "dict-lookup-with-envelope",
        with_envelope,
        params={"sweep": SWEEP},
        unit="ms per lookup",
    )
    harness.report(run.cases[-1])

    def without_envelope():
        for i in range(SWEEP):
            _ = store.get(i)
            yield i

    harness.time_case(
        run, "dict-lookup-bare",
        without_envelope,
        params={"sweep": SWEEP},
        unit="ms per lookup",
    )
    harness.report(run.cases[-1])


def time_duration_bar_accuracy(run: harness.Run) -> None:
    """Three nodes with controlled durations — do the bars recover them?"""
    g = Graph()

    # node A: ~60% of work, node B: ~30%, node C: ~10%
    durations_us = {"heavy": 600, "medium": 300, "light": 100}
    reps = 200

    wall_start = time.perf_counter()

    for rep in range(reps):
        for node_id, us in durations_us.items():
            env = Envelope(node_id, rep, "gray", "held").open()
            # busy-wait for controlled duration (sleep is too coarse)
            target = time.perf_counter() + us / 1_000_000
            while time.perf_counter() < target:
                pass
            env.close()
            g.record(env)

    wall_end = time.perf_counter()
    wall_ms = (wall_end - wall_start) * 1000.0

    bars = g.duration_bars()
    by_node = g.timings_by_node()
    node_totals = {nid: sum(e.ms for e in envs) for nid, envs in by_node.items()}
    envelope_total = sum(node_totals.values())
    remainder_ms = wall_ms - envelope_total

    expected_fractions = {}
    total_us = sum(durations_us.values())
    for nid, us in durations_us.items():
        expected_fractions[nid] = us / total_us

    print("  duration bars:")
    for nid in sorted(bars):
        expected = expected_fractions.get(nid, 0)
        actual = bars[nid]
        err = abs(actual - expected)
        print(f"    {nid:>8}: expected={expected:.3f}  actual={actual:.3f}  err={err:.3f}")

    print(f"  wall={wall_ms:.1f} ms, envelopes={envelope_total:.1f} ms, "
          f"remainder={remainder_ms:.1f} ms ({remainder_ms/wall_ms*100:.1f}%)")

    run.note(f"duration bars: {bars}")
    run.note(f"expected fractions: {expected_fractions}")
    run.note(f"wall={wall_ms:.1f} ms, envelopes={envelope_total:.1f} ms, "
             f"remainder={remainder_ms:.1f} ms ({remainder_ms/wall_ms*100:.1f}%)")

    max_err = max(abs(bars.get(nid, 0) - expected_fractions[nid])
                  for nid in durations_us)
    case = harness.Case(
        "duration-bar-accuracy",
        params={"reps": reps, "nodes": len(durations_us),
                "durations_us": durations_us},
        samples_ms=[max_err * 1000],  # store the error as the sample
        unit="max fraction error (x1000)",
        note=f"remainder={remainder_ms:.1f}ms ({remainder_ms/wall_ms*100:.1f}%)",
    )
    run.cases.append(case)


def main() -> None:
    run = harness.Run(
        experiment="04-instrumentation",
        question=(
            "Is the timing envelope cheap enough to leave on, and do the "
            "duration bars recover each node's fraction of the total?"
        ),
    )

    print("04 — instrumentation")
    print()

    print("wrapping overhead:")
    time_wrapping_overhead(run)
    print()

    print("duration bar accuracy:")
    time_duration_bar_accuracy(run)
    print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
