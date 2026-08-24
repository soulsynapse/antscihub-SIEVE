"""Is a declaration a fetch plan, or just a description of one?

P4 of `docs/archive/2026.08-substrate-port.md`. ADR-0006 says a step declares the inputs
it admits as a function of the position being computed, that the justification
is scheduling fetches rather than conserving memory, and that **a re-fetch the
declaration predicted is a defect while a re-fetch it could not have predicted
is only a fetch.** That last sentence is the whole thing, and until this file it
was a sentence: nothing counted the difference, so an avoidable decode looked
exactly like the store being slow — which is the mistake the tool folder records
as having cost it a day.

The trap the ADR calls pathological is the one worth building a check around.
`needs(row)` is the point set: what must be resident to evaluate one position.
`residency(active, rows)` is the working set: what may not be evicted while
serving a horizon. They are different numbers whenever offsets are sparse, and
honouring the point set for a moving playhead costs a fetch per offset per
position — worse than having no declaration at all. `--broken` makes exactly
that substitution, and the predicted-re-fetch count is what reports it.

Six cases, none needing footage. The last one is the first time P1 through P4
run together.

**sets** — `needs` is the point set and `reach` is how far back the oldest
input sits, and for a sparse step those are different numbers. A step holding
three fixed lags and the current row admits four inputs and spans thirty-one;
one integer cannot be both.

**union** — `residency` over a run of positions closes the gaps between sparse
offsets, so retention converges on a window around the playhead. Over a single
position it stays sparse, which is the case where the playhead is stationary
and nothing is under pressure.

**forms** — residency is over `(row, form key)` pairs, not rows. Two steps
wanting different pictures of one instant need different arrays, and a store
unioning by row alone would think one satisfied the other.

**keys** — a tool key folds the parameters its field actually uses and excludes
anything downstream of the series. Folding a display threshold would invalidate
work whose own inputs never changed.

**classes** — the same arithmetic lands in different cost classes against
different fetches, which is what falsified declared cost classes and produced
ADR-0007. Checked as a property rather than against a number: a step that is
free beside an expensive fetch need not be free beside a cheap one.

**refetch** — the integration case, and the one with a number in it. A playhead
walks a run of positions; residency is handed to the store as its protected set;
every fetch that misses is charged to the ledger as a predicted re-fetch if the
declaration named it and as an ordinary fetch if it did not. Under the union the
predicted count is zero. Under the point set it is not, and the difference is
the pathology stated with a figure instead of an adjective.

The budget is deliberately smaller than the step's own span. That matters more
than it looks: with room to spare, plain recency holds the working set by
accident, the protected set never decides anything, and the union and the point
set come out identical — a version of this case with a comfortable budget passed
under `--broken` and was proving nothing.

`--broken` replaces `residency` with the point set at the current position.

Run:
    uv run --group experiments python experiments/substrate-checks/05-declarations.py
    uv run --group experiments python experiments/substrate-checks/05-declarations.py --broken
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis import tool as tool_mod  # noqa: E402
from sieve.analysis.tool import (  # noqa: E402
    BUDGETED,
    COMMIT,
    FREE,
    Tool,
    analysis_form,
    classify,
    residency,
)
from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.frame.form import build  # noqa: E402
from sieve.session.ledger import PREDICTED_FETCH, Ledger  # noqa: E402
from sieve.store.resident import ResidentStore  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 600
CROP = (0, 0, 64, 48)
FRAME_BYTES = 64 * 48


def sparse_tool(name: str = "mhi", lags=(30, 20, 10)) -> Tool:
    """The case the point set gets wrong: a handful of inputs spanning many."""
    offsets = tuple(sorted(-lag for lag in lags) + [0])
    return Tool(name=name, form_for=analysis_form("gray"), offsets=offsets,
                field=lambda frames, row: None,
                params={"lags": "-".join(str(lag) for lag in sorted(lags))})


def dense_tool(name: str = "absdiff") -> Tool:
    return Tool(name=name, form_for=analysis_form("gray"), offsets=(-1, 0),
                field=lambda frames, row: None)


def point_set_residency(active, rows):
    """`residency` as the point set — the substitution ADR-0006 forbids.

    Kept here as the thing being argued against. It looks like a tightening:
    hold exactly what the current position needs and nothing more. What it
    actually does for a moving playhead is discard, at every step, the inputs
    the next step is about to want.
    """
    if isinstance(rows, int):
        rows = (rows,)
    last = list(rows)[-1]
    return {(need, form.key())
            for tool, form in active for need in tool.needs(last)}


def case_sets(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    sparse = sparse_tool()
    if sparse.needs(100) != (70, 80, 90, 100):
        bad.append(f"needs(100) said {sparse.needs(100)}")
    if sparse.reach != 30:
        bad.append(f"reach said {sparse.reach}")
    if len(sparse.needs(100)) == sparse.reach + 1:
        bad.append("the admitted set and the span are the same number; this "
                   "step is not sparse and the case is not testing what it "
                   "says")

    dense = dense_tool()
    if dense.needs(5) != (4, 5) or dense.reach != 1:
        bad.append(f"the dense step declared {dense.needs(5)} / {dense.reach}")
    run.note(f"sets: the sparse step admits {len(sparse.needs(100))} inputs "
             f"spanning {sparse.reach + 1} rows — one integer cannot be both")
    return "sets (admitted is not spanned)", 2, bad


def case_union(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    sparse = sparse_tool()
    form = sparse.form_for(CROP)
    active = [(sparse, form)]

    still = residency(active, 100)
    if len(still) != 4:
        bad.append(f"a stationary playhead needs {len(still)} rows, not 4")

    horizon = range(100, 140)
    moving = residency(active, horizon)
    rows = sorted(row for row, _ in moving)
    if len(rows) != len(set(rows)):
        bad.append("the union carries duplicates")
    # the claim: over a run of consecutive positions the union closes the gaps
    # between sparse offsets, so retention converges on a plain window
    gaps = [b - a for a, b in zip(rows, rows[1:]) if b - a > 1]
    if gaps:
        bad.append(f"the union over 40 consecutive positions still has gaps "
                   f"{gaps[:5]}")
    if rows[0] != 70 or rows[-1] != 139:
        bad.append(f"the union spans {rows[0]}..{rows[-1]}, expected 70..139")
    run.note(f"union: 40 consecutive positions of a step with offsets "
             f"{sparse.offsets} unions to a contiguous {rows[0]}..{rows[-1]} — "
             "sparse at a point, a window over a run")
    return "union (a run closes the gaps)", len(rows), bad


def case_forms(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    grey = dense_tool("a")
    colour = Tool(name="b", form_for=analysis_form("bgr"), offsets=(0,),
                  field=lambda frames, row: None)
    active = [(grey, grey.form_for(CROP)), (colour, colour.form_for(CROP))]
    held = residency(active, 50)

    forms = {form_key for _, form_key in held}
    if len(forms) != 2:
        bad.append(f"two steps at different forms produced {len(forms)} form "
                   "keys")
    if (50, grey.form_for(CROP).key()) not in held:
        bad.append("the grey step's own instant is not in the residency")
    if len({row for row, _ in held}) >= len(held):
        bad.append("residency is keyed by row alone; one form would satisfy "
                   "the other")
    run.note(f"forms: {len(held)} pairs over {len({r for r, _ in held})} rows "
             "— an input is held in a form, not merely at an instant")
    return "forms (pairs, not rows)", len(held), bad


def case_keys(run: Run) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    plain = Tool(name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
                 field=lambda f, r: None)
    fast = Tool(name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
                field=lambda f, r: None, params={"preset": "fast"})
    medium = Tool(name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
                  field=lambda f, r: None, params={"preset": "medium"})
    if plain.key() != "dis":
        bad.append(f"a step with no params keyed as {plain.key()!r}")
    if fast.key() == medium.key():
        bad.append("two presets share a key")
    if fast.key() != "dis(preset=fast)":
        bad.append(f"key spelled {fast.key()!r}")

    # order must not reach the key, or two runs of one configuration disagree
    a = Tool(name="t", form_for=analysis_form(), offsets=(0,),
             field=lambda f, r: None, params={"x": 1, "y": 2})
    b = Tool(name="t", form_for=analysis_form(), offsets=(0,),
             field=lambda f, r: None, params={"y": 2, "x": 1})
    if a.key() != b.key():
        bad.append(f"parameter order reached the key: {a.key()} vs {b.key()}")
    run.note("keys: params the field uses are folded, order is not, and "
             "anything downstream of the series is deliberately absent")
    return "keys (folds inputs, not readouts)", 4, bad


def case_classes(run: Run) -> tuple[str, int, list[str]]:
    """A class belongs to the pairing, so one field must land in two of them."""
    bad: list[str] = []
    field_ms, period_ms, paint_ms = 6.0, 41.7, 4.0
    expensive_fetch, cheap_fetch = 120.0, 0.05

    beside_expensive = classify(field_ms, expensive_fetch, period_ms, paint_ms)
    beside_cheap = classify(field_ms, cheap_fetch, period_ms, paint_ms)
    if beside_expensive == beside_cheap:
        bad.append(f"the same field landed in {beside_expensive} against both "
                   "fetches; a cost class is supposed to belong to the pairing")
    if beside_expensive != FREE:
        bad.append(f"beside a {expensive_fetch} ms fetch a {field_ms} ms field "
                   f"classed {beside_expensive}, not {FREE}")
    if beside_cheap not in (BUDGETED, COMMIT):
        bad.append(f"beside a {cheap_fetch} ms fetch it classed {beside_cheap}")

    if classify(500.0, cheap_fetch, period_ms, paint_ms) != COMMIT:
        bad.append("a field far larger than the period did not class commit")
    # what is left of the period once the fetch and the drawing are removed,
    # not the period alone: a step that fits the period and not the drawing
    # beside it does not fit
    tight = period_ms - cheap_fetch - paint_ms
    if classify(tight + 1, cheap_fetch, period_ms, paint_ms) != COMMIT:
        bad.append("budgeted was measured against the period rather than what "
                   "was left of it")
    run.note(f"classes: {field_ms} ms of field is {beside_expensive} beside a "
             f"{expensive_fetch} ms fetch and {beside_cheap} beside a "
             f"{cheap_fetch} ms one — the same arithmetic, two classes")
    return "classes (belongs to the pairing)", 5, bad


def case_refetch(run: Run, broken: bool) -> tuple[str, int, list[str]]:
    """Walk a playhead and count the re-fetches the declaration predicted."""
    bad: list[str] = []
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    book = Ledger()
    tool = sparse_tool()
    form = tool.form_for(CROP)
    active = [(tool, form)]
    # Two numbers chosen so the case can actually distinguish the two
    # residencies, and both were wrong on the first attempt.
    #
    # The budget must sit below what plain recency would hold anyway. This
    # step touches four rows per position and its oldest input is thirty back,
    # so about thirty-one rows are in flight; give an LRU more than that and it
    # keeps the working set by accident, protection decides nothing, and the
    # union and the point set come out identical.
    store = ResidentStore(budget_bytes=30 * FRAME_BYTES)

    #: and the horizon must exceed the *closest* gap between lags, or the union
    #: does not close. Over four positions a step at lags 30/20/10 unions to
    #: four clusters of four with six-position holes between them, and a row
    #: sitting in a hole is evicted before it is wanted again — which reads as
    #: the declaration failing when it is the horizon being shorter than the
    #: step reaches.
    horizon = 11
    fetched: set[int] = set()
    refetches = 0
    for playhead in range(100, 300):
        ahead = range(playhead, min(playhead + horizon, ROWS))
        protected = (point_set_residency(active, ahead) if broken
                     else residency(active, ahead))
        declared = {row for row, _ in protected}

        for row in sorted(tool.needs(playhead)):
            if store.get(form.key(), row) is not None:
                continue
            answer = route.at(row)
            if answer is None:
                continue
            if row in fetched:
                refetches += 1
                # whether a re-fetch is a defect or merely a fetch is the
                # declaration's to say, which is the entire point of ADR-0006
                if row in declared:
                    book.waste(PREDICTED_FETCH,
                               f"row {row} for {tool.key()} at {playhead}")
            fetched.add(row)
            store.put(form.key(), row, build(answer[0], form),
                      protected=protected)

    predicted = book.counts()["waste"].get(PREDICTED_FETCH, 0)
    run.note(f"refetch: {len(route.asked)} fetches over 200 positions, "
             f"{refetches} of them re-fetches ({predicted} of those named by "
             f"the declaration in force)"
             + (" [point set]" if broken else " [union]"))
    # The assertion is on re-fetches, not on the named subset. Counting only
    # what a declaration named rewards declaring less: the point set names
    # four rows, so almost nothing it loses is ever charged to it. The claim
    # under test is that an honest declaration makes re-fetches avoidable at
    # all, which is a statement about the total.
    if refetches:
        bad.append(f"{refetches} re-fetches over {len(route.asked)} fetches; "
                   f"{predicted} of them were rows a declaration had named")
    return "refetch (predicted is a defect)", len(route.asked), bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        tool_mod.residency = point_set_residency

    run = Run(
        experiment="P4-declarations" + ("-broken" if broken else ""),
        question="Does a declaration schedule fetches, and is a re-fetch it "
                 "predicted distinguishable from one it could not have?",
    )
    run.note("no footage: a declaration is about which rows in which forms, "
             "and nothing about pixels")
    if broken:
        run.note("RUN WITH --broken: `residency` is replaced by the point set "
                 "at the current position — the substitution ADR-0006 calls "
                 "pathological. `refetch` is expected to FAIL.")

    results = [
        case_sets(run),
        case_union(run),
        case_forms(run),
        case_keys(run),
        case_classes(run),
        case_refetch(run, broken),
    ]

    ok = True
    print(f"{'case':<40} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<40} {checked:>9}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} checked, {len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))

    print()
    for line in run.notes:
        print(f"  · {line}")

    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken run tripped nothing: the point set and the union "
              "agreed, so `refetch` is not demonstrating the pathology it "
              "claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
