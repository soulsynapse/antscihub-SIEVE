---
title: The lookahead conversion picks a home
priority: normal
phase: 3
status: open
gated_on: nothing
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
