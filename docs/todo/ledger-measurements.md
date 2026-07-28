---
title: The ledger's three unmeasured numbers
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — the ledger landed with its reserve and worker
  arithmetic marked provisional; each measurement below replaces a stated
  guess with a finding, and none blocks the items consuming the ledger
reads:
  - src/sieve/gui/concurrency.py
  - src/sieve/decode/prefetch.py
  - docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md
---

# The ledger's three unmeasured numbers

The resource ledger (completed 2026-07-27) landed the resolver, the byte
column, and the resolved worker split — with three of its hypotheses left as
stated guesses because each needs the reference footage or a live session,
not a unit test. This item is those measurements, lifted verbatim from the
ledger item so they do not dissolve into its completion entry. Each outcome
is a finding in `docs/findings/`; the ledger's constants then cite it.

- **H2 — the four-worker prefetch optimum does not survive the luma path.**
  The wall was the 47.6 MB buffer; luma is 15.9 MB, so the optimum should
  move. Re-run the worker sweep from the threading finding with `luma=True`.
  Outcome either way is a finding and sets the preview pool's ceiling
  (`INFERRED_WORKER_CAP` is flagged "inherited, not established" on this
  path in `decode/prefetch.py`).
- **H3 — the reserve.** Measure the session's RSS floor (app open, video
  loaded, nothing rendered) on the reference workstation and once on a small
  machine. That number replaces `memory_reserve`'s provisional
  `min(4 GB, max(2 GB, 25%))`.
- **H4 — the ledger accounts for what the process actually holds.**
  Instrument peak RSS over a reference tuning session and compare to
  declared-sum plus reserve. A large gap means an undeclared consumer
  exists; finding it is the point. This is also the measurement
  `docs/todo/cache-eviction.md` says nobody has taken — one instrumented
  session serves both.

The declared-floor test in `tests/unit/test_concurrency.py` and the honest
gap (`UNBOUNDED`) already say what the ledger cannot: until H4 runs, the sum
describes the *declared* session, not necessarily the whole one.
