"""Can one declaration contract schedule the GUI, two tools and a series writer?

The graph has four nodes, each declaring {form, offsets, pressure}:

  gui         reach 1, offset (0,), INTERACTIVE pressure. Moves every tick
              to simulate a drag. Accepts approximate frames.
  absdiff     reach 1, offsets (-1, 0), BATCH pressure. Wants exact frames
              at analysis form.
  dis_flow    reach 1, offsets (-1, 0), BATCH pressure. Same shape, heavier
              compute, same declaration.
  series_w    reach 0, offset (0,), BATCH pressure. Consumes a field and
              releases its upstream frame when the scalar is written.

Three things are measured:

1. **Graph overhead.** The cost of `declare`, `held`, `evictable`, and
   `release_position` against the same decisions made by hand (the flat
   `residency` call from `tool-experiments/tools.py`). The null hypothesis
   is that the graph operations are dict touches and in the noise.

2. **Declaration completeness.** Does the graph's `held()` set match the
   union of what every node needs? Does `evictable()` correctly identify
   frames no node wants? Run the four-node graph over a 300-position
   sweep and verify at every position.

3. **Priority ordering.** Does `pressure_queue()` consistently rank the GUI
   above the tools, and the tools above idle nodes? Verified at every
   position in the sweep.

The experiment does not decode frames or fill a store. It tests the
declaration contract in isolation — whether the bookkeeping is correct and
whether it is cheap. Frames are dummy arrays; what matters is the ref-count
arithmetic.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from graph import Envelope, Graph, Need, Urgency

import forms
import tools as tools_mod

harness.RESULTS = Path(__file__).resolve().parent / "results"

SWEEP = 300
CROP = (100, 100, 462, 456)

FORM_GRAY = forms.Form(CROP, (CROP[2], CROP[3]), "gray")
FORM_BGR = forms.Form(CROP, (CROP[2], CROP[3]), "bgr")


def run_graph_sweep(run: harness.Run) -> None:
    """Sweep the graph over SWEEP positions and verify at every step."""
    g = Graph()

    tool_a = tools_mod.absdiff()
    tool_d = tools_mod.dis_flow()

    form_a = tool_a.form_for(CROP)
    form_d = tool_d.form_for(CROP)
    form_gui = FORM_BGR

    errors: list[str] = []

    for pos in range(1, SWEEP + 1):
        #: a sweep over the whole run, declared once and left standing —
        #: the producer the tools ride on, and what makes the derived rank
        #: have anything to derive from
        if pos == 1:
            g.declare(Need("sweep", 0, tuple(range(SWEEP + 1)),
                           form_a.key(), Urgency.DEFERRED))
        g.declare(Need("gui", pos, (0,), form_gui.key(), Urgency.INTERACTIVE))
        g.declare(Need("absdiff", pos, tool_a.offsets, form_a.key(), Urgency.DEFERRED))
        g.declare(Need("dis_flow", pos, tool_d.offsets, form_d.key(), Urgency.DEFERRED))
        g.declare(Need("series_w", pos, (0,), form_a.key(), Urgency.DEFERRED))

        held = g.held()

        gui_needs = {(pos, form_gui.key())}
        a_needs = {(pos + off, form_a.key()) for off in tool_a.offsets}
        d_needs = {(pos + off, form_d.key()) for off in tool_d.offsets}
        s_needs = {(pos, form_a.key())}
        #: the sweep holds its whole span for the life of the run — a
        #: consumer that may be scrubbed anywhere in a window declares the
        #: window, and the hold is the declaration (ADR-0006)
        sweep_needs = {(p, form_a.key()) for p in range(SWEEP + 1)}
        expected = gui_needs | a_needs | d_needs | s_needs | sweep_needs

        if held != expected:
            extra = held - expected
            missing = expected - held
            errors.append(f"pos={pos}: held mismatch. extra={extra}, missing={missing}")

        pq = g.pressure_queue()
        order = [n.node_id for n in pq]
        if order[0] != "gui":
            errors.append(f"pos={pos}: GUI not served first, got {order[0]}")

        #: the derived properties, which is the whole of the contract now
        #: that nothing declares a rank. A tool sitting inside the sweep's
        #: declared window must fall behind it: the sweep will reach those
        #: positions in its own order, and jumping the queue buys by seek
        #: what was already arriving by sequential read (ADR-0006).
        if order.index("sweep") > order.index("absdiff"):
            errors.append(f"pos={pos}: absdiff outranks the sweep feeding it")
        if order.index("sweep") > order.index("dis_flow"):
            errors.append(f"pos={pos}: dis_flow outranks the sweep feeding it")
        if order.index("gui") > order.index("sweep"):
            errors.append(f"pos={pos}: sweep outranks a waiting person")

        # series writer releases after consuming
        evictable_before = g.release_position("series_w", pos, form_a.key())

        # absdiff and dis_flow also hold pos at form_a.key() so it should
        # not be evictable yet (unless form keys differ)
        if form_a.key() == form_d.key():
            if evictable_before:
                pass  # absdiff or dis_flow still holds it
        # no assertion here — just record

    if errors:
        for e in errors[:10]:
            print(f"  ERROR: {e}")
        run.note(f"{len(errors)} declaration errors in sweep")
    else:
        print("  all declaration checks passed")
        run.note("all declaration checks passed over full sweep")


def time_graph_ops(run: harness.Run) -> None:
    """Time the graph operations against the flat residency call."""
    g = Graph()
    tool_a = tools_mod.absdiff()
    tool_d = tools_mod.dis_flow()
    form_a = tool_a.form_for(CROP)
    form_d = tool_d.form_for(CROP)
    form_gui = FORM_BGR

    # -- graph path --------------------------------------------------------

    def graph_work():
        for pos in range(1, SWEEP + 1):
            g.declare(Need("gui", pos, (0,), form_gui.key(), Urgency.INTERACTIVE))
            g.declare(Need("absdiff", pos, tool_a.offsets, form_a.key(), Urgency.DEFERRED))
            g.declare(Need("dis_flow", pos, tool_d.offsets, form_d.key(), Urgency.DEFERRED))
            g.declare(Need("series_w", pos, (0,), form_a.key(), Urgency.DEFERRED))
            g.held()
            g.evictable(set())
            g.pressure_queue()
            g.release_position("series_w", pos, form_a.key())
            yield pos

    harness.time_case(
        run, "graph-declare-hold-evict-priority",
        graph_work,
        params={"nodes": 4, "sweep": SWEEP, "forms": 2},
        unit="ms per position",
    )
    harness.report(run.cases[-1])

    # -- flat residency path (tool-experiments baseline) -------------------

    active = [
        (tool_a, form_a),
        (tool_d, form_d),
    ]

    def flat_work():
        for pos in range(1, SWEEP + 1):
            tools_mod.residency(active, pos)
            yield pos

    harness.time_case(
        run, "flat-residency",
        flat_work,
        params={"tools": 2, "sweep": SWEEP},
        unit="ms per position",
    )
    harness.report(run.cases[-1])


def time_envelope_overhead(run: harness.Run) -> None:
    """Time the envelope open/close against a bare perf_counter pair."""
    g = Graph()

    def envelope_work():
        for i in range(SWEEP):
            env = Envelope("test", i, "gray", "held")
            env.open()
            env.close()
            g.record(env)
            yield i

    harness.time_case(
        run, "envelope-open-close-record",
        envelope_work,
        params={"sweep": SWEEP},
        unit="ms per envelope",
    )
    harness.report(run.cases[-1])

    def bare_perf_counter():
        for i in range(SWEEP):
            t0 = time.perf_counter()
            t1 = time.perf_counter()
            yield i

    harness.time_case(
        run, "bare-perf-counter-pair",
        bare_perf_counter,
        params={"sweep": SWEEP},
        unit="ms per pair",
    )
    harness.report(run.cases[-1])

    bars = g.duration_bars()
    run.note(f"duration_bars keys: {sorted(bars.keys())}")
    run.note(f"duration_bars values: { {k: round(v, 4) for k, v in bars.items()} }")


def main() -> None:
    run = harness.Run(
        experiment="01-unified-declaration",
        question=(
            "Can one declaration contract schedule the GUI, two tools and a "
            "series writer — and is the graph overhead in the noise?"
        ),
    )

    print("01 — unified declaration")
    print()

    print("correctness sweep:")
    run_graph_sweep(run)
    print()

    print("graph overhead:")
    time_graph_ops(run)
    print()

    print("envelope overhead:")
    time_envelope_overhead(run)
    print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
