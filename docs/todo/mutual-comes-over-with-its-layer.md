---
title: mutual/ comes over with its layer
step: "02.0.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_machine.py tests/unit/test_pool_meter.py tests/unit/test_ledger_sensors.py -q && uv run lint-imports"
opened: 2026-08-07
---

# mutual/ comes over with its layer

All four modules of `mutual/` verbatim (PLAN.md, porting discipline), because
`decode/` reads three of them and 02.1 cannot be verbatim without them. The
package is 682 lines whose only dependency outside the standard library is
`psutil`, and its only internal edge is `shares -> machine`, so there is no
part of it that arrives speculatively.

It brings its seat in the stack with it, and that is the half of this item
that is not a copy:

- `.importlinter` gains `sieve.mutual` between the `decode | storage` row and
  `sieve.core`, which is where v2 seats it, and `core-purity`'s
  `source_modules` gains it — v2's contract is named "core and mutual import
  no toolkit, no codec, no processes" and the second half of that name is the
  reason `machine.py` may read `psutil` while `core/` may not.
- The comment above the layers block currently says whether `mutual` ports at
  all is Phase 5's question. PLAN.md answered it; the comment is wrong once
  this lands, not merely stale, and it goes.
- `LAYER_ORDER` in `scripts/doc_index.py` follows `.importlinter` by its own
  docstring, so it gains the same entry or `SCAFFOLD.md` refuses to render.
- `psutil` joins `pyproject.toml`'s runtime dependencies with the reason
  beside it, since `machine.py` is shipped code and not a test helper.

The three test files are v2's own and port unchanged. `test_concurrency.py`
is not among them: it imports `sieve.gui.concurrency`, so its subject is a
consumer that does not exist here.

## The blocker (2026-08-07)

Everything above landed and diffs byte-identical against the v2 blobs. The
`done_when` invocation still fails on one assertion, and the porting
discipline forbids the edit that would clear it, so this stops here for the
reviewer.

`test_machine.py`'s `test_the_session_rss_reading_is_real_and_monotone_in_
allocation` opens with `assert before > 64 * MIB`. That number measures the
pytest session's import footprint, not the resolver: the same test passes
under `uv run pytest -q` over the whole v3 suite and fails under the
three-file selection `done_when` names, and v2's own bare session cleared the
threshold by 20 KB. The measurements are in
`findings/2026.08.07-the-rss-floor-measures-the-test-session-not-the-resolver.md`.

The question: the floor is a sanity guard against a fabricated constant, and
the monotonicity assertion three lines below it — allocate 64 MB, touch every
page, the reading must move by 32 MB — carries that claim on its own and
passes. Does the floor come out, drop to something v3's environment can
actually meet, or does `done_when` name the whole suite instead? Any of the
three is an edit to a ported test or to a criterion, which is the reviewer's
to make and not this run's.
