"""Is a step's positioning derivable from what feeds it, or did it have to declare it?

`nodes.Step.produces` states a name, a kind and a dtype and stops, on the claim
that a step cannot honestly say anything else about its output — its form
follows the crop it was handed and its timebase, origin and access come from
whatever feeds it. One step cannot test that claim: with `lk_flow`'s `(-1, 0)`,
reach, span and the count of admitted inputs are all 1, so a derivation that
trims by any of the three passes and two of the three readings are wrong.

So two steps against one source, with `lag_mhi` chosen because its admitted set
is not its reach — four inputs spanning thirty-one.

Three things it has to show, each killing a different way the claim could be
false:

1. The two extents' heads sit at `listed[reach]`, thirty-nine positions apart
   at these lags. Equal heads would mean the derivation never read `reach` and
   `Extent` is not derivable at all.
2. The two `Positioning` records are equal — same timebase, same origin, same
   access, same window — including when the source is forward-only, where the
   *input's* access is FORWARD and the output's is not. If a step needed a
   different one, positioning is partly the step's to declare.
3. Two bindings of one step at two crops both offer `"flow"`. That is not a
   defect; it is the fact that `Produced.name` is tool-local and qualifying it
   is the pipeline's job — cheap to know now, expensive to discover after the
   name is in the tool contract.

Then the whole producer side end to end: run the step, record where its inputs
landed, and read the values back out through the bound `Output` — a covered row
answering with its value and an uncovered one refusing LATER.

Run: `uv run --group tools --group experiments python 01-derived-binding.py`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "decode-experiments"))
sys.path.insert(0, str(HERE.parent / "tool-experiments"))

import harness  # noqa: E402
from bind import bind, inputs_for  # noqa: E402
from series import Series  # noqa: E402

from sieve.contract.edges import FRAME, Access, Positioning  # noqa: E402
from sieve.contract.nodes import Refusal  # noqa: E402
from sieve.registry import load  # noqa: E402

harness.RESULTS = HERE / "results"

#: Random-access and forward-only spellings of one synthetic recording.
RANDOM_AT = "synthetic:frames=200"
FORWARD_AT = "synthetic:frames=200,access=forward"

#: How many positions to actually compute. Enough to cover both steps' warm-up
#: and leave covered and uncovered rows either side of the boundary.
COMPUTE = 40


def _tool_key(tool) -> str:
    """The durable spelling, folded here because `contract.Tool` has no `key`.

    `experiments/tool-experiments/tools.py` folds name, version and params;
    the production `Tool` never grew the method. Porting it is the pipeline's,
    since only the pipeline knows a node's upstream prefix to fold in front.
    """
    stem = f"{tool.name}@{tool.version}"
    params = tool.role.params
    if not params:
        return stem
    bits = ",".join(f"{k}={params[k]}" for k in sorted(params))
    return f"{stem}({bits})"


def _series_for(tool, upstream, listed, form) -> Series:
    at = upstream.edge.at
    return Series(
        source=RANDOM_AT,
        tool_key=_tool_key(tool),
        form_key=form.key(),
        pts=np.asarray(listed, dtype=np.int64),
        timebase=f"{at.timebase.num}/{at.timebase.den}",
    )


def _frame_output(opened):
    for output in opened.outputs.values():
        if output.edge.kind == FRAME:
            return output
    raise SystemExit(f"{opened.address} offered no frame edge")


def main() -> None:
    run = harness.Run(
        experiment="01-derived-binding",
        question=(
            "Is a step's positioning and extent derivable from what feeds it "
            "plus its own offsets, or does a step have to declare them?"
        ),
    )
    registry = load()
    steps = {tool.name: tool for tool in registry.of_kind("step")}
    for wanted in ("lk flow", "lag mhi"):
        if wanted not in steps:
            raise SystemExit(f"{wanted} did not load: {registry.unavailable}")

    source = registry.source_for(RANDOM_AT, FRAME)
    opened = source.role.open(RANDOM_AT)
    upstream = _frame_output(opened)
    listed = upstream.extent().listed
    rect = upstream.edge.form.rect

    print("01 — derived binding")
    print(f"  source: {RANDOM_AT}, {len(listed)} positions, "
          f"access {upstream.edge.at.access.value}")
    print()

    errors: list[str] = []
    bound = {}
    for name, tool in steps.items():
        form = tool.role.form_for(rect)
        series = _series_for(tool, upstream, listed, form)
        bound[name] = (tool, series, bind(tool.role, upstream, rect, series))

    # ── 1. the heads sit at listed[reach] ────────────────────────────────
    heads = {}
    for name, (tool, _, outputs) in bound.items():
        reach = tool.role.reach
        head = next(iter(outputs.values())).extent().listed[0]
        heads[name] = head
        if head != listed[reach]:
            errors.append(
                f"{name}: head {head} is not listed[{reach}] = {listed[reach]}")
        print(f"  {name}: offsets {tool.role.offsets}, reach {reach}, "
              f"admits {len(tool.role.offsets)}, head {head}")
    # In rows, not in positions. Written the other way first and it failed:
    # the heads came out 29029 apart rather than 29, because a position is a
    # pts in the stream's timebase and these are 1001 ticks each (ADR-0004).
    # The reading that sounds right in frame counts is wrong in the
    # coordinate the contract actually uses, and it is wrong by a factor
    # nothing would have flagged.
    spread = listed.index(heads["lag mhi"]) - listed.index(heads["lk flow"])
    expected = steps["lag mhi"].role.reach - steps["lk flow"].role.reach
    if spread != expected:
        errors.append(f"heads are {spread} rows apart, not {expected}")
    print(f"  heads are {spread} rows apart, "
          f"{heads['lag mhi'] - heads['lk flow']} ticks")
    run.note(f"heads at listed[reach]: {heads}, {spread} rows apart")
    print()

    # ── 2. one positioning, derived, and not the input's ─────────────────
    at = upstream.edge.at
    want_at = Positioning(timebase=at.timebase, origin=at.origin,
                          access=Access.RANDOM, window=None)
    for name, (_, _, outputs) in bound.items():
        for product, output in outputs.items():
            if output.edge.at != want_at:
                errors.append(f"{name}.{product}: {output.edge.at} != {want_at}")

    forward = registry.source_for(FORWARD_AT, FRAME).role.open(FORWARD_AT)
    up_forward = _frame_output(forward)
    tool = steps["lk flow"]
    forward_form = tool.role.form_for(up_forward.edge.form.rect)
    forward_bound = bind(
        tool.role, up_forward, up_forward.edge.form.rect,
        _series_for(tool, up_forward, up_forward.extent().listed, forward_form))
    forward_at = next(iter(forward_bound.values())).edge.at
    if up_forward.edge.at.access is not Access.FORWARD:
        errors.append("the forward source did not declare FORWARD")
    if forward_at.access is not Access.RANDOM:
        errors.append(f"over a FORWARD input the output was {forward_at.access}")
    print(f"  positioning derived: {want_at.access.value}, "
          f"window {want_at.window}, timebase "
          f"{want_at.timebase.num}/{want_at.timebase.den}, "
          f"origin {want_at.origin.value}")
    print(f"  over a {up_forward.edge.at.access.value} input, the step's "
          f"output is {forward_at.access.value}")
    run.note(f"one positioning for both steps: {want_at.access.value}, "
             f"window={want_at.window}; over a FORWARD input the output is "
             f"{forward_at.access.value}")
    forward.close()
    print()

    # ── 3. two crops, one product name ───────────────────────────────────
    x, y, w, h = rect
    other = (x, y, max(2, w // 2), max(2, h // 2))
    tool = steps["lk flow"]
    left_form, right_form = tool.role.form_for(rect), tool.role.form_for(other)
    left = bind(tool.role, upstream, rect,
                _series_for(tool, upstream, listed, left_form))
    right = bind(tool.role, upstream, other,
                 _series_for(tool, upstream, listed, right_form))
    if set(left) != set(right):
        errors.append("two crops of one step offered different names")
    print(f"  two crops of {tool.name!r} both offer {sorted(left)} — "
          f"{left_form.key()} vs {right_form.key()}")
    run.note(f"product names are tool-local: two crops both offer "
             f"{sorted(left)}; qualification is the pipeline's")
    print()

    # ── the producer side, end to end ────────────────────────────────────
    tool, series, outputs = bound["lk flow"]
    output = outputs["flow"]
    head_row = tool.role.reach
    samples: list[float] = []
    for row in range(head_row, head_row + COMPUTE):
        frames = inputs_for(tool.role, upstream, rect, row, listed)
        if frames is None:
            errors.append(f"row {row} could not be fed")
            continue
        start = time.perf_counter()
        field = tool.role.field(frames, row)
        value = float(tool.role.reduce(field))
        samples.append((time.perf_counter() - start) * 1000.0)
        # Where its inputs landed, and never from anything that draws.
        series.put(row, value)

    covered = output.read(listed[head_row])
    uncovered = output.read(listed[head_row + COMPUTE + 1])
    if not covered.delivered:
        errors.append(f"a covered row refused {covered.refusal}")
    if uncovered.refusal is not Refusal.LATER:
        errors.append(f"an uncovered row answered {uncovered!r}, not LATER")
    if not isinstance(covered.frame, float):
        errors.append(f"a value edge answered with {type(covered.frame)}")
    print(f"  computed {len(samples)} rows from {listed[head_row]}; "
          f"covered row reads {covered.frame:.4f}, "
          f"uncovered row refuses {uncovered.refusal.value}")
    run.note("a value edge's payload arrives in `Answer.frame` — the record "
             "holds a float under a field named for pixels")

    case = harness.Case(
        "lk-flow-through-a-binding",
        params={"source": RANDOM_AT, "rows": COMPUTE,
                "form": left_form.key()},
        samples_ms=samples,
        unit="ms per position",
        note="field and reduce only; the read is not timed",
    )
    run.cases.append(case)
    harness.report(case)
    print()

    if errors:
        for error in errors[:10]:
            print(f"  ERROR: {error}")
        run.note(f"{len(errors)} errors — the derivation does not hold")
    else:
        print("  all three checks passed; the derivation holds for two steps")
        run.note("heads, positioning and end-to-end read all held")

    opened.close()
    print()
    print(f"result: {run.write()}")


if __name__ == "__main__":
    main()
