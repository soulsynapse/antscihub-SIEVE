"""Does re-entry beat polling, on a window fill with one step riding along?

README question 1's countable half. The felt half — foreground latency during
a scrub — is the explorer's, because a number for how a drag feels is a
number about a drag.

Two arms, one variable. Both run the same dispatcher, the same pool, the same
graph, the same tool and the same window, over the same footage:

  polling   `Poller`, which is `orchestrator-experiments/explorer.py`'s
            `ToolRunner._work` with Qt removed and nothing else changed: one
            thread per step, declaring a row, then sleeping 5 ms in a loop
            until every needed row is resident, with a ten-second deadline
            and a `starved` counter for the rows that hit it.
  reentry   `nodes.StepNode` driven by `nodes.Pass`: no thread, no interval,
            no deadline. The dispatcher re-enters the step when its rows
            land.

The arm is the only difference. Both arms' rows are fetched by the same
`Dispatcher` with the same fetch thread, so anything the seek/step rule
decides is common to both and cancels.

## What is measured, and why each

- **wall** for the step to compute every row of the window. The headline, and
  the one most likely to come out equal — the sweep's decodes dominate both
  arms and neither changes them.
- **handoff**: from the moment the last input a row needs is resident, to the
  moment the arithmetic for that row starts. This is the term re-entry
  actually removes, and it is the only one where a poll interval can appear.
  Measured identically in both arms by timestamping every landing through
  `Pool.on_put`, so neither arm is trusted to report its own latency.
- **threads**, **sleeps**, and **slept_s**: what the arrangement costs when it
  is doing nothing. A poller that never has to wait still runs a thread.
- **starved**: rows abandoned at the deadline. Structurally impossible in the
  re-entry arm, which is a claim rather than a measurement and is reported as
  the absence it is.
- **values agree**: every row's value, both arms, compared exactly. A
  scheduling change that moves a number is not a scheduling change.

## The topology

    source -> pool -> {sweep (declares the window), step (absdiff, reach 1)}

One form throughout — the full luma plane at source sampling — with the step
deriving its own crop inside its own envelope. Cross-form negotiation in the
pool is a different question and mixing it in here would make the handoff
number a statement about two things.

The sweep is what makes this a fair test of the *step's* arrangement: rows
arrive at the step because a producer was already fetching them in its own
order, which is the regime both arms are actually deployed in. A step
fetching for itself alone would measure a decoder.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from harness import FOOTAGE

import av

import forms as forms_mod
import tools as tools_mod
from dispatcher import Dispatcher
from fetch import Fetcher
from graph import Envelope, Graph, Need, Urgency
from nodes import Pass, StepNode, Sweep
from pool import Pool

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
CROP_RECT = (2144, 982, 1024, 1024)
POOL_BUDGET = 12 << 30
#: Short beside the explorer's 20 s window on purpose: this measures a
#: handoff per row, which needs rows and not seconds, and the memory numbers
#: this arm would produce are the derived-eviction finding's already.
WINDOW_FRAMES = 160
#: `nodes.Pass`'s request depth — how many activations of one node may be in
#: flight. Named in every result because it is part of the core shape.
#:
#: One, because deeper was measured and only cost: across interleaved
#: repeats, depth 16 raised the handoff p50 above depth 1's and moved the
#: wall not at all. It buys nothing while the fetch thread is the bottleneck,
#: which it is whenever a decode costs milliseconds and a step's arithmetic
#: costs tenths of one. The arm is kept and measured rather than deleted,
#: because "deeper is worse here" is a result and a knob with one value that
#: nobody checked is not.
DEPTH = 1
DEEP = 16             #: the contrasting depth, run as its own arm
#: Interleaved, because the arms drift together across a session — every arm
#: was slower in the third repeat than in the first — and one run of each
#: cannot tell an effect from that drift. It told this experiment the wrong
#: thing once already.
REPS = 3
POLL_S = 0.005        #: V1's interval, carried so the arm is V1's arm
DEADLINE_S = 10.0     #: V1's deadline, same reason


class Landings:
    """When each key landed, so neither arm reports its own latency.

    Installed on the pool. `handoff` for a row is the gap between the last of
    its inputs landing and its arithmetic starting, and both arms are timed
    against this one clock.
    """

    def __init__(self, pool: Pool) -> None:
        self.at: dict[tuple[int, str], float] = {}
        self._lock = threading.Lock()
        pool.on_put(self._landed)

    def _landed(self, key: tuple[int, str]) -> None:
        with self._lock:
            self.at[key] = time.perf_counter()

    def ready_at(self, rows, form_key: str) -> float:
        """When the last of these landed. 0.0 if any never did."""
        with self._lock:
            stamps = [self.at.get((row, form_key)) for row in rows]
        return max(stamps) if all(s is not None for s in stamps) else 0.0


class Poller:
    """V1's `ToolRunner._work`, Qt removed and nothing else changed.

    Kept faithful deliberately, including the shape of the local `derived`
    dict and the manual eviction below `pos - reach`: the comparison is
    against what V1 actually ran, not against a version of it improved on the
    way past. The only additions are the two the measurement needs — a
    handoff sample per row, and the wall.
    """

    def __init__(self, tool: tools_mod.Tool, source_form: forms_mod.Form,
                 graph: Graph, pool: Pool, landings: Landings) -> None:
        self.tool = tool
        self.source_form = source_form
        self.crop_form = tool.form_for(CROP_RECT)
        self.graph = graph
        self.pool = pool
        self.landings = landings
        self.node_id = f"tool-{tool.name}-{id(self)}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.values: dict[int, float] = {}
        self.computed = 0
        self.starved = 0
        self.sleeps = 0
        self.slept_s = 0.0
        self.handoff_ms: list[float] = []

    def run_over(self, start: int, end: int) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._work, args=(start, end),
                                        daemon=True)
        self._thread.start()

    def join(self, timeout: float = 600.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def stop(self) -> None:
        self._stop.set()
        self.join(10)
        self.graph.release(self.node_id)

    def _work(self, start: int, end: int) -> None:
        fk = self.source_form.key()
        reach = self.tool.reach
        derived: dict[int, np.ndarray] = {}
        try:
            for pos in range(start + reach, end):
                if self._stop.is_set():
                    return
                needed = self.tool.needs(pos)
                self.graph.declare(Need(self.node_id, pos, self.tool.offsets,
                                        fk, Urgency.DEFERRED))
                fulls: dict[int, np.ndarray] = {}
                deadline = time.perf_counter() + DEADLINE_S
                while len(fulls) < len(needed):
                    if self._stop.is_set():
                        return
                    for n in needed:
                        if n not in fulls:
                            arr = self.pool.get(n, fk, by=self.node_id)
                            if arr is not None:
                                fulls[n] = arr
                    if len(fulls) < len(needed):
                        if time.perf_counter() > deadline:
                            break
                        self.sleeps += 1
                        before = time.perf_counter()
                        time.sleep(POLL_S)
                        self.slept_s += time.perf_counter() - before

                if len(fulls) < len(needed):
                    self.starved += 1
                    continue

                noticed = time.perf_counter()
                landed = self.landings.ready_at(needed, fk)
                if landed:
                    self.handoff_ms.append((noticed - landed) * 1000.0)

                for n in needed:
                    if n not in derived:
                        crop, _how = forms_mod.derive(
                            fulls[n], self.source_form, self.crop_form)
                        derived[n] = crop
                field = self.tool.field({n: derived[n] for n in needed}, pos)
                value = self.tool.reduce(field)
                for n in list(derived):
                    if n < pos - reach:
                        derived.pop(n, None)
                self.values[pos] = value
                self.computed += 1
                for n in needed:
                    self.graph.release_row(self.node_id, n, fk)
        finally:
            self.graph.release(self.node_id)


class TimedStepNode(StepNode):
    """`StepNode` with one handoff sample per row, against the same clock."""

    def __init__(self, *args, landings: Landings, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.landings = landings
        self.handoff_ms: list[float] = []

    def _activate(self, reason, ctx):
        from dispatcher import Reason
        if reason is Reason.ALL_FRAMES_READY:
            landed = self.landings.ready_at(self.tool.needs(ctx.row),
                                            self.source_key)
            if landed:
                self.handoff_ms.append(
                    (time.perf_counter() - landed) * 1000.0)
        super()._activate(reason, ctx)


def _open_total() -> tuple[int, int, int, float]:
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate)
        width, height = stream.width, stream.height
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
    return total - GOP, width, height, fps


def _quantiles(samples: list[float]) -> dict:
    if not samples:
        return {"n": 0}
    ordered = sorted(samples)
    return {"n": len(ordered),
            "p50": round(ordered[len(ordered) // 2], 3),
            "p95": round(ordered[int(len(ordered) * 0.95)], 3),
            "max": round(ordered[-1], 3),
            "total_ms": round(sum(ordered), 1)}


def _arena(width: int, height: int, start: int, end: int):
    """A graph, a pool, a landings clock, a dispatcher and a declared window.

    Built fresh per arm: a pool carried across arms would hand the second one
    a window somebody else decoded, which is the whole measurement.
    """
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    landings = Landings(pool)
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    form_key = source_form.key()
    dispatcher = Dispatcher(graph, pool, form_key,
                            lambda _band: Fetcher(BIG), recorders=2)
    sweep = Sweep(start, end, start, form_key, graph)
    return graph, pool, landings, source_form, form_key, dispatcher, sweep


def run_polling(run, total: int, width: int, height: int,
                start: int, end: int) -> dict:
    graph, pool, landings, source_form, form_key, dispatcher, sweep = _arena(
        width, height, start, end)
    tool = tools_mod.absdiff()
    poller = Poller(tool, source_form, graph, pool, landings)
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    poller.run_over(start, end)
    poller.join()
    wall = time.perf_counter() - t0
    stats = {"arm": "polling",
             "wall_s": round(wall, 3),
             "computed": poller.computed,
             "starved": poller.starved,
             "threads": {"fetch": 1, "recorders": 2, "per_step": 1},
             "sleeps": poller.sleeps,
             "slept_s": round(poller.slept_s, 3),
             "handoff_summary": _quantiles(poller.handoff_ms),
             "dispatcher": dispatcher.stats(),
             "pool": pool.stats()}
    values = dict(poller.values)
    poller.stop()
    dispatcher.stop()
    return {"stats": stats, "values": values, "handoff_ms": poller.handoff_ms}


def run_reentry(run, total: int, width: int, height: int,
                start: int, end: int, depth: int = DEPTH) -> dict:
    graph, pool, landings, source_form, form_key, dispatcher, sweep = _arena(
        width, height, start, end)
    tool = tools_mod.absdiff()
    step = TimedStepNode(tool, source_form, CROP_RECT, dispatcher,
                         landings=landings)
    walk = Pass(step, start + tool.reach, end, depth=depth)
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    walk.run()
    walk.done.wait(timeout=600)
    wall = time.perf_counter() - t0
    stats = {"arm": "reentry",
             "wall_s": round(wall, 3),
             "computed": step.computed,
             #: not zero — absent. There is no deadline to exceed, so no row
             #: can be abandoned for having waited too long.
             "starved": None,
             "threads": {"fetch": 1, "recorders": 2, "per_step": 0},
             "sleeps": 0,
             "slept_s": 0.0,
             "request_depth": depth,
             "handoff_summary": _quantiles(step.handoff_ms),
             "dispatcher": dispatcher.stats(),
             "pool": pool.stats()}
    values = dict(step.values)
    dispatcher.stop()
    return {"stats": stats, "values": values, "handoff_ms": step.handoff_ms}


def main() -> None:
    total, width, height, fps = _open_total()
    start = total // 3
    end = min(start + WINDOW_FRAMES, total)

    run = harness.Run(
        experiment="01-reentry",
        question="Does re-entry beat polling on a window fill, and on what axis?")
    run.add_footage(BIG)
    run.note("topology: source -> pool -> {sweep declares the window; one "
             "step at reach 1 rides along}. One form throughout, the full "
             "luma plane at source sampling; the step derives its own crop "
             f"{CROP_RECT} inside its own envelope.")
    run.note(f"core shape: 1 fetch thread, 2 recorder threads, every node "
             f"PARALLEL. The polling arm adds one thread per step; the "
             f"re-entry arms add none. Request depth is the arm.")
    run.note(f"window: rows {start}..{end} ({end - start} frames) at "
             f"{fps:.3f} fps, of {total} listed. Nothing else declares, so "
             f"the fetch thread never preempts and the whole window is one "
             f"sequential run. This is the quiet case on purpose: what "
             f"re-entry does under contention is the explorer's to say.")
    run.note("Both arms are timed against one clock: every landing is "
             "stamped through Pool.on_put, so no arm reports its own "
             "latency. Handoff samples are per row, kept across all repeats.")
    run.note(f"{REPS} repeats, arms interleaved within each repeat. A single "
             f"run of each read the wall difference as an effect when it was "
             f"session drift: every arm is slower in the last repeat than in "
             f"the first, by more than the arms differ from each other.")

    arms = [("polling", None), (f"reentry-d{DEPTH}", DEPTH),
            (f"reentry-d{DEEP}", DEEP)]
    samples: dict[str, list[float]] = {name: [] for name, _ in arms}
    walls: dict[str, list[float]] = {name: [] for name, _ in arms}
    last: dict[str, dict] = {}
    values: dict[str, dict] = {}

    for rep in range(REPS):
        for name, depth in arms:
            if depth is None:
                got = run_polling(run, total, width, height, start, end)
            else:
                got = run_reentry(run, total, width, height, start, end,
                                  depth=depth)
            stats = got["stats"]
            samples[name].extend(got["handoff_ms"])
            walls[name].append(stats["wall_s"])
            last[name] = stats
            values[name] = got["values"]
            print(f"rep{rep} {name:>14} wall {stats['wall_s']:>6}s  "
                  f"computed {stats['computed']}  "
                  f"seeks {stats['dispatcher']['seeks']}  "
                  f"handoff p50 {stats['handoff_summary']['p50']}")

    for name, depth in arms:
        params = dict(last[name])
        params["walls_s_per_repeat"] = walls[name]
        params["repeats"] = REPS
        case = harness.Case(
            name=f"{name}-handoff",
            params=params,
            samples_ms=[round(ms, 4) for ms in samples[name]],
            unit="ms from last input resident to arithmetic starting",
            note=("one thread per step, 5 ms poll, 10 s deadline"
                  if depth is None else
                  f"no thread, no interval, no deadline; request depth {depth}"))
        run.cases.append(case)

    print()
    for case in run.cases:
        harness.report(case)
        print(f"    walls {case.params['walls_s_per_repeat']}")

    base = values["polling"]
    for name, _ in arms[1:]:
        other = values[name]
        shared = sorted(set(base) & set(other))
        bad = [row for row in shared if base[row] != other[row]]
        biggest = max((abs(base[r] - other[r]) for r in shared), default=None)
        run.note(f"values, polling vs {name}: {len(shared)} rows computed by "
                 f"both, {len(bad)} disagree, max abs difference {biggest}. "
                 f"Rows only polling computed: {sorted(set(base) - set(other))}"
                 f"; only {name}: {sorted(set(other) - set(base))}.")
        print(f"[agree] polling vs {name}: {len(shared)} rows, {len(bad)} "
              f"disagree, max abs diff {biggest}")

    path = run.write()
    print(f"[wrote] {path}")


if __name__ == "__main__":
    main()
