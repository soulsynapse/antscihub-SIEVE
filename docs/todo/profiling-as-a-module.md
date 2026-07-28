---
title: Profiling as a module
status: deferred
serves: [A1]
gated_on: >
  a budget miss whose cause is not obvious from the span that reported it —
  concretely, a `full_preview_render` miss over a multi-node graph
reads:
  - docs/SCAFFOLD.md
  - docs/findings/
  - pyproject.toml
---

# Profiling as a module

**Why not now.** `viztracer` and `py-spy` are in the dev group and imported by
nothing. Every measurement in `docs/findings/` so far came from timing a named
interval directly — the seek cost, the colour conversion, the scrub round trip
— and each of those was a hypothesis with an obvious place to put a
`perf_counter`. A profiler earns its place when the question is *where did the
time go*, and that question has not been asked yet.

**What would make it the right time.** A budget miss whose cause is not obvious
from the span that reported it. Half of that is now in place: `bench/metrics.py`
publishes spans against budget keys and `Sample.within_budget` says which
missed, so a miss can arrive with a key and no explanation — which is exactly
the gap `bench/profiling.py` fills. The other half is a *nested* span worth
attributing, and today the only publisher is `gui/player.py`'s scrub round trip,
whose cause is already known (`docs/findings/2026.07.25-the-seek-is-irreducible.md`).
The trigger is therefore the preview: a `full_preview_render` miss over a
multi-node graph is the first question of the form "which node?". The two tools
are complementary and both are already declared — VizTracer for phase structure,
py-spy for sampling a process nobody instrumented — so this is wiring, not a
choice.

Read: `docs/SCAFFOLD.md` `bench/profiling.py`, `docs/findings/`,
`pyproject.toml` dev group.
