---
title: Implementation equivalence is measured
status: deferred
opened: 2026-08-06T05:38:55-07:00
priority: unassessed
gated_on: >
  the first second implementation of any filter: a CUDA kernel, a
  filter-equivalent FFmpeg filtergraph route, or any other foreign engine
reads:
  - src/sieve/backend/dispatch.py
  - src/sieve/core/filter_base.py
  - docs/todo/gpu-execution.md
  - ../../../antscihub-SIEVE/docs/ARCHITECTURE.md
  - ../../../antscihub-SIEVE/docs/par/0005-silent-substitution.md
---

# Implementation equivalence is measured

**Why deferred.** Today `src/sieve/backend/dispatch.py` is the route by
which a second backend joins a filter: a kernel registers under the existing
`filter_id` and `version`, distinguished only by backend. That route can select
an implementation, but it does not measure that the second implementation
computes the same result as the reference. The local architecture already keeps
backend identity in cache keys unless `backend_agnostic` is true; this item is
the missing admission bar before any implementation may erase that difference.

The governing argument is not repeated here. The sibling architecture's
[invariant 4](../../../antscihub-SIEVE/docs/ARCHITECTURE.md#the-invariants)
says equivalence is earned by registration-time measurement, and
[PAR-0005](../../../antscihub-SIEVE/docs/par/0005-silent-substitution.md)
draws the line between proof-authorized rewrites and measured foreign
implementations. Read those before editing this item.

**What promotes it.** The trigger is sharper than `docs/todo/gpu-execution.md`:
the first foreign engine is the first second implementation of any filter. Two
plausible claimants now exist rather than one: a CUDA kernel, and the
working-size FFmpeg filtergraph route. In this checkout the FFmpeg route is on
the authored side of the line as a distinct lowered source identity; it crosses
this trigger if it is allowed to stand in for a filter's output.

**What done looks like.** A second implementation is admitted only by a
repo-owned harness that runs it against a reference implementation over a
versioned corpus deliberately containing low SNR, motion blur, compression
artifacts, and near-threshold contrast. Contributors provide implementations
and, where the tool contract allows it, an equivalence spec; they do not write
the tests that decide membership, because people write tests that pass. After
admission, selection can rank by measured cost per machine and input shape.

**The line today.** A backend whose output differs is a different answer. It
must be authored and keyed as a different answer, not selected silently under
the same `filter_id`.

**Regression check.** The first non-reference implementation of any filter has
a failing gate unless the admission harness has measured equivalence against
the corpus and recorded the reference, corpus version, comparator, tolerance,
and cost measurement. A test written inside the contributed backend is not
evidence for admission.
