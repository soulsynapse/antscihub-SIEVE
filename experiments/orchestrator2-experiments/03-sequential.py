"""Is `sequential` load-bearing, or does the bounded-reach contract already cover it?

README question 3. `contract/nodes.py`'s `Step.sequential` and
`tool-experiments/tools.py`'s `Tool.sequential` both exist and nothing
consults either.

## The prior art, because this is not an open problem

Filter-graph runtimes have mapped this space and the answer is a taxonomy,
not a binary. AviSynth+ has three MT modes: `MT_NICE_FILTER` (stateless, call
it from anywhere), `MT_MULTI_INSTANCE` (has state, so give each thread its
own copy), and `MT_SERIALIZED` (one at a time). VapourSynth's four are the
same distinctions redrawn, with `fmFrameState` for the serial-and-ordered
case. **The middle option is the one a naive port forgets**: state does not
imply serialization, it implies the state must not be shared.

And the arithmetic here is not intrinsically sequential. A decayed motion
history is `acc_n = max(alpha * acc_{n-1}, m_n)` — a first-order recurrence in
the max-plus semiring. Composing two of them gives
`a -> max(alpha^2 a, max(alpha C_1, C_2))`, the same shape, so the operator is
associative and the recurrence is a **prefix scan**: computable in any order
by the standard parallel-scan decomposition, exactly, with a constant-size
summary per chunk.

The consequence that matters here is weaker than a scan and more useful.
Because `alpha < 1` the influence of row `n - j` falls as `alpha^j`, so past
some `j` the history cannot move the answer at the precision anyone reads.
That is an **effective reach**, and it is structurally the same fact as a
keyframe bounding a seek — `2026.08.21-uncut-seek-costs-a-gop-not-a-frame` is
this tree's measurement of the same idea, and the usual name elsewhere is IIR
warm-up. A step with bounded reach is an ordinary step: `offsets` expresses
it, `first_honest` trims its warm-up rows, and no flag is involved.

So the question is not "does ordering work" — it does, trivially — but
**whether the contract the tree already has covers the case that motivated the
flag.** `tools.lag_mhi` is the same picture with sparse offsets and no state,
which is the tree having made this move once already.

## The arms

  reference   an ascending single-threaded loop. What the unbounded
              accumulator produces.
  shared      one stateful tool instance, `Mode.PARALLEL`, two recorder
              threads. **This is a data race and is included as one.** It is
              what a naive port writes, and its wrongness is a property of
              sharing mutable state between threads, not of parallel
              dispatch. An earlier version of this experiment reported it as
              evidence about scheduling, which was wrong.
  ordered     the same stateful tool under `Mode.ORDERED`: serial, ascending.
              Correct, and what being correct this way costs is the point.
  bounded-k   the same picture as a **stateless** step at offsets
              `(-k, ..., 0)`, recomputing the recurrence over its own reach.
              Nothing to race and nothing to order, so it runs fully
              parallel. Several `k`, to find the effective reach.

The sweep declares its window attention-first from an anchor, which is V1's
arrangement carried intact and why rows arrive out of ascending order in the
ordinary case rather than a contrived one.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import av
import harness
from harness import FOOTAGE

import forms as forms_mod
import tools as tools_mod
from dispatcher import Dispatcher, Mode
from fetch import Fetcher
from graph import Graph
from nodes import Pass, StepNode, Sweep
from pool import Pool

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
CROP_RECT = (2144, 982, 1024, 1024)
POOL_BUDGET = 12 << 30
WINDOW_FRAMES = 160
#: the anchor the sweep fills from, as a fraction of the window. 0.5, so the
#: second half arrives first and ascending delivery is not free.
ANCHOR_AT = 0.5
DECAY = 0.85
#: reaches for the stateless arm. The top one is past where `DECAY ** k * 255`
#: falls under half a grey level, which is the algebra's prediction for where
#: truncation stops being visible; the run says whether it holds on footage.
REACHES = (2, 5, 10, 20, 40)


def stateful_mhi(alpha: float = DECAY) -> tools_mod.Tool:
    """The unbounded accumulator: offsets `(0,)`, everything else in state."""
    state: dict[str, np.ndarray | None] = {"acc": None, "prev": None}

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        cur = frames[row].astype(np.float32)
        prev = state["prev"]
        motion = np.zeros_like(cur) if prev is None else np.abs(cur - prev)
        acc = state["acc"]
        acc = motion if acc is None else np.maximum(acc * alpha, motion)
        state["acc"] = acc
        state["prev"] = cur
        return acc

    return tools_mod.Tool(name="mhi-stateful",
                          form_for=tools_mod.analysis_form("gray"),
                          offsets=(0,), field=field, sequential=True,
                          params={"alpha": alpha}, version=1)


def bounded_mhi(reach: int, alpha: float = DECAY) -> tools_mod.Tool:
    """The same picture as an ordinary step: no state, reach `k`.

    Every value depends on nothing outside `offsets`, which is what makes it
    schedulable in any order by a dispatcher that knows nothing about it.
    """
    offsets = tuple(range(-reach, 1))

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        acc = None
        prev = None
        for offset in offsets:
            cur = frames[row + offset].astype(np.float32)
            if prev is not None:
                motion = np.abs(cur - prev)
                acc = motion if acc is None else np.maximum(acc * alpha,
                                                            motion)
            prev = cur
        return acc if acc is not None else np.zeros_like(prev)

    return tools_mod.Tool(name=f"mhi-reach{reach}",
                          form_for=tools_mod.analysis_form("gray"),
                          offsets=offsets, field=field, sequential=False,
                          params={"alpha": alpha, "reach": reach}, version=1)


def _open_total() -> tuple[int, int, int, float]:
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate)
        width, height = stream.width, stream.height
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
    return total - GOP, width, height, fps


def _arena(width: int, height: int):
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    dispatcher = Dispatcher(graph, pool, source_form.key(),
                            lambda _band: Fetcher(BIG), recorders=2, readers=1)
    return graph, pool, source_form, dispatcher


def run_arm(tool: tools_mod.Tool, mode: Mode, width: int, height: int,
            start: int, end: int, anchor: int) -> dict:
    graph, pool, source_form, dispatcher = _arena(width, height)
    step = StepNode(tool, source_form, CROP_RECT, dispatcher)
    dispatcher.set_mode(step.node_id, mode)
    sweep = Sweep(start, end, anchor, source_form.key(), graph)
    walk = Pass(step, start + tool.reach, end, depth=WINDOW_FRAMES)

    depths = []
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    walk.run()
    while not walk.done.wait(0.05):
        depths.append(dispatcher.stats()["ready_depth"])
        if time.perf_counter() - t0 > 600:
            break
    wall = time.perf_counter() - t0
    stats = dispatcher.stats()
    out = {"mode": mode.value, "tool": tool.name, "reach": tool.reach,
           "wall_s": round(wall, 3), "computed": step.computed,
           "values": dict(step.values), "order": list(step.order),
           "peak_ready_depth": max(depths) if depths else 0,
           "peak_concurrent": step.peak_concurrent,
           "dispatcher": stats, "pool": pool.stats()}
    dispatcher.stop()
    return out


def run_reference(width: int, height: int, start: int, end: int) -> dict:
    """A plain ascending loop. No dispatcher, no threads, nothing to order."""
    _graph, _pool, source_form, _dispatcher = _arena(width, height)
    tool = stateful_mhi()
    crop_form = tool.form_for(CROP_RECT)
    fetcher = Fetcher(BIG)
    values = {}
    t0 = time.perf_counter()
    try:
        for row in range(start, end):
            arr, _how = fetcher.exact(row)
            crop, _ = forms_mod.derive(arr, source_form, crop_form)
            values[row] = tool.reduce(tool.field({row: crop}, row))
    finally:
        fetcher.close()
    return {"mode": "reference", "wall_s": round(time.perf_counter() - t0, 3),
            "computed": len(values), "values": values}


def _ascending_runs(order: list[int]) -> int:
    return 1 + sum(1 for a, b in zip(order, order[1:]) if b <= a)


def _compare(reference: dict, got: dict, from_row: int) -> dict:
    """Against the reference, on rows where the reference itself is honest.

    `from_row` excludes the reference's own warm-up: it began at `start` with
    an empty accumulator, so its early rows carry less history than a bounded
    arm reaching back past them, and comparing there would score the
    reference's artefact against the arm's.
    """
    shared = sorted(row for row in (set(reference["values"])
                                    & set(got["values"])) if row >= from_row)
    if not shared:
        return {"rows_compared": 0}
    diffs = [abs(reference["values"][r] - got["values"][r]) for r in shared]
    return {"rows_compared": len(shared),
            "rows_disagreeing": sum(1 for d in diffs if d != 0.0),
            "max_abs_diff": round(max(diffs), 6),
            "mean_abs_diff": round(sum(diffs) / len(diffs), 6)}


def main() -> None:
    total, width, height, fps = _open_total()
    start = total // 3
    end = min(start + WINDOW_FRAMES, total)
    anchor = start + int((end - start) * ANCHOR_AT)
    honest_from = start + max(REACHES)

    run = harness.Run(
        experiment="03-sequential",
        question="Is `sequential` load-bearing, or does the bounded-reach "
                 "contract the tree already has cover the case?")
    run.add_footage(BIG)
    run.note("topology: source -> pool -> {sweep declares the window "
             "attention-first from an anchor at its midpoint; one step}. The "
             "stateful step is built for this experiment because the tree "
             "contains none, and tools.py argues none should exist until "
             "something real needs one.")
    run.note(f"core shape: 1 fetch thread, 1 reader, 2 recorder threads, the "
             f"whole window armed at once. Window rows {start}..{end}, anchor "
             f"{anchor}. Comparisons start at row {honest_from}, past the "
             f"reference's own warm-up.")
    run.note("prior art leaned on rather than re-derived: AviSynth+'s three "
             "MT modes (nice / multi-instance / serialized) and "
             "VapourSynth's four, which say state implies unshared state "
             "rather than serialization; and the max-plus recurrence being "
             "associative, so the accumulator is a prefix scan whose history "
             "decays as alpha^j, giving an effective reach — the same "
             "structure as a keyframe bounding a seek.")

    reference = run_reference(width, height, start, end)
    print(f"[reference] {reference['computed']} rows, {reference['wall_s']}s, "
          f"ascending, single-threaded")

    rows = []

    shared = run_arm(stateful_mhi(), Mode.PARALLEL, width, height, start,
                     end, anchor)
    shared["note"] = ("one tool instance across two recorder threads: a data "
                      "race, included to show what a naive port does")
    rows.append(("shared-parallel (race)", shared))

    ordered = run_arm(stateful_mhi(), Mode.ORDERED, width, height, start,
                      end, anchor)
    ordered["note"] = "serial and ascending; correct, and the cost is the point"
    rows.append(("ordered", ordered))

    for reach in REACHES:
        got = run_arm(bounded_mhi(reach), Mode.PARALLEL, width, height,
                      start, end, anchor)
        got["note"] = (f"stateless, offsets (-{reach}..0); nothing to race "
                       f"and nothing to order")
        rows.append((f"bounded-{reach}", got))

    print()
    for name, got in rows:
        got["comparison"] = _compare(reference, got, honest_from)
        cmp = got["comparison"]
        print(f"{name:<24} wall {got['wall_s']:>6}s  runs "
              f"{_ascending_runs(got['order']):>2}  conc "
              f"{got['peak_concurrent']}  depth "
              f"{got['peak_ready_depth']:>3}  |  wrong "
              f"{cmp.get('rows_disagreeing')}/{cmp.get('rows_compared')}  "
              f"max {cmp.get('max_abs_diff')}  mean "
              f"{cmp.get('mean_abs_diff')}")
        run.note(
            f"arm {name}: {got['note']}. wall {got['wall_s']} s, "
            f"{_ascending_runs(got['order'])} ascending run(s), peak "
            f"concurrent {got['peak_concurrent']}, peak ready depth "
            f"{got['peak_ready_depth']}; against the reference on "
            f"{cmp.get('rows_compared')} rows, "
            f"{cmp.get('rows_disagreeing')} disagree, max abs "
            f"{cmp.get('max_abs_diff')}, mean abs "
            f"{cmp.get('mean_abs_diff')}.")
        run.cases.append(harness.Case(
            name=name,
            params={k: v for k, v in got.items()
                    if k not in ("values", "order")},
            samples_ms=[], unit="see params", note=got["note"]))

    run.write()


if __name__ == "__main__":
    main()
