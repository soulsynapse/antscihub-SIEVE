---
title: A tool's declaration is asserted by nothing
priority: high
phase: 2
status: open
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
