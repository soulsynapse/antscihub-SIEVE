---
title: Whether the worker split should be a controller rather than a constant
status: deferred
after: [ledger-producers]
serves: [A2]
opened: 2026-07-28
gated_on: >
  evidence that the fixed constants are wrong on machines that are not the
  reference — concretely, pool-utilisation samples from more than one class of
  machine showing the declared split leaving a pool starved or idle. The
  sensor landed 2026-07-28
  (docs/completed-todo/2026.07.28-ledger-producers.md), so what is missing is
  no longer instrumentation but a second machine to point it at. A governor
  tuned on argument would oscillate where a fixed constant merely sits at the
  wrong value.
reads:
  - src/sieve/gui/concurrency.py
  - docs/completed-todo/2026.07.28-ledger-producers.md
  - docs/findings/2026.07.28-the-luma-path-has-almost-nothing-left-to-thread.md
---

# Constant, or controller

Raised 2026-07-28 alongside the ledger-producers item
(docs/completed-todo/2026.07.28-ledger-producers.md): "the load
balancing should be automatic, I'm not certain if it is tuned to my machine
it's actually useful." The observability half became that item. This is the
half it deliberately does not do.

`resolve_worker_split` resolves the three pools from one input — core count —
and only ever downward. The constants are measured optima from the reference
class of machine (`PREVIEW_WORKERS` from the luma finding; `DETECTOR_WORKERS`
by its own admission a judgement). The explicit position in
`resolve_worker_split`'s docstring is that more cores must *never* scale the
pools up, because the prefetch optimum is a memory-bandwidth property of the
frame buffer rather than a core count — and the 8- and 12-worker measurements
are the evidence that scaling on core count is the mistake.

That reasoning is sound and this item does not contest it. What it questions
is the *converse*: bandwidth being the binding resource is an argument for
not scaling on cores, not an argument for a constant. A machine with
different memory bandwidth has a different optimum, and nothing measures it.

## Why this waits

Three reasons, in descending order of how much they should matter.

1. **One machine's worth of evidence.** The sensor landed 2026-07-28, so the
   original blocker — no per-machine evidence at all — is gone, and what
   replaced it is narrower and just as blocking: every sample so far comes
   from the reference class of machine, which is the class the constants were
   already tuned on. A controller fitted to it would be the constant with more
   moving parts.
2. **A confounded objective.** "Is the split working" is not directly
   observable; what is observable is throughput, and throughput depends on
   what the user is doing. The 2026-07-28 session is the cautionary case: it
   would have scored as total failure on ring hit rate while the ring was, by
   design, not in play — plain playback does not engage `feed_bounds`' fold.
   A controller must condition on mode or it will re-tune against a mode that
   is not running.
3. **Reproducibility.** A session whose worker split drifts is a session
   whose timings cannot be compared to another's, which is a real cost to
   every future finding in `docs/findings/`. Rule 7 says the split cannot
   change *what a result is* — it is not hashed, correctly — but it can make
   two measurements of the same thing disagree for reasons nobody recorded.
   Any controller needs to publish its resolved split alongside every sample,
   or findings taken under it are not comparable.

## The likely shape, when it comes

Not a continuous controller. The cheaper and more defensible form is a
**one-shot calibration**: measure the machine's actual bandwidth-bound
prefetch optimum once, at first run or on demand, cache it against a machine
fingerprint, and let `resolve_worker_split` read that instead of a literal.
That keeps a session's split fixed — reproducibility intact, point 3
answered — while making the constant per-machine rather than per-reference.
It is also the form the existing measurement infrastructure already supports:
the luma sweep that produced `LUMA_WORKER_CAP` is exactly the procedure,
already written, currently run by hand on one machine.

A live governor remains possible after that and should be opened by its own
evidence: a workload where the right split changes *within* a session, which
neither the luma finding nor anything else has yet shown.
