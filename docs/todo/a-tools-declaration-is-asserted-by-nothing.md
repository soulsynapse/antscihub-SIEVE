---
title: A tool's declaration is asserted by nothing
priority: high
phase: 2
status: awaiting-review
gated_on: nothing
done_when: 'uv run pytest tests/unit -k "mode_is_what_the_run_does or element_is_what_the_run_emits or a_version_bump_moves_the_key" -q'
opened: 2026-08-07
---

# A tool's declaration is asserted by nothing

Tools declare `element`, `mode`, `version`, `primary_params` and `caption` in
their `register_tool` call, and mutating each in turn on `crop` — `PRESERVED` to
`AGGREGATED`, `STREAMING` to `WINDOWED`, `primary_params` and `caption` to
empty, `version` to `2.0.0` — left the whole unit suite green when this was
measured. 04.5's sweep over `temporal_baseline` killed `element`,
`settling_epsilon` and `stateful`; the rest survived, including the *value* of a
`param_stereotypes` entry, since 01.4 pinned that every field has a stereotype
and not that it has the right one.

Two of them are load-bearing rather than descriptive. `element` is what `dag.py`
reads to decide an edge is legal and `mode` is what the executor branches on, so
a tool declaring the wrong one produces a graph that validates, runs, and is
wrong about what it computed. `version` is worse quietly: it is in the cache
key, so a wrong value serves another build's results.

An earlier draft of this item asked for a table in the test file, one row per
tool, where adding a tool without adding its row is the failure. That is
refused twice over. It is a shared list every tool after has to enter, which
`adr/a-tool-is-one-file.md` names as the failure mode it exists for; and a table
of expected values asserting that a spec declares what it declares is a
declaration certified by a copy of itself, which is the last clause of
`adr/declared-means-verified.md`. The table would also pass forever on a tool
whose declaration is *consistently* wrong in both places.

Derive instead, and check the claim rather than the transcription.
`tests/unit/test_cache_admission.py` is the worked example already on the tree:
a declaration is checked by running it. The same shape here, generic over
`discover()` — a `STREAMING` tool's output at a frame does not move when the
frames before it are perturbed, and a `WINDOWED` one's does, out to its declared
warmup and no further; `element` and the `accepts`/`emits` dtypes are checked
against what the run actually hands back through the executor. A wrong
declaration fails, not merely a mistyped one.

`version` has no behavioural referent — nothing makes `2.0.0` false — but it has
a consequence, so pin it there: a per-tool cache-key golden, which is an
additive file in the shape `tests/goldens/` already uses and not a row anywhere.

Out of scope, and each for a reason rather than for room. `warmup_kind` belongs
to `docs/todo/every-bounded-declaration-is-run-not-read.md`, which covers the
same hole on the admission side. `caption`, `primary_params` and the stereotype
*values* are the licensed shape in `adr/declared-means-verified.md` — a
declaration whose consumer the plan schedules, standing on a registration-time
validity check until Phase 7's generator arrives — and asserting that `ENUM`
rather than `SCALAR_RANGE` is the *right* kind for a field needs the consumer
that reads it. They are checkable in Phase 7 and not before, which is a reason
to leave them and not a reason to write a table for them now.

## What landed

`tests/unit/test_declarations_run.py`, parametrised over `discover()` and
holding the three cases `done_when` names. Every case runs the tool as a
single-node root graph through the executor, with `run` wrapped by
`dataclasses.replace` so the call widths can be read off without touching a
declaration, and a scratch `ToolRegistry` so the wrapper does not outlive the
call.

`mode` is asserted as the width the executor actually handed the tool: one
frame for `STREAMING`, more than one for `WINDOWED`. The second half is the
clause that had no subject — a `WINDOWED` tool with nothing to window is handed
the same single frame a streaming one gets, so the declaration accumulates
nothing and costs the interactive loop a decode per warm frame. Beside it, a
tool declaring neither state nor warmup has its answer compared across two runs
whose footage differs at one interior frame, which is the leg a spec cannot
satisfy by declaring differently.

`element` is asserted where a run can decide it: `FRAME` as an equivalence in
both directions against "one value came back for an input of many", `BLOCK` as
strictly coarser than its input, `AGGREGATED` as never coarser the wrong way,
and the emitted dtype and channels against `emits`.

**The relation half of `element` is not delivered, and is not deliverable this
way.** `crop` emits strictly fewer elements than it consumed and every one of
them is still a pixel, so no rule over counts separates `PRESERVED` from
`AGGREGATED`; `rescale`'s default scale of 1.0 breaks the other direction, since
a shipped configuration of an aggregating tool emits exactly what it consumed.
The mutant `crop element=PRESERVED ==> AGGREGATED` is confirmed SURVIVED and the
reasoning is
[a finding](../findings/2026.08.07-the-element-relation-is-not-decidable-from-a-run.md).
The test's docstring says the half is open rather than covering it with a rule
that is false of the shelf. `accepts` is likewise not asserted: the footage each
tool is fed is derived from its own `accepts`, so a case over it would be the
copy-of-itself this item refuses.

`version` is pinned as one golden per tool under `tests/goldens/`,
`cache_key_<tool_id>_<version>.txt` — a file a tool adds beside itself, not a
row it enters — plus the bump: the same tool at `9.9.9` must key differently.
The seven cacheable tools have one each; the three `EPSILON` tools are asserted
to have none and to refuse a key, so both sides of `cache_policy` are accounted
for here.

Shown red by mutation rather than by reverting an implementation, there being no
implementation to revert — a gate that passes on a correct tree is the intended
outcome, and what has to fail is the declaration it exists to catch. Six mutants
via `scripts/mutation_sweep.py`, all KILLED: `crop`'s `mode` and `version`,
`block_signal`'s `element` and its `emits` dtype, `detect`'s `element` and
`mode`. A seventh, `crop`'s `run` carrying a frame across calls, is killed by the
perturbation leg.

```
$ uv run pytest tests/unit -k "mode_is_what_the_run_does or element_is_what_the_run_emits or a_version_bump_moves_the_key" -q
..............................                                           [100%]
30 passed, 496 deselected in 2.29s
```

The whole gate is green beside it: `ruff check`, `ruff format --check`,
`lint-imports` (6 contracts kept), 761 tests.
