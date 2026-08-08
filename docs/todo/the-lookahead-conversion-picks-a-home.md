---
title: The lookahead conversion picks a home
priority: normal
phase: 3
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py tests/unit/test_plan.py -q -k one_conversion && uv run lint-imports"
opened: 2026-08-07
---

# The lookahead conversion picks a home

`core/tool_base.py` holds `node_warmup_frames`, `node_lookahead_frames` and
`input_warmup_frames` — the last being the per-edge conversion, extracted from
`source_warmup_frames` so a graph walk could fold it, with a docstring arguing
that two implementations of one conversion is exactly what the arrangement
prevents. Its lookahead twin is `_input_lookahead_frames`, and 03.5 put it in
`pipeline/plan.py` because moving a function into the tool contract is a
decision about that contract and the item re-derived a `pipeline` module.

So the symmetric pair is split across two layers by an accident of sequencing.
Either it moves up beside its twin, or `input_warmup_frames` moves down and
`tool_base` keeps only the per-node declarations — and the second is not
obviously worse, since `source_warmup_frames` is the single-path definition the
walk is checked against and it is the only other caller.

What decides it is whether anything outside `pipeline/` folds either side.
Phase 6's `preview.py` is the candidate; if it takes a plan rather than a graph,
nothing does, and `core` is carrying two functions for one consumer.

## The deciding fact has arrived, and it does not settle the direction

`preview.py` landed at 06.2 as `src/sieve/pipeline/preview.py` — inside
`pipeline/`, and it takes a `Pipeline`, building the `Dag` and the
`ExecutionPlan` itself rather than being handed either. So it folds neither
side, and no module outside `pipeline/` does. `core` is carrying the warmup
conversion for one consumer, which is the reading that argues for moving it
down.

What that reading has to answer is the layering: `.importlinter` puts `core`
below `pipeline`, so `input_warmup_frames` cannot move into `plan.py` alone —
`source_warmup_frames` calls it and is the single-path definition the walk is
checked against, so it moves too, and `core/tool_base.py` is left holding only
the per-node declarations. Moving the twin up instead costs nothing at the
layer and leaves `core` where it is. Both are still live; the fact only prices
them.

The criterion is neutral between them: a case spelling `one_conversion`,
asserting that the two conversions are defined in one module — the `__module__`
of the pair, not a hard-coded name — so the item closes whichever way the pair
travels and does not close if it stays split. `lint-imports` is joined to it
because the "moves down" branch is the one that can be made to pass by breaking
a layer, and a green suite would not say so.
