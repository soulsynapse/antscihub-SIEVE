---
title: Detection is a filter emitting a per-frame channel
status: open
opened: 2026-07-29T12:18:58-07:00
priority: high
gated_on: nothing
after: [a-kernel-that-sees-a-span, a-filter-names-what-it-emits]
serves: A3
reads: [src/sieve/detect/detector.py, src/sieve/gui/detector_worker.py, src/sieve/core/ops/detection.py]
---

# Detection is a filter emitting a per-frame channel

The migration's center of mass. `src/sieve/filters/detect.py`: the Morlet
band power, the gate, and the count become a windowed filter whose parameters
are `Node.params` like everyone else's — hashed into identity,
backend-dispatched, cached, refused up front. Emission is a per-frame channel
(decided 2026-07-29, REWORK.md ## Decided); intervals are derived downstream,
and the deriving step is the natural first `TableSpec` emitter, which is
`sink-writers`' trigger.

What this makes true, none of which can be patched in place beforehand: the
values that decide what is claimed as an event enter a cache key for the
first time (the current `cli/detect_cmd.py` docstring's hashing claim is
false today); `detector_worker.derive` stops being a computation and becomes
a call through the one path — the QThread wrapper around it survives
unchanged, exactly as `materialize_worker` wraps `materialize_crop`; and the
parameter space becomes enumerable from the spec, which is what A3 needs.

**Do not add `DetectorSettings` to the cache key in the meantime** — the gap
closes for free here, and an interim key is a second spelling with its own
migration. (The old draft's step 12 records the same instruction.)

Schema untouched — `Project.detector` keeps working until the flip. The GUI
copies (`DetectorState` and friends) die in `detector-state-dies`, after the
flip, not here.
