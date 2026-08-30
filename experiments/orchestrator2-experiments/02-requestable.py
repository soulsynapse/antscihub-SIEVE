"""Does routing a chained field through the dispatcher cost more than holding it in a dict?

README question 2. `2026.08.30-holding-a-chained-field-pays-above-a-producer-
crossover` already established, at this same 462² regime, that holding a
producer's field beats recomputing it above a producer cost of roughly a third
of a millisecond, and which of this tree's steps fall either side of that.
**That number is not re-derived here.** `chain-experiments/02-chained-field`
measured it with a plain `Held` dict scoped to one binding.

What is unmeasured is whether making the field *requestable* — a consumer's
field want becoming `ctx.request(row, field_key)` like any other, waiting on
an activation the dispatcher re-enters, held in the refcounted pool rather
than in a dict — costs anything on top of that. It is not obviously free: the
same-day re-entry finding puts an activation's handoff at a few tenths of a
millisecond, and the chained-field finding puts the consumer's own arithmetic
floor at about half of one. A per-row cost of that size against a floor of
that size moves the crossover rather than rounding off it.

## The arms

Every arm computes identical values over identical rows with **every frame
resident before timing starts**, as in the finding this reads against: decode
is in none of these numbers.

  recomputed    the consumer computes the producer's field for each admitted
                offset, every row. No cache anywhere. The upper bound.
  held          the producer's fields kept in `sieve/pipeline/binding.py`'s
                `Held`, released below `row - reach`. This is the finding's
                arrangement, reproduced here so the dispatcher arm has a
                baseline taken on the same machine on the same day rather
                than a number carried across from another folder.
  dispatched-1  the producer is a node whose field lands in the pool; the
                consumer requests those rows and is re-entered when they are
                all resident. **One recorder thread**, so the only difference
                from `held` is the bookkeeping path: same work, same order,
                same thread.
  dispatched-2  the same with two recorder threads, where the producer's
                activations may overlap the consumer's. Not a purer version
                of the same measurement — a different question — and reported
                separately for that reason.

The one-recorder arm is the one that answers the question as asked. The
two-recorder arm says what the arrangement is worth when it is also allowed
to overlap, which is a benefit of being requestable rather than a cost of it.
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
from dispatcher import Dispatcher, Reason
from fetch import Fetcher
from graph import Graph
from nodes import ChainedStepNode, Pass, StepNode
from pool import Pool

from sieve.pipeline.binding import Held

harness.RESULTS = Path(__file__).resolve().parent / "results"

#: The small regime the analysis costs were priced in, and the one
#: `chain-experiments/02` used, so the arms here are readable against it.
SMALL = FOOTAGE / "rep3_intermittent_crop.MP4"
#: The consumer's lags — `lag_mhi`'s shape, four admitted positions spanning
#: thirty-one, so reach and the count of admitted inputs are different numbers.
LAGS = (30, 20, 10)
CONSUMER_OFFSETS = tuple(sorted(-lag for lag in LAGS) + [0])
COMPUTE = 120          #: consumer rows timed
POOL_BUDGET = 4 << 30
WARMUP = 5             #: discarded and stated, as everywhere
#: Interleaved repeats. The re-entry experiment of the same date read session
#: drift as an effect from one run per arm, and this machine drifts by more
#: than these arms differ; the arms are cycled so drift lands on all of them.
REPS = 3


def _open_small() -> tuple[int, int, int]:
    with av.open(str(SMALL)) as container:
        stream = container.streams.video[0]
        total = stream.frames or int(
            stream.duration * stream.time_base * stream.average_rate)
        return total, stream.width, stream.height


def producer_tool() -> tools_mod.Tool:
    """DIS ultrafast — above the crossover, so holding is supposed to pay."""
    return tools_mod.dis_flow()


def consumer_field(fields: dict[int, np.ndarray], row: int) -> np.ndarray:
    """Four weighted maximums over the producer's fields. The consumer's own
    arithmetic, and the floor no cache can touch."""
    out = None
    for rank, offset in enumerate(CONSUMER_OFFSETS[:-1]):
        weight = (rank + 1) / len(LAGS)
        aged = np.abs(fields[row + offset]) * weight
        out = aged if out is None else np.maximum(out, aged)
    current = np.abs(fields[row])
    return current if out is None else np.maximum(out, current)


def consumer_tool() -> tools_mod.Tool:
    return tools_mod.Tool(
        name="chained-mhi", form_for=tools_mod.analysis_form("gray"),
        offsets=CONSUMER_OFFSETS, field=consumer_field,
        params={"lags": "-".join(str(lag) for lag in sorted(LAGS))},
        version=1)


def _resident(rows: range, source_form: forms_mod.Form,
              crop_form: forms_mod.Form) -> dict[int, np.ndarray]:
    """Every crop the run needs, decoded before anything is timed."""
    fetcher = Fetcher(SMALL)
    crops = {}
    try:
        for row in rows:
            arr, _how = fetcher.exact(row)
            crops[row], _ = forms_mod.derive(arr, source_form, crop_form)
    finally:
        fetcher.close()
    return crops


def run_recomputed(crops, producer, consumer, rows) -> tuple[dict, list]:
    """Per-row samples carry the producer's work, because the consumer does
    it. That is what makes them comparable to `held` and not to a dispatched
    arm whose producer ran in a separate pass."""
    values, samples = {}, []
    for row in rows:
        t0 = time.perf_counter()
        fields = {}
        for needed in consumer.needs(row):
            fields[needed] = producer.field(
                {n: crops[n] for n in producer.needs(needed)}, needed)
        values[row] = consumer.reduce(consumer.field(fields, row))
        samples.append((time.perf_counter() - t0) * 1000.0)
    return values, samples


def run_held(crops, producer, consumer, rows) -> tuple[dict, list]:
    held = Held()
    values, samples = {}, []
    for row in rows:
        t0 = time.perf_counter()
        fields = {}
        for needed in consumer.needs(row):
            got = held.get(needed)
            if got is None:
                got = producer.field(
                    {n: crops[n] for n in producer.needs(needed)}, needed)
                held.put(needed, got)
            fields[needed] = got
        values[row] = consumer.reduce(consumer.field(fields, row))
        held.keep_from(row + min(CONSUMER_OFFSETS))
        samples.append((time.perf_counter() - t0) * 1000.0)
    return values, samples


def run_dispatched(crops, producer, consumer, rows, recorders: int,
                   source_form, crop_form) -> tuple[dict, list, dict]:
    """The producer's field lands in the pool; the consumer requests it.

    Frames are put into the pool before timing starts and the fetch thread
    never has anything to do, which is what keeps decode out of these numbers
    exactly as it is out of the other arms'.
    """
    graph = Graph()
    pool = Pool(graph, budget_bytes=POOL_BUDGET)
    source_key = source_form.key()
    dispatcher = Dispatcher(graph, pool, source_key,
                            lambda: Fetcher(SMALL), recorders=recorders,
                            readers=1)
    for row, crop in crops.items():
        pool.put(row, source_key, crop, by="preload")

    up = StepNode(producer, crop_form, crop_form.rect, dispatcher,
                  offers_field=True)
    down = ChainedStepNode(consumer, up.field_key, dispatcher)

    #: the producer runs over everything the consumer will admit, first. Its
    #: own pass, because a field is a product like any other and something
    #: has to ask for it — the consumer asking is what makes it requestable,
    #: not what makes it produced.
    lowest = min(rows) + min(CONSUMER_OFFSETS)
    up_pass = Pass(up, lowest, max(rows) + 1, depth=1)

    per_row: dict[int, float] = {}
    started: dict[int, float] = {}
    original = down._activate

    def timed(reason, ctx):
        if reason is Reason.ALL_FRAMES_READY:
            started[ctx.row] = time.perf_counter()
        original(reason, ctx)
        if reason is Reason.ALL_FRAMES_READY:
            per_row[ctx.row] = (time.perf_counter() - started[ctx.row]) * 1000.0

    down._activate = timed

    dispatcher.start()
    t0 = time.perf_counter()
    up_pass.run()
    up_pass.done.wait(600)
    t_producer = time.perf_counter() - t0
    down_pass = Pass(down, min(rows), max(rows) + 1, depth=1)
    down_pass.run()
    down_pass.done.wait(600)
    wall = time.perf_counter() - t0
    stats = dispatcher.stats()
    values = dict(down.values)
    stats["chain_wall_s"] = round(wall, 3)
    stats["producer_pass_s"] = round(t_producer, 3)
    stats["producer_rows"] = up.computed
    #: what the whole chain cost per consumer row, which is the only figure
    #: comparable to the other arms. The per-activation samples below are the
    #: consumer's own arithmetic with the producer's already paid for, and
    #: reading them against `held` would be reading a floor against a total.
    stats["chain_ms_per_consumer_row"] = round(wall * 1000.0 / len(rows), 3)
    stats["pool"] = pool.stats()
    dispatcher.stop()
    samples = [per_row[row] for row in rows if row in per_row]
    return values, samples, stats


def main() -> None:
    total, width, height = _open_small()
    producer = producer_tool()
    consumer = consumer_tool()
    source_form = forms_mod.Form((0, 0, width, height), (width, height),
                                 "gray")
    crop_form = producer.form_for((0, 0, width, height))

    first = producer.reach + consumer.reach
    rows = list(range(first, min(first + COMPUTE, total)))
    needed = range(0, rows[-1] + 1)

    run = harness.Run(
        experiment="02-requestable",
        question="Does routing a chained field through the dispatcher cost "
                 "more than holding it in a dict?")
    run.add_footage(SMALL)
    run.note("topology: source -> pool -> producer (DIS ultrafast, offsets "
             "(-1,0), offering its field) -> consumer (lags 30/20/10 plus 0 "
             "over that field). A two-deep chain, one form, one crop.")
    run.note(f"{len(list(needed))} frames resident before any arm is timed, "
             f"so decode is in none of these numbers — the same precondition "
             f"as chain-experiments/02, whose crossover this does not "
             f"re-derive.")
    run.note(f"core shape: 1 fetch thread with nothing to fetch, request "
             f"depth 1, every node PARALLEL; the recorder count is the arm. "
             f"{WARMUP} warm-up rows discarded per arm per repeat, "
             f"{REPS} repeats interleaved.")
    run.note("The dispatched arms' per-row samples are the consumer "
             "activation alone, with the producer's fields already in the "
             "pool. They are NOT comparable to the other arms' samples, "
             "which carry the producer's work; the comparable figure is "
             "`chain_ms_per_consumer_row`, the whole chain over the same "
             "rows. An earlier run of this experiment reported the floor "
             "against the totals and made the dispatcher look four times "
             "faster than a dict.")
    run.note("Demand does not propagate backwards here: the producer is "
             "driven by its own `Pass`, and a consumer requesting a field "
             "row waits for it rather than causing it. VapourSynth's "
             "`requestFrameFilter` propagates; this does not, so "
             "'requestable' in this experiment means 'held and served under "
             "a key', which is weaker.")

    crops = _resident(needed, source_form, crop_form)
    print(f"  {len(crops)} crops resident at {crop_form.key()}")

    samples = {}
    chains = {}
    values = {}
    extra = {}
    for rep in range(REPS):
        got, sam = run_recomputed(crops, producer, consumer, rows)
        samples.setdefault("recomputed", []).extend(sam[WARMUP:])
        chains.setdefault("recomputed", []).append(round(sum(sam) / 1000.0, 3))
        values["recomputed"] = got

        got, sam = run_held(crops, producer, consumer, rows)
        samples.setdefault("held", []).extend(sam[WARMUP:])
        chains.setdefault("held", []).append(round(sum(sam) / 1000.0, 3))
        values["held"] = got

        for recorders in (1, 2):
            name = f"dispatched-r{recorders}"
            got, sam, stats = run_dispatched(
                crops, producer, consumer, rows, recorders, source_form,
                crop_form)
            samples.setdefault(name, []).extend(sam[WARMUP:])
            chains.setdefault(name, []).append(stats["chain_wall_s"])
            values[name] = got
            extra[name] = stats
        print(f"  rep{rep} chains: "
              + "  ".join(f"{k} {v[-1]}s" for k, v in chains.items()))

    notes = {
        "recomputed": "upstream field recomputed per demand",
        "held": "upstream field in binding.Held, released below row - reach",
        "dispatched-r1": ("upstream field requestable in the pool; one "
                          "recorder, so the only difference from held is the "
                          "bookkeeping path"),
        "dispatched-r2": ("upstream field requestable in the pool; two "
                          "recorders, so producer and consumer may overlap"),
    }
    print()
    for name in ("recomputed", "held", "dispatched-r1", "dispatched-r2"):
        walls = chains[name]
        per_row = [round(w * 1000.0 / len(rows), 3) for w in walls]
        params = {"rows": len(rows), "lags": list(LAGS),
                  "form": crop_form.key(), "repeats": REPS,
                  "chain_wall_s_per_repeat": walls,
                  "chain_ms_per_consumer_row_per_repeat": per_row}
        if name in extra:
            params["recorders"] = extra[name]["threads"]["recorders"]
            params["dispatcher"] = extra[name]
        case = harness.Case(name, params=params, samples_ms=samples[name],
                            unit="ms per consumer row", note=notes[name])
        run.cases.append(case)
        harness.report(case)
        print(f"      chain {walls} s  ->  {per_row} ms per consumer row")
        run.note(f"arm {name}: {notes[name]}. Chain wall per repeat {walls} "
                 f"s over {len(rows)} consumer rows = {per_row} ms per row.")

    base = values["recomputed"]
    for name, got in values.items():
        if name == "recomputed":
            continue
        shared = sorted(set(base) & set(got))
        bad = [r for r in shared if base[r] != got[r]]
        worst = max((abs(base[r] - got[r]) for r in shared), default=None)
        run.note(f"values, recomputed vs {name}: {len(shared)} rows shared, "
                 f"{len(bad)} disagree, max abs difference {worst}.")
        print(f"[agree] recomputed vs {name}: {len(bad)}/{len(shared)} "
              f"disagree, max abs diff {worst}")

    path = run.write()
    print(f"[wrote] {path}")


if __name__ == "__main__":
    main()
