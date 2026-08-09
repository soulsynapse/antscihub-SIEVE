---
title: The luma cap is slower than sequential on a small allocation
priority: high
phase: 8
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_decode_workers.py -q -k 'a_small_allocation_is_not_handed_more_workers_than_it_can_overlap'"
opened: 2026-08-09
---

# The luma cap is slower than sequential on a small allocation

`resolve_workers` answers `min(available_cpus(), LUMA_WORKER_CAP)` and the cap
is 2, so every allocation of two CPUs or more is handed two decode threads on
the luma path. 08.5's sweep measured what that buys at each size on the
reference footage
([findings/2026.08.09-the-luma-worker-cap-is-right-at-sixteen-cores-and-a-third-slower-at-four.md](../findings/2026.08.09-the-luma-worker-cap-is-right-at-sixteen-cores-and-a-third-slower-at-four.md)):
right at 16 and 32 CPUs, 33% *slower than one worker* at four, 53% slower at
two. The cap bounds the guess from above and there is no term in the resolver
that can see the bottom of the range, so the smaller the allocation the worse
the guess — which is the opposite of the direction a ceiling is meant to fail
in, and it lands on the cluster job step VISION's headless run is aimed at.

What the fix is, is not settled and this item is where it gets settled. A floor
on cores per worker is the obvious shape (`available_cpus() // k`, which at
`k = 4` reproduces the measured optimum at every size in the sweep), and it is
one arithmetic constant replacing another chosen on one machine — so a criterion
asserting a specific formula would be this run picking the shape. What is not in
question is that the resolver must not hand a 2-CPU allocation more workers than
a 32-CPU one gets per core.

The colour path is not part of this. `INFERRED_WORKER_CAP = 4` reads 11% off the
measured optimum of 3 on the whole allocation, which is inside what the
constant's own comment claims for itself, and its core-count axis was not swept.
If the fix is a formula rather than a second constant it has to say what it does
on the colour path, and that reading is a `sieve sweep --colour --core-counts`
away.

The measurement's own limit, from the finding: masking four cores out of
thirty-two keeps the whole last-level cache and memory controller, so this
samples core count and not a small machine. The sign is trustworthy — two
workers contending on four cores is not an artefact of cache size — and the
magnitude is not.

## Closed 2026-08-09 (review of 12217da): the invariant this item called settled cannot be met

Two rulings the run made are recorded here because the criterion witnesses
neither and a run log is not somewhere a later reader looks.

**The stated invariant is unsatisfiable, and a different one was pinned.** "The
resolver must not hand a 2-CPU allocation more workers than a 32-CPU one gets
per core" fails for every resolver that returns at least one worker: one worker
on two cores is two cores per worker against sixteen at the top of the range, so
the small allocation always has the worse ratio, and reading the sentence the
other way round only makes the requirement stricter. What landed instead is a
fixed floor — cores per worker never below `CORES_PER_WORKER` whenever more than
one worker starts — which delivers what the sentence was reaching for at the two
sizes it names. That substitution is the run's decision, not this item's.

**The colour path was ruled in, against this item's third paragraph.** "The
colour path is not part of this" and "if the fix is a formula it has to say what
it does on the colour path" are this item disagreeing with itself; the run took
the second and the floor applies to both paths. Nothing measured moves — the
floor is slack at 16 and 32 CPUs, the only colour sizes read — but the colour
answer does change below them, four workers becoming two at 8 CPUs, and that
half rests on the contention mechanism rather than on a reading. The sweep that
would settle it is folded into
[a-truncated-unpinned-set-is-pinned-and-duplicates-the-fast-class.md](a-truncated-unpinned-set-is-pinned-and-duplicates-the-fast-class.md),
whose criterion does not cover it — see the review note in that file.

The justification written into `CORES_PER_WORKER`'s comment overclaims by one
core set (`class1[:8]`, where the sweep read sequential 2.1% faster than the two
workers the floor allows). The constant survives that; the sentence does not,
and the correction is queued. Amended in the finding this item cites.
