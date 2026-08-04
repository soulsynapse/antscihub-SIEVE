---
title: Warmup is derived, epsilon is a field, cacheable splits fact from policy
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
reads: [src/sieve/core/filter_base.py, src/sieve/filters/temporal_baseline.py, src/sieve/filters/background_ema.py]
---

# Warmup is derived, epsilon is a field, cacheable splits fact from policy

REWORK.md R3. `warmup_frames` stops being a hand-typed decorator argument and
becomes a function of the filter's own parameters — the mechanism exists
(`ParamsBase.warmup_frames()`, with `node_warmup_frames` refusing a
refinement that exceeds the spec's bound). Derivations: `motion_history` is
exactly τ; `background_ema` is `log(ε) / log(1−α)`, analytic;
`temporal_baseline` is `N` if its window is rolling — **the first step of
this item is answering whether it is rolling or adaptive**; if adaptive, it
stays declared and is the only unverifiable case.

The epsilon moves from docstring sentence to spec field — a test cannot
assert against a sentence, and its value is a scientific call per filter, not
a default.

Then the R3 gate: a property test over `discover()` — run each filter from
two start points, require agreement within its declared epsilon at
`i >= warmup`. Filters nobody has verified live in a shrink-only set, the
`WITHOUT_PRODUCER` idiom.

And `cacheable` splits fact from policy: `deterministic and not stateful`
fuses a permanent fact about the operation with a policy contingent on
verification, so the policy cannot change without the fact becoming a lie —
you would have to un-declare `stateful` to get a key, precisely the incentive
the declaration exists to remove. The spec declares facts; the planner
decides policy, reading the verification. This *refines* the settled row
"Stateful nodes … deliberately uncacheable" rather than overturning it — read
the stateful-output finding first; the key-cannot-carry-state argument
stands, and verification-gated caching must not route around it.
