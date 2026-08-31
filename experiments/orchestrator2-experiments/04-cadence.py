"""Does the recorded set depend on what the machine had time to draw?

ADR-0005's acceptance test, run. That ADR states it in one line — *whether
the set of recorded values would differ on a slower machine* — and never took
the measurement, because the four experiments that could have caught the
defect were cost experiments and a value filed by the wrong producer costs
exactly what the right one costs. This one does not measure duration as the
headline. It measures **which rows exist afterwards**.

Two arms, each run under two loads. The comparison that matters is an arm
against *itself*:

  landed    `nodes.StepNode` driven by `nodes.Pass`. A row is recorded when
            the dispatcher re-enters the step because its inputs landed.
  drawn     `Renderer`, which is the defect ADR-0005 records this tree having
            built: a display loop that paints the newest row on hand and
            files the number it computed in order to paint it. It never goes
            back for a row the fill passed while a paint was in flight,
            because a display does not — that is what makes the set a
            property of the session.

**Comparing `landed` against `drawn` is not the measurement.** Their sets
differ enormously by construction: one records every row of the window and the
other records whatever the frontier was at paint times. The measurement is
each arm's quiet set against its own loaded set. An arm whose two sets are
identical records what the work produced; an arm whose two sets differ records
what the machine had slack for.

## Both outcomes, before the run

- **`landed` identical across loads and `drawn` differing**: the display was a
  data source and recording on the landing cadence removes it. ADR-0005's
  three candidates all clear this bar, so what separates them stops being
  whether they fix this and becomes how each handles an input arriving after
  its row was decided — which is the Dataflow candidate's whole vocabulary and
  neither of the others'.
- **`landed` also differing across loads**: something in the current
  arrangement is still coupled to load, the landing cadence is not sufficient
  on its own, and the ADR is not closed by it. Where the difference lives —
  eviction, a superseded activation, the pool ceiling — is the next question
  and not this one.
- **`drawn` not differing across loads**: the load did not make a slower
  machine, and nothing here is a result. That is a defect in this experiment,
  not a finding about the arrangement, so `paint_ms` and `paints` are reported
  first and checked before anything else is read.

## The topology

    source -> pool -> {sweep (declares the window), recorder (reach 1)}

One form throughout, the full luma plane at source sampling, the step deriving
its own crop inside its own envelope — 01-reentry's topology exactly, so its
numbers are the quiet baseline for everything here except the recorded set.

The sweep is what makes either arm's set interesting: rows arrive because a
producer is fetching them in its own order, and the arms differ only in what
gets to file a value when one does.

## The core shape

One fetch thread, two recorder threads, every node PARALLEL, request depth 1.
The `drawn` arm adds one display thread; the `landed` arm adds none. Load is
`LOAD_THREADS` background threads doing float32 matmuls, which release the GIL
and take cores from whatever else is running.
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
from graph import Graph
from nodes import Pass, StepNode, Sweep
from pool import Pool

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GOP = 24
CROP_RECT = (2144, 982, 1024, 1024)
POOL_BUDGET = 12 << 30
#: 01-reentry's window, so the quiet arms are comparable to its numbers.
WINDOW_FRAMES = 160
DEPTH = 1
#: Interleaved and repeated for the reason 01-reentry learned the hard way:
#: every arm is slower in the last repeat than in the first, by more than the
#: arms differ from each other, and one run of each cannot tell those apart.
REPS = 3
#: A display cadence, not a poll interval. The `drawn` arm is not waiting for
#: anything — it paints, and this is how often.
DISPLAY_S = 1 / 60
#: What stands in for a slower machine. Named in the result because a set
#: measured under four contending threads and a set measured under none are
#: different facts about the same code.
LOAD_THREADS = 4
LOAD_N = 512


class Load:
    """Background threads that take cores, or nothing at all.

    A slower machine, approximated the only way a fixed machine can: the same
    work with less of the processor available to it. numpy's matmul releases
    the GIL, so this contends for cores rather than for the interpreter —
    which is the contention a real second application produces and the
    contention a GIL-bound spin loop does not.
    """

    def __init__(self, threads: int) -> None:
        self.threads = threads
        self._stop = threading.Event()
        self._running: list[threading.Thread] = []

    def __enter__(self) -> "Load":
        self._stop.clear()
        for i in range(self.threads):
            thread = threading.Thread(target=self._burn, name=f"load{i}",
                                      daemon=True)
            thread.start()
            self._running.append(thread)
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        for thread in self._running:
            thread.join(timeout=10)
        self._running = []

    def _burn(self) -> None:
        a = np.random.rand(LOAD_N, LOAD_N).astype(np.float32)
        b = np.random.rand(LOAD_N, LOAD_N).astype(np.float32)
        while not self._stop.is_set():
            a @ b


class Renderer:
    """The display as a data source — ADR-0005's Rejected section, runnable.

    Paints at `DISPLAY_S` and files the value it computed in order to paint.
    Two properties are the whole point and neither is an oversight:

    It draws the **newest** row whose inputs are on hand, so a fill that ran
    ahead while a paint was in flight leaves rows behind. And it **never goes
    back**: once the frontier has moved past a row, that row is gone, because
    that is what a display does. A renderer that returned for skipped rows
    would be a background pass wearing a renderer's clothes, and would measure
    nothing.

    It does not declare. It reads what the sweep is already holding, which is
    exactly the argument that made this arrangement look free: the frame was
    decoded anyway and the number falls out of drawing it.
    """

    def __init__(self, tool: tools_mod.Tool, source_form: forms_mod.Form,
                 crop_rect, pool: Pool, cadence_s: float = DISPLAY_S) -> None:
        self.tool = tool
        self.source_form = source_form
        self.crop_form = tool.form_for(crop_rect)
        self.source_key = source_form.key()
        self.pool = pool
        self.cadence_s = cadence_s
        self.node_id = f"render-{id(self)}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.values: dict[int, float] = {}
        self.paints = 0
        self.skipped = 0        #: rows the frontier passed without drawing
        self.paint_ms: list[float] = []
        self.compute_ms: list[float] = []

    def run_over(self, start: int, end: int) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(start, end),
                                        daemon=True)
        self._thread.start()

    def join(self, timeout: float = 600.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def stop(self) -> None:
        self._stop.set()
        self.join(10)

    def _frontier(self, lo: int, hi: int, above: int) -> int | None:
        """The highest row in [lo, hi) above `above` whose inputs are on hand.

        Scans down from the top, so under a sequential fill it stops within a
        few rows of the frontier. A miss all the way down means the fill has
        not reached anything new since the last paint, which is a wait in a
        real renderer and is a no-op here.
        """
        for row in range(hi - 1, max(lo, above + 1) - 1, -1):
            if all(self.pool.has(n, self.source_key)
                   for n in self.tool.needs(row)):
                return row
        return None

    def _loop(self, start: int, end: int) -> None:
        lo = start + self.tool.reach
        drawn_through = lo - 1
        while not self._stop.is_set():
            tick = time.perf_counter()
            row = self._frontier(lo, end, drawn_through)
            if row is not None:
                #: every row between the last one drawn and this one went past
                #: unrecorded, which is the measurement and not a leak
                self.skipped += row - drawn_through - 1
                t_compute = time.perf_counter()
                crops = {}
                for n in self.tool.needs(row):
                    full = self.pool.get(n, self.source_key, by=self.node_id)
                    if full is None:
                        crops = {}
                        break
                    crop, _how = forms_mod.derive(full, self.source_form,
                                                  self.crop_form)
                    crops[n] = crop
                if crops:
                    field = self.tool.field(crops, row)
                    self.values[row] = self.tool.reduce(field)
                    self.compute_ms.append(
                        (time.perf_counter() - t_compute) * 1000.0)
                    self.paints += 1
                    drawn_through = row
            self.paint_ms.append((time.perf_counter() - tick) * 1000.0)
            if drawn_through >= end - 1:
                return
            rest = self.cadence_s - (time.perf_counter() - tick)
            if rest > 0:
                time.sleep(rest)


class TimedStepNode(StepNode):
    """`StepNode` with one compute sample per row, so both arms report the
    same quantity in the same units."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.compute_ms: list[float] = []

    def _activate(self, reason, ctx):
        from dispatcher import Reason
        if reason is not Reason.ALL_FRAMES_READY:
            return super()._activate(reason, ctx)
        before = time.perf_counter()
        try:
            return super()._activate(reason, ctx)
        finally:
            self.compute_ms.append((time.perf_counter() - before) * 1000.0)


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
            "max": round(ordered[-1], 3)}


def _arena(width: int, height: int, start: int, end: int):
    """A graph, a pool, a dispatcher and a declared window, fresh per arm.

    Carried across arms it would hand the second one a window somebody else
    decoded, and the fill rate is half of what selects the drawn arm's set.
    """
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    form_key = source_form.key()
    dispatcher = Dispatcher(graph, pool, form_key,
                            lambda: Fetcher(BIG), recorders=2)
    sweep = Sweep(start, end, start, form_key, graph)
    return graph, pool, source_form, form_key, dispatcher, sweep


def run_landed(width: int, height: int, start: int, end: int) -> dict:
    graph, pool, source_form, form_key, dispatcher, sweep = _arena(
        width, height, start, end)
    tool = tools_mod.absdiff()
    step = TimedStepNode(tool, source_form, CROP_RECT, dispatcher)
    walk = Pass(step, start + tool.reach, end, depth=DEPTH)
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    walk.run()
    walk.done.wait(timeout=900)
    wall = time.perf_counter() - t0
    stats = {"arm": "landed",
             "wall_s": round(wall, 3),
             "recorded": len(step.values),
             #: absent rather than zero: nothing selects against a row here,
             #: so there is no cadence for one to fall through
             "skipped": None,
             "paints": None,
             "paint_summary": None,
             "compute_summary": _quantiles(step.compute_ms),
             "dispatcher": dispatcher.stats(),
             "pool": pool.stats()}
    values = dict(step.values)
    dispatcher.stop()
    return {"stats": stats, "values": values, "compute_ms": step.compute_ms}


def run_drawn(width: int, height: int, start: int, end: int) -> dict:
    graph, pool, source_form, form_key, dispatcher, sweep = _arena(
        width, height, start, end)
    tool = tools_mod.absdiff()
    renderer = Renderer(tool, source_form, CROP_RECT, pool)
    dispatcher.start()
    t0 = time.perf_counter()
    sweep.declare()
    renderer.run_over(start, end)
    renderer.join(timeout=900)
    wall = time.perf_counter() - t0
    stats = {"arm": "drawn",
             "wall_s": round(wall, 3),
             "recorded": len(renderer.values),
             "skipped": renderer.skipped,
             "paints": renderer.paints,
             "paint_summary": _quantiles(renderer.paint_ms),
             "compute_summary": _quantiles(renderer.compute_ms),
             "dispatcher": dispatcher.stats(),
             "pool": pool.stats()}
    values = dict(renderer.values)
    renderer.stop()
    dispatcher.stop()
    return {"stats": stats, "values": values,
            "compute_ms": renderer.compute_ms}


def _set_delta(quiet: dict, loaded: dict) -> dict:
    """What two runs of one arm disagree about, in rows.

    The headline. `only_quiet` and `only_loaded` are rows one run recorded and
    the other did not; `disagree` is rows both recorded at different values,
    which would be a different and worse defect than the one under test.
    """
    a, b = set(quiet), set(loaded)
    shared = sorted(a & b)
    disagree = [row for row in shared if quiet[row] != loaded[row]]
    union = a | b
    return {"quiet_n": len(a), "loaded_n": len(b), "shared_n": len(shared),
            "only_quiet_n": len(a - b), "only_loaded_n": len(b - a),
            "identical_sets": a == b,
            "jaccard": round(len(a & b) / len(union), 4) if union else 1.0,
            "values_disagree_n": len(disagree),
            "only_quiet": sorted(a - b)[:40],
            "only_loaded": sorted(b - a)[:40]}


def main() -> None:
    total, width, height, fps = _open_total()
    start = total // 3
    end = min(start + WINDOW_FRAMES, total)

    run = harness.Run(
        experiment="04-cadence",
        question=("Does the set of recorded values depend on what the machine "
                  "had time to draw? ADR-0005's acceptance test."))
    run.add_footage(BIG)
    run.note("topology: source -> pool -> {sweep declares the window; one "
             "recorder at reach 1}. One form throughout, the full luma plane "
             f"at source sampling; the crop {CROP_RECT} is derived inside the "
             "recorder's own envelope. 01-reentry's topology exactly.")
    run.note(f"core shape: 1 fetch thread, 2 recorder threads, every node "
             f"PARALLEL, request depth {DEPTH}. The drawn arm adds one "
             f"display thread at {DISPLAY_S * 1000:.1f} ms; the landed arm "
             f"adds none.")
    run.note(f"load stands in for a slower machine: {LOAD_THREADS} threads "
             f"doing {LOAD_N}x{LOAD_N} float32 matmuls, which release the GIL "
             f"and contend for cores rather than for the interpreter. Read "
             f"paint_summary first — if load did not move it, the loaded arm "
             f"is not a slower machine and nothing below is a result.")
    run.note(f"window: rows {start}..{end} ({end - start} frames) at "
             f"{fps:.3f} fps, of {total} listed. Nothing else declares, so "
             f"the fill is one sequential run and the fetch thread never "
             f"preempts.")
    run.note("compute_ms is not comparable ACROSS arms: StepNode holds its "
             "derived crops between rows (binding.Held) and the renderer "
             "re-derives both every paint, because a display draws the row it "
             "is on. Within an arm across loads it is the same code, which is "
             "the only comparison made of it here.")
    run.note("The comparison is each arm against ITSELF under two loads. "
             "Comparing landed against drawn is not the measurement: their "
             "sets differ by construction, since one records every row and "
             "the other records whatever the frontier was when it painted.")
    run.note(f"{REPS} repeats, arms interleaved within each repeat, for the "
             f"reason 01-reentry recorded: every arm is slower in the last "
             f"repeat than in the first, by more than the arms differ.")

    arms = [("landed", run_landed), ("drawn", run_drawn)]
    loads = [("quiet", 0), ("loaded", LOAD_THREADS)]
    samples: dict[str, list[float]] = {}
    walls: dict[str, list[float]] = {}
    last: dict[str, dict] = {}
    values: dict[str, dict] = {}
    for arm, _ in arms:
        for load, _n in loads:
            samples[f"{arm}-{load}"] = []
            walls[f"{arm}-{load}"] = []

    deltas: list[dict] = []
    for rep in range(REPS):
        per_rep: dict[str, dict] = {}
        for arm, runner in arms:
            for load, threads in loads:
                name = f"{arm}-{load}"
                if threads:
                    with Load(threads):
                        got = runner(width, height, start, end)
                else:
                    got = runner(width, height, start, end)
                stats = got["stats"]
                samples[name].extend(got["compute_ms"])
                walls[name].append(stats["wall_s"])
                last[name] = stats
                values[name] = got["values"]
                per_rep[name] = got["values"]
                paint = stats["paint_summary"]
                print(f"rep{rep} {name:>14} wall {stats['wall_s']:>7}s  "
                      f"recorded {stats['recorded']:>4}  "
                      f"skipped {stats['skipped']}  "
                      f"paint p50 {paint['p50'] if paint else '-'}")
        for arm, _ in arms:
            delta = _set_delta(per_rep[f"{arm}-quiet"],
                               per_rep[f"{arm}-loaded"])
            delta["arm"] = arm
            delta["repeat"] = rep
            deltas.append(delta)
            print(f"       {arm:>14} quiet vs loaded: "
                  f"identical_sets={delta['identical_sets']}  "
                  f"only_quiet={delta['only_quiet_n']}  "
                  f"only_loaded={delta['only_loaded_n']}  "
                  f"values_disagree={delta['values_disagree_n']}")

    for arm, _ in arms:
        for load, threads in loads:
            name = f"{arm}-{load}"
            params = dict(last[name])
            params["walls_s_per_repeat"] = walls[name]
            params["repeats"] = REPS
            params["load_threads"] = threads
            params["set_deltas_vs_own_quiet"] = [
                d for d in deltas if d["arm"] == arm] if load == "loaded" else None
            run.cases.append(harness.Case(
                name=f"{name}-compute",
                params=params,
                samples_ms=[round(ms, 4) for ms in samples[name]],
                unit="ms per row of derive + field + reduce",
                note=("recorded when its inputs landed"
                      if arm == "landed" else
                      f"recorded when it was painted, {DISPLAY_S * 1000:.1f} "
                      f"ms cadence, never revisited")))

    print()
    for case in run.cases:
        harness.report(case)
        print(f"    walls {case.params['walls_s_per_repeat']}  "
              f"recorded {case.params['recorded']}")

    for arm, _ in arms:
        mine = [d for d in deltas if d["arm"] == arm]
        stable = sum(1 for d in mine if d["identical_sets"])
        run.note(
            f"{arm}: quiet and loaded recorded identical sets in "
            f"{stable}/{len(mine)} repeats. Rows only the quiet run "
            f"recorded, per repeat: {[d['only_quiet_n'] for d in mine]}; only "
            f"the loaded run: {[d['only_loaded_n'] for d in mine]}. Values "
            f"disagreeing on shared rows: {[d['values_disagree_n'] for d in mine]}.")
        print(f"[sets] {arm}: identical in {stable}/{len(mine)} repeats")

    path = run.write()
    print(f"[wrote] {path}")


if __name__ == "__main__":
    main()
