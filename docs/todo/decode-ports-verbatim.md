---
title: decode/ ports verbatim
step: "02.1"
status: deferred
gated_on: "a ruling on two phase-order questions: whether mutual/ comes over with decode/, and where write_ffv1 lands for test_decode.py's NTSC fixture"
done_when: "uv run pytest tests/integration/test_decode.py tests/unit/test_decode_workers.py -q"
opened: 2026-08-06
---

# decode/ ports verbatim

All six modules of `decode/`, byte-identical modulo imports (PLAN.md, porting
discipline); the test files above port with them and run on
`synthetic_video` (00.4). ffmpeg presence is the environment's problem, not
the port's — if it is missing, that is a blocker note at the bottom of this
item, never a softened test.

## Deferred 2026-08-07: the criterion reaches past `decode/` three ways

Read at v2 `main` (671aa8a). None of the three is a spelling difference, so
none is the proceed-against-evident-intent case.

**`tests/unit/test_decode_format.py` is not a decode test.** It imports
`sieve.backend.dispatch` (PLAN.md drops `backend/` outright),
`core.filter_base` + `filter_registry` (01.2 ported `tool_base` *cut*, and
`ParamsBase`/`CostEstimate`/`TableSpec` are not all of what came over),
`core.pipeline_model` (Phase 3, re-derived as schema v1 under
`adr/v2-does-not-import.md`), and `pipeline.{dag,cache_key,executor,plan}` —
whose ports are 02.2 and 02.3. Its three classes are `TestNeedsChroma`,
`TestSourceKey`, `TestTheExecutorRefusesADisagreement`; the subjects are
`graph_needs_chroma`, `source_key`, and `FormatMismatchError`. It never
touches `synthetic_video` — it runs on a `_OneFrame` fake. What it is really
testing is the format contract *between* decode and the executor, which is
why it was written here in v2, and it cannot go green until the executor
exists. Either it moves to 02.3 or its chroma half splits out; both are
decisions.

**`tests/integration/test_decode.py` needs `storage/crop_writer.py`.** It
calls `write_ffv1` to synthesize the NTSC-rate file that `TestTheSourceRate`
reads. PLAN.md puts `crop_writer.py` in Phase 4 with `crop`. The dependency
is one fixture, so this one is the closest to clerical — but the fix is
either porting an unnamed file or rewriting a fixture, and the discipline
refuses both without a ruling.

**`decode/` does not stand alone.** `ffmpeg.py` imports
`sieve.mutual.machine.available_cpus`, `mutual.pool_meter.PoolMeter`, and
`mutual.shares.PREVIEW_WORKERS`; `prefetch.py` imports the first two and
re-exports `available_cpus` deliberately. `test_decode_workers.py` is
entirely about `resolve_workers`, so the cap constants are its subject, not
an incidental import. PLAN.md Phase 5 says `mutual/` "ports only if a command
reads it" — decode reads it, two phases early. Verbatim therefore means
carrying four unnamed files (`mutual/{__init__,machine,pool_meter,shares}.py`),
which "no files beyond what the item names" forbids.

Nothing was written to `src/` or `tests/`.

## Reviewed 2026-08-07: one of the three was the criterion's to fix

All three were re-derived against v2 `main` (671aa8a) and PLAN.md and all
three hold. They are not the same kind of problem, and only the first was a
reviewer's to settle.

`test_decode_format.py` is struck from `done_when`. Every one of its cases
imports a module that does not exist after this item — the strongest form of
the test the 01.2 amendment established — and its subjects are `dag`,
`cache_key`, and `executor`, which 02.2 and 02.3 build. It does not simply
move there: it also needs `backend/` (dropped), `filter_base`/
`filter_registry` under their v2 names, and `pipeline_model` (Phase 3), so it
is a re-derivation and not a port, and it is now a pool item
(`the-decode-executor-format-contract-is-rederived.md`) rather than a line in
02.3's criterion.

The other two are phase-order rulings, not criterion defects, so the item
stays `deferred` on them. Striking `test_decode.py` would strike this item's
whole subject, and pulling `mutual/` or `crop_writer.py` forward is a change
to PLAN.md's order — the reviewer may edit a criterion, not the plan. The
underlying tension is in PLAN.md itself: the port disposition lists `decode/*`
as verbatim while Phase 5 holds `mutual/` "only if a command reads it", and
`decode/ffmpeg.py` reads it. One of those two sentences has to give.
