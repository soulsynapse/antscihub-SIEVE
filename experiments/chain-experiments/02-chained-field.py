"""Can a step be fed another step's field, and what does serving that field cost?

Every chain this tree can build is a fan one deep. `pipeline/binding.py` refuses
any upstream whose edge kind is not FRAME, a step's products are values, and
`session._rebind` assembles whatever tools happen to be installed off the head
because there is nothing else it could assemble. The two facts a pipeline
document exists to carry — a topology and a set of values — have no second legal
shape between them.

So: reopen `edges.KINDS` with FIELD, make the want a declaration instead of a
hardcoded kind, and bind `lk flow`'s field to a step that consumes it. The
proposed records are in `bind.py`; this is what tries to break them.

Four things it has to show, each killing a different way the proposal could be
false:

1. **The want is load-bearing in both directions.** A field consumer bound to
   the source's frame edge is refused, and a frame consumer bound to the field
   edge is refused. If either binds, the declaration is decoration and the kind
   check that `pipeline/binding.py` hardcodes today was doing the work.
2. **A field's form does not answer for a frame's.** `nodes.Step` refuses to
   offer the field on exactly this ground: image-sized float32 over the same
   rect would grade EXACT against a uint8 gray frame, and `forms.grade` and
   `store.Frames.dominator` would both wave it through with plausible numbers.
   Spelling the sample format in `Form.pix` has to close that in `grade`, in
   both directions, and separate the two `Form.key()`s that a durable key is
   folded from.
3. **Reach composes.** Over `lk flow` (reach 1) a consumer at lags 30/20/10
   (reach 30) has no honest answer before row 31, not row 30. A binding that
   trimmed by the consumer's own reach alone produces a first row computed from
   an upstream field whose inputs do not exist — one row wrong at the head of
   every chained series, silently.
4. **Held and recomputed agree.** The cache is not allowed to change a number.

Then the cost, which is the reason to run it rather than argue it. A consumer at
those lags asks for each upstream row four times, thirty rows apart. Recomputed,
that is four flow fields per consumer row. Held under ADR-0006's rule — release
what no declaration still admits, which is everything below `row - reach` — it
is one, at the price of holding `reach + 1` fields.

**Frames are held in both cases, deliberately.** Whether a frame cache pays is
`orchestrator-experiments`' question and it is answered
(`docs/findings/2026.08.30-derived-eviction-reproduces-the-fixed-window.md`).
Leaving the frame side to vary would price that again and bury the field
question underneath it, so every frame this needs is resident before either
case is timed and the only thing that differs is whether a *field* is kept.

Run: `uv run --group tools --group experiments python 02-chained-field.py`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "decode-experiments"))
sys.path.insert(0, str(HERE.parent / "tool-experiments"))

import harness  # noqa: E402
from bind import (  # noqa: E402
    FIELD,
    Declared,
    Held,
    Product,
    Wanted,
    bind,
    inputs_for,
)
from series import Series  # noqa: E402

from sieve.contract import forms  # noqa: E402
from sieve.contract.edges import FRAME, VALUE  # noqa: E402
from sieve.contract.forms import Form  # noqa: E402
from sieve.contract.nodes import Answer, Output, Refusal, read_form  # noqa: E402
from sieve.registry import load  # noqa: E402

harness.RESULTS = HERE / "results"

#: Structural checks run here: deterministic, and no decode in the way.
SYNTHETIC = "synthetic:frames=200"
#: The timed cases run on real footage, at the small 462² regime the analysis
#: costs were priced in (`docs/findings/2026.08.21-optical-flow-dominates...`).
FOOTAGE = harness.FOOTAGE / "rep3_intermittent_crop.MP4"

#: The consumer's lags. `lag_mhi`'s shape on purpose: four admitted positions
#: spanning thirty-one, so reach and the count of admitted inputs are different
#: numbers and a derivation trimming by the wrong one fails here.
_LAGS = (30, 20, 10)
_OFFSETS = tuple(sorted(-lag for lag in _LAGS) + [0])

#: Consumer rows computed per case. The reuse ratio approaches four as this
#: grows — over N rows the consumer makes 4N demands of N + reach distinct
#: upstream rows — so a short sweep understates the hold by measuring mostly
#: head. Long enough here to be within a tenth of the asymptote.
COMPUTE = 240


# ── the load: a step that eats fields ────────────────────────────────────────

def _consumed(fields: dict[int, Any], row: int) -> Any:
    """Weighted temporal max of the upstream field over the admitted lags.

    Not a difference: the input is already a measurement, and differencing one
    measurement against an older copy of itself is a second-order quantity
    nobody asked for. The max over a span is what "was there motion anywhere in
    the last thirty positions" means, and it is the reduction that makes the
    lags load-bearing.
    """
    out = np.asarray(fields[row], dtype=np.float32)
    for rank, offset in enumerate(_OFFSETS[:-1]):
        weight = (rank + 1) / len(_LAGS)
        out = np.maximum(out, np.asarray(fields[row + offset],
                                         dtype=np.float32) * weight)
    return out


def _mean(field: Any) -> float:
    return float(np.mean(field))


def consumer() -> Declared:
    """The step under test: wants a field, offers a value."""
    return Declared(
        wants=Wanted(FIELD),
        offsets=_OFFSETS,
        field=_consumed,
        reduce=_mean,
        produces=(Product("motion", VALUE, dtype="float"),),
        params={"lags": "-".join(str(lag) for lag in sorted(_LAGS))},
    )


def producer(tool) -> Declared:
    """`lk flow` as it would declare itself once a field is a kind.

    Its arithmetic verbatim, its frame want made a record, and the field it
    already computes offered as a product instead of drawn and discarded. The
    tool file is not edited: what a tool declares is the question, and editing
    it before the answer is in would re-key every series it has written
    (ADR-0010) for a proposal that might not survive.
    """
    step = tool.role
    return Declared(
        wants=Wanted(FRAME, step.form_for),
        offsets=step.offsets,
        field=step.field,
        reduce=step.reduce,
        produces=(Product("flow", VALUE, dtype="float"),
                  Product("flow field", FIELD, pix="f32")),
        params=step.params,
    )


# ── plumbing ─────────────────────────────────────────────────────────────────

def _tool_key(name: str, version: int, params) -> str:
    stem = f"{name}@{version}"
    if not params:
        return stem
    return f"{stem}({','.join(f'{k}={params[k]}' for k in sorted(params))})"


def _series(step: Declared, name: str, address: str, upstream: Output,
            listed: tuple[int, ...], form: Form) -> Series:
    at = upstream.edge.at
    return Series(
        source=address,
        tool_key=_tool_key(name, 1, step.params),
        form_key=form.key(),
        pts=np.asarray(listed, dtype=np.int64),
        timebase=f"{at.timebase.num}/{at.timebase.den}",
    )


def _frame_output(opened) -> Output:
    for output in opened.outputs.values():
        if output.edge.kind == FRAME:
            return output
    raise SystemExit(f"{opened.address} offered no frame edge")


def _resident(upstream: Output, want: Form, listed: tuple[int, ...],
              rows: range) -> Output:
    """*upstream* with every frame *rows* needs already in RAM.

    The frame side held flat across both cases, so what the timing compares is
    fields and nothing else. Built by reading through the real `Output`, so the
    form it serves is the one the source or the canonical construction produced
    rather than one this file shaped.
    """
    kept: dict[int, Any] = {}
    for row in rows:
        answer = read_form(upstream, listed[row], want)
        if not answer.delivered:
            raise SystemExit(f"row {row} refused {answer.refusal} while warming")
        kept[row] = answer.frame

    ranks = {position: row for row, position in enumerate(listed)}

    def read(position: int | None, form: Form | None = None) -> Answer:
        row = ranks.get(position) if position is not None else None
        held = None if row is None else kept.get(row)
        if held is None:
            return Answer(refusal=Refusal.LATER)
        return Answer(held)

    return Output(edge=upstream.edge, read=read, extent=upstream.extent,
                  starts=upstream.starts)


def _sweep(step: Declared, feeding: Output, rect, rows: tuple[int, ...],
           listed: tuple[int, ...], held: Held | None) -> tuple[list[float],
                                                                list[float]]:
    """Compute *rows* of *step*, returning its values and per-row milliseconds.

    The release is the declaration's: everything below `row - reach` is a row
    no admitted offset can still name, which is
    `orchestrator-experiments/02-derived-eviction.py`'s rule with a field in it
    rather than a frame.
    """
    values: list[float] = []
    samples: list[float] = []
    for row in rows:
        # Inside the timer: releasing is part of what holding costs, and a
        # cache measured without its own bookkeeping is a cache measured
        # favourably.
        start = time.perf_counter()
        if held is not None:
            held.keep_from(row + min(step.offsets))
        fields = inputs_for(step, feeding, rect, row, listed)
        if fields is None:
            raise SystemExit(f"row {row} could not be fed")
        value = float(step.reduce(step.field(fields, row)))
        samples.append((time.perf_counter() - start) * 1000.0)
        values.append(value)
    return values, samples


# ── the experiment ───────────────────────────────────────────────────────────

def structural(registry, errors: list[str], run: harness.Run) -> None:
    """The four checks, on the synthetic source. No decode in the way."""
    steps = {tool.name: tool for tool in registry.of_kind("step")}
    tool = steps["lk flow"]
    source = registry.source_for(SYNTHETIC, FRAME)
    opened = source.role.open(SYNTHETIC)
    upstream = _frame_output(opened)
    listed = upstream.extent().listed
    rect = upstream.edge.form.rect

    up, down = producer(tool), consumer()
    want = up.wants.form_for(rect)
    flow = bind(up, upstream, rect,
                _series(up, "lk flow", SYNTHETIC, upstream, listed, want))
    field_edge = flow["flow field"].edge

    # ── 1. the want is load-bearing, both ways ───────────────────────────
    try:
        bind(down, upstream, rect, _series(down, "field mhi", SYNTHETIC,
                                           upstream, listed, want))
    except ValueError as why:
        print(f"  a field want fed a frame edge: refused — {why}")
    else:
        errors.append("a field want bound to the source's frame edge")
    try:
        bind(up, flow["flow field"], rect,
             _series(up, "lk flow", SYNTHETIC, upstream, listed, want))
    except ValueError as why:
        print(f"  a frame want fed a field edge: refused — {why}")
    else:
        errors.append("a frame want bound to a field edge")

    chained = bind(down, flow["flow field"], rect,
                   _series(down, "field mhi", SYNTHETIC, flow["flow field"],
                           listed, field_edge.form))
    print(f"  {down.wants.kind} want bound to {field_edge.name!r}: "
          f"offers {sorted(chained)}")
    run.note("the want is load-bearing: a field consumer refuses a frame edge "
             "and a frame consumer refuses a field edge; the matched pair binds")

    # ── 2. a field's form does not answer for a frame's ──────────────────
    frame_form = want
    field_form = field_edge.form
    if (field_form.rect, field_form.out) != (frame_form.rect, frame_form.out):
        errors.append("the field is not at the form the step read its input in")
    for have, asked, label in ((frame_form, field_form, "gray answering f32"),
                               (field_form, frame_form, "f32 answering gray")):
        if forms.grade(have, asked) is not None:
            errors.append(f"{label} graded {forms.grade(have, asked)}, not None")
    if frame_form.key() == field_form.key():
        errors.append(f"one key for both: {frame_form.key()}")
    print(f"  same geometry, two keys: {frame_form.key()} vs "
          f"{field_form.key()}; neither grades against the other")
    run.note("spelling the sample format in Form.pix closes the collision "
             "nodes.Step refused a field edge over — grade() is None both ways "
             "and the two Form.key()s differ")

    # ── 3. reach composes ────────────────────────────────────────────────
    head = chained["motion"].extent().listed[0]
    composed = up.reach + down.reach
    if head != listed[composed]:
        errors.append(f"chained head {head} is not listed[{composed}] "
                      f"= {listed[composed]}")
    # The field itself answers at row 30 — the producer's reach is 1, so of
    # course it does. What fails there is the *consumer*, whose oldest lag
    # lands on row 0, and that is the row a binding trimming by the consumer's
    # own reach would have called its head.
    naive = inputs_for(down, flow["flow field"], rect, down.reach, listed)
    honest = inputs_for(down, flow["flow field"], rect, composed, listed)
    if naive is not None:
        errors.append(f"the consumer was fed at row {down.reach}, whose oldest "
                      f"lag is row {down.reach + min(_OFFSETS)}")
    if honest is None:
        errors.append(f"the consumer could not be fed at row {composed}")
    print(f"  reach composes: {up.reach} + {down.reach} = {composed}; "
          f"head {head} = listed[{composed}], the consumer cannot be fed at "
          f"row {down.reach} and can at row {composed}")
    run.note(f"reach composes across a chain: the head sits at "
             f"listed[{composed}], not listed[{down.reach}]")

    opened.close()


def timed(registry, errors: list[str], run: harness.Run) -> None:
    """Recompute against hold, on real footage, with frames resident in both."""
    if not FOOTAGE.exists():
        run.note(f"{FOOTAGE.name} absent — the timed cases did not run")
        print(f"  {FOOTAGE} absent; structural checks only")
        return
    run.add_footage(FOOTAGE)
    steps = {tool.name: tool for tool in registry.of_kind("step")}
    address = str(FOOTAGE)
    source = registry.source_for(address, FRAME)
    opened = source.role.open(address)
    upstream = _frame_output(opened)
    listed = upstream.extent().listed
    rect = upstream.edge.form.rect

    up, down = producer(steps["lk flow"]), consumer()
    want = up.wants.form_for(rect)
    first = up.reach + down.reach
    rows = tuple(range(first, first + COMPUTE))
    needed = range(0, rows[-1] + 1)

    warm = _resident(upstream, want, listed, needed)
    print(f"  {len(needed)} frames resident at {want.key()}")

    results = {}
    for label, held in (("recomputed", None), ("held", Held())):
        flow = bind(up, warm, rect,
                    _series(up, "lk flow", address, warm, listed, want),
                    held=held)
        field_out = flow["flow field"]
        values, samples = _sweep(down, field_out, rect, rows, listed, held)
        results[label] = (values, samples, held)
        case = harness.Case(
            f"consumer-{label}",
            params={"source": FOOTAGE.name, "rows": COMPUTE,
                    "lags": list(_LAGS), "form": want.key(),
                    "frames_resident": len(needed)},
            samples_ms=samples,
            unit="ms per consumer row",
            note=("upstream field recomputed per demand"
                  if held is None else
                  "upstream field held, released below row - reach"),
        )
        run.cases.append(case)
        harness.report(case)

    # ── the floor ────────────────────────────────────────────────────────
    # Every field already held and nothing released, so the only work left is
    # the consumer's own four maximums. Not a proposal — 270 resident fields
    # is what the hold exists to avoid — but the number the other two are
    # read against: what the hold cannot remove because it was never the
    # producer's.
    floor_held = Held()
    flow = bind(up, warm, rect,
                _series(up, "lk flow", address, warm, listed, want),
                held=floor_held)
    field_out = flow["flow field"]
    for row in range(min(rows) + min(_OFFSETS), max(rows) + 1):
        field_out.read(listed[row])
    _, floor = _sweep(down, field_out, rect, rows, listed, None)
    case = harness.Case(
        "consumer-arithmetic-only",
        params={"source": FOOTAGE.name, "rows": COMPUTE, "lags": list(_LAGS),
                "form": want.key(), "fields_resident": floor_held.computed},
        samples_ms=floor,
        unit="ms per consumer row",
        note="every upstream field pre-held and nothing released — the floor, "
             "not a proposal",
    )
    run.cases.append(case)
    harness.report(case)

    # ── 4. the cache did not change a number ─────────────────────────────
    left, right = results["recomputed"][0], results["held"][0]
    worst = max(abs(a - b) for a, b in zip(left, right))
    if worst != 0.0:
        errors.append(f"held and recomputed disagree by {worst:g}")
    print(f"  held and recomputed agree to {worst:g}")

    held = results["held"][2]
    asks = held.computed + held.reused
    reuse = asks / held.computed if held.computed else 0.0
    print(f"  {asks} field demands over {COMPUTE} rows: {held.computed} "
          f"computed, {held.reused} reused ({reuse:.2f}x), peak "
          f"{held.peak_rows} fields / {held.peak_bytes / 1e6:.1f} MB")
    # What the hold costs where the footage is actually large. An
    # extrapolation by pixel count and labelled one: nothing here decoded a
    # 5.3K frame, and the per-field bytes are the only part of this that
    # scales without measuring.
    uncut = held.peak_bytes * (5312 * 2988) / (want.out[0] * want.out[1])
    run.note(f"a consumer at lags {_LAGS} asks for each upstream field "
             f"{reuse:.2f} times; holding them costs {held.peak_rows} fields "
             f"({held.peak_bytes / 1e6:.1f} MB at {want.out[0]}x{want.out[1]} "
             f"float32) and releases on the declaration")
    run.note(f"extrapolated by pixel count, not measured: the same {held.peak_rows} "
             f"fields at 5312x2988 float32 would be {uncut / 1e9:.2f} GB")
    print(f"  the same hold at 5312x2988 float32: {uncut / 1e9:.2f} GB "
          f"(extrapolated by pixel count)")

    quick = harness.quantiles(results["recomputed"][1])
    kept = harness.quantiles(results["held"][1])
    base = harness.quantiles(floor)
    if quick and kept and kept["p50"] > 0:
        run.note(f"recomputed p50 {quick['p50']:.2f} ms/row vs held "
                 f"{kept['p50']:.2f} ms/row — {quick['p50'] / kept['p50']:.2f}x, "
                 f"frames resident in both")
        # Why the speedup is smaller than the reuse ratio, said once here so
        # nobody has to derive it from two numbers that look inconsistent.
        run.note(f"the consumer's own arithmetic is {base['p50']:.2f} ms/row and "
                 f"the hold cannot touch it: of the {quick['p50'] - base['p50']:.2f} "
                 f"ms/row the producer costs, holding removes "
                 f"{quick['p50'] - kept['p50']:.2f} — which is why {reuse:.2f}x "
                 f"reuse buys {quick['p50'] / kept['p50']:.2f}x wall time")
        print(f"  floor {base['p50']:.2f} ms/row is the consumer's own "
              f"arithmetic; the producer costs "
              f"{quick['p50'] - base['p50']:.2f} recomputed and "
              f"{kept['p50'] - base['p50']:.2f} held")
    opened.close()


def main() -> None:
    run = harness.Run(
        experiment="02-chained-field",
        question=(
            "Can a step declare that it wants a field and bind to another "
            "step's, and does holding that field beat recomputing it?"
        ),
    )
    registry = load()
    steps = {tool.name: tool for tool in registry.of_kind("step")}
    if "lk flow" not in steps:
        raise SystemExit(f"lk flow did not load: {registry.unavailable}")

    print("02 — a step fed another step's field")
    print()
    errors: list[str] = []
    structural(registry, errors, run)
    print()
    timed(registry, errors, run)
    print()

    if errors:
        for error in errors[:10]:
            print(f"  ERROR: {error}")
        run.note(f"{len(errors)} errors — the proposal does not hold as written")
    else:
        print("  all four checks passed; a declared want binds a field")
        run.note("want, form separation, composed reach and cache equivalence "
                 "all held")
    print()
    print(f"result: {run.write()}")


if __name__ == "__main__":
    main()
