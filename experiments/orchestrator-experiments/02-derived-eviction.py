"""Does eviction derived from declarations hold fewer frames than a fixed window?

Two models, same workload:

  fixed       a 300-frame window. Everything inside is held, everything
              outside is dropped. The current model.
  derived     frames held until every declared consumer is past them.
              The window is a consequence of the graph's reaches, not a
              parameter.

The workload: a simulated fill over 600 positions with three consumers —
the GUI at reach 1, `absdiff` at reach 1 (offsets -1,0), and `lag_mhi` at
reach 30 (offsets -30,-20,-10,0). The interesting case is `lag_mhi`: its
reach is 30, but it only needs four positions out of those thirty. The fixed
window holds all 300; the derived model should hold only the union of what
the three consumers declare, which is at most 34 positions (30 + 1 + 0 for
gui + 2 for absdiff, minus overlaps with mhi's set).

Three things are measured:

1. **Peak holds.** The maximum number of (position, form_key) pairs held at
   any point during the sweep, under each model.

2. **Eviction events.** How many frames each model drops over the sweep.
   Derived should evict earlier and more often.

3. **Correctness.** At every position, verify that no consumer's declared
   need is evicted — the invariant the derived model must never violate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from graph import Graph, Need, Urgency

import forms
import tools as tools_mod

harness.RESULTS = Path(__file__).resolve().parent / "results"

SWEEP = 600
CROP = (100, 100, 462, 456)
WINDOW = 300


def run_derived(run: harness.Run) -> None:
    """Sweep with declaration-derived eviction."""
    g = Graph()
    tool_a = tools_mod.absdiff()
    tool_m = tools_mod.lag_mhi()
    form_a = tool_a.form_for(CROP)
    form_m = tool_m.form_for(CROP)
    form_gui = forms.Form(CROP, (CROP[2], CROP[3]), "bgr")

    peak = 0
    evictions = 0
    errors: list[str] = []
    holds_trace: list[int] = []

    # all frames ever "fetched" — the pool eviction draws from
    all_fetched: set[tuple[int, str]] = set()

    for pos in range(max(-min(tool_m.offsets), 1), SWEEP + 1):
        g.declare(Need("gui", pos, (0,), form_gui.key(), Urgency.INTERACTIVE))
        g.declare(Need("absdiff", pos, tool_a.offsets, form_a.key(), Urgency.DEFERRED))
        g.declare(Need("mhi", pos, tool_m.offsets, form_m.key(), Urgency.DEFERRED))
        g.declare(Need("series_w", pos, (0,), form_a.key(), Urgency.DEFERRED))

        # simulate fetching what was just declared
        held = g.held()
        all_fetched |= held

        # series writer releases after consuming
        g.release_position("series_w", pos, form_a.key())

        # evict anything the graph says is free
        can_evict = g.evictable(all_fetched)
        evictions += len(can_evict)
        all_fetched -= can_evict

        current_held = g.held()
        peak = max(peak, len(current_held))
        holds_trace.append(len(current_held))

        # correctness: nothing a consumer needs was evicted
        for nid, need in [("gui", Need("gui", pos, (0,), form_gui.key())),
                          ("absdiff", Need("absdiff", pos, tool_a.offsets, form_a.key())),
                          ("mhi", Need("mhi", pos, tool_m.offsets, form_m.key()))]:
            for p in need.needed_positions():
                key = (p, need.form_key)
                if key not in current_held:
                    errors.append(f"pos={pos}: {nid} needs {key} but not held")

    case = harness.Case(
        "derived-eviction",
        params={
            "sweep": SWEEP, "window": "derived",
            "tools": "absdiff,mhi(30-20-10)", "forms": 2,
        },
        samples_ms=[float(h) for h in holds_trace],
        unit="frames held",
    )
    run.cases.append(case)
    harness.report(case)

    run.note(f"derived: peak={peak}, evictions={evictions}")
    if errors:
        for e in errors[:10]:
            print(f"  ERROR: {e}")
        run.note(f"{len(errors)} eviction correctness errors")
    else:
        print(f"  derived: peak={peak} held, {evictions} evictions, no errors")


def run_fixed(run: harness.Run) -> None:
    """Sweep with fixed-window eviction."""
    tool_a = tools_mod.absdiff()
    tool_m = tools_mod.lag_mhi()
    form_a = tool_a.form_for(CROP)
    form_m = tool_m.form_for(CROP)
    form_gui = forms.Form(CROP, (CROP[2], CROP[3]), "bgr")

    peak = 0
    evictions = 0
    holds_trace: list[int] = []

    held: set[tuple[int, str]] = set()

    for pos in range(max(-min(tool_m.offsets), 1), SWEEP + 1):
        # simulate fetching for all consumers at this position
        gui_needs = {(pos, form_gui.key())}
        a_needs = {(pos + off, form_a.key()) for off in tool_a.offsets}
        m_needs = {(pos + off, form_m.key()) for off in tool_m.offsets}
        held |= gui_needs | a_needs | m_needs

        # fixed window: drop anything more than WINDOW positions back
        before = len(held)
        held = {(p, fk) for p, fk in held if p > pos - WINDOW}
        evictions += before - len(held)

        peak = max(peak, len(held))
        holds_trace.append(len(held))

    case = harness.Case(
        "fixed-window",
        params={
            "sweep": SWEEP, "window": WINDOW,
            "tools": "absdiff,mhi(30-20-10)", "forms": 2,
        },
        samples_ms=[float(h) for h in holds_trace],
        unit="frames held",
    )
    run.cases.append(case)
    harness.report(case)

    run.note(f"fixed: peak={peak}, evictions={evictions}")
    print(f"  fixed:   peak={peak} held, {evictions} evictions")


def main() -> None:
    run = harness.Run(
        experiment="02-derived-eviction",
        question=(
            "Does declaration-derived eviction hold fewer frames than a "
            "fixed 300-frame window, with the same consumers?"
        ),
    )

    print("02 — derived eviction")
    print()

    run_derived(run)
    run_fixed(run)
    print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
