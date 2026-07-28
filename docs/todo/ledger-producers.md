---
title: The memory ledger has no producer, and the worker split has no sensor
status: open
opened: 2026-07-28
gated_on: >
  nothing structurally — the metrics bus and the HUD it already feeds are the
  surface this publishes on
reads:
  - src/sieve/gui/concurrency.py
  - src/sieve/bench/budgets.py
  - src/sieve/bench/metrics.py
  - src/sieve/gui/main_window.py
  - docs/todo/ledger-measurements.md
---

# A ceiling nothing publishes is a number, not a budget

Raised 2026-07-28, from a session where the instrument had to be a scratch
script attached by PID: "if this measurement tool is so critical it really
should be built into the app itself", and then "the load balancing should be
automatic, I'm not certain if it is tuned to my machine it's actually useful,
and you should have built in logs to get feedback on how effective the load
balancing actually is".

Both halves are the same defect, and it is a rule 4 defect hiding where rule
4's machinery does not look.

`bench/budgets.py` enforces rule 4 for *latency*: `WITHOUT_PRODUCER` is the
honest list of budgets nothing publishes at runtime, and
`tests/bench/test_budget_producers.py` fails both on a producerless budget
missing from the list and on a listed one that has since grown a producer.

`gui/concurrency.py` declares two more tables — three worker pools and four
memory shares — and **not one row in either has a producer.** There is no
`WITHOUT_PRODUCER` equivalent, because there is nothing to exempt: the count
is zero. `UNBOUNDED` looks like the same construction but is not; it names
consumers missing a *declaration*, not budgets missing a *publisher*. The
file states the position outright at line 24 — "the ledger is a sum a test
checks, never a runtime governor" — which was a reasonable scope when the
ledger landed and is what this item revisits.

The consequence is concrete. `PREVIEW_WORKERS = 2` is the measured optimum
from the luma finding, on the machine that finding was measured on, applied
as a ceiling everywhere. `resolve_worker_split` degrades it downward by core
count and never anything else. `DETECTOR_WORKERS = 2`'s own docstring calls
itself "a judgement, not a measurement — nobody has profiled the three pools
competing, and the day someone does is the day this should change." No
session on any other machine has ever produced evidence for or against any of
these. A user cannot find out whether the split fits their hardware, and
neither can we.

## Why observability first, and not adaptive allocation

The obvious reading of "load balancing should be automatic" is a runtime
governor that measures and re-tunes the pools live. That is the right
eventual shape and the wrong first move, for a control reason rather than a
conservatism one: **there is currently no sensor.** A loop closed around an
unobserved plant does not converge on the right split, it oscillates, and an
oscillating allocator is worse than a fixed constant that is wrong by 20%.

The objective is also confounded in a way that is easy to underestimate. The
recorded session of 2026-07-28 would have scored as total failure by any
naive throughput measure — 4633 of 4633 gets served from decode, zero ring
hits at every capacity — and the split had nothing to do with it: the session
was ordinary playback, where `feed_bounds`' fold does not engage and the ring
is not in play by design. A governor reading that signal would have re-tuned
against a mode that was never running. Whatever gets published has to carry
*which mode produced it*, or it will be averaged across modes that do not
compare.

Rule 7 raises no objection to either half. Worker counts and memory shares
change where a result lives and how fast it arrives, never what it is; they
are not hashed, and nothing about instrumenting or later adapting them can
touch result identity.

## What to build

The wiring already exists and is the reason this is a small item.
`main_window.py:358` connects the metrics bus to a HUD
(`self._metrics.sample.connect(self._filter_tab.hud.show_sample)`) — there is
a live path from a measurement to something on screen. What is missing is
anything publishing on the resource side of it.

1. **A memory producer.** Sample process RSS including children, publish on
   the bus, compare against `sum(MEMORY_SHARES) + memory_reserve()`. This is
   the standing version of `docs/todo/ledger-measurements.md`'s H3 and H4:
   the floor and the peak stop being a person's errand and become something
   every session reports. Note `psutil` is *not* a declared runtime
   dependency — it resolves in dev as a transitive of pytest-benchmark — so
   this is either a new dependency or `ctypes`/`GetProcessMemoryInfo` on
   Windows and `/proc` elsewhere. Decide explicitly; do not rely on the
   transitive.
2. **A pool-utilisation producer.** Per pool, time spent with work in flight
   against wall time, plus queue depth. This is the evidence
   `DETECTOR_WORKERS`' docstring asks for by name.
3. **Mode in the sample.** Per the confound above: a render-fed playback
   sample and a plain playback sample are not comparable and must not be
   summed.
4. **`WITHOUT_PRODUCER`'s equivalent for these two tables**, machine-checked
   the same way, so the gap shrinks visibly instead of silently.

Rule 6 governs the display: a sampler that cannot read a child process —
permissions, a worker exiting mid-sample — must refuse rather than report the
parent's RSS as the total. An undercounting memory readout is precisely the
"looks better-founded than it is" failure, and it is worse than no readout
because it would be believed.

Surfacing follows the existing principle: where the symptom is, not in a
preferences dialog.

## What this does not do

It does not make allocation adaptive. It makes adaptation *possible to
justify*, by producing the per-machine evidence that does not currently exist
anywhere. Whether the fixed constants should become a controller is a
separate item, and it should be opened by data from this one — specifically,
by the constants turning out to be wrong on machines that are not the
reference.

It also does not retire `docs/todo/ledger-measurements.md`. H3 and H4 want a
number on the reference workstation to replace `memory_reserve`'s provisional
formula; this item wants every session to report its own. The first is a
constant, the second is a sensor, and the sensor is how the constant gets
checked later.
