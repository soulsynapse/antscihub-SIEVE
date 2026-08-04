---
title: Parity comparison finding
status: deferred
priority: unassessed
opened: 2026-07-27T14:35:51-07:00
gated_on: >
  a seated session with the v1 checkout — v1 is a sibling repo no agent can
  reach and no headless run can drive, so the pending decision is what that
  session is for: a live two-GUI side-by-side, or one throwaway v1 run that
  dumps its count/gate series as a fixture a headless harness then compares
  against forever (recommended)
reads:
  - docs/findings/_TEMPLATE.md
  - docs/todo/downsample-or-rescale.md
---

# Parity comparison finding

Run v1 and v2 on `videos-testing/stab_GX010050c2_02_18_26.MP4` at matched
settings — scale 0.25, block auto, zscore, same frequency band, same D — and
write to `docs/findings/`: the numeric agreement of the count and gate series
where comparable, the interaction latencies against the budget table, the
throughput, and a gained/lost list. Anything lost that matters becomes its own
`docs/todo/` item with its trigger.

This was the last item of the filter tab's v1-parity plan, the one work item
that plan left open when it was deleted on 2026-08-04; items 1–8 landed
2026.07.26–27 and their entries are in `docs/completed-todo/`. The v1 semantics
the port had to match are recorded where they are implemented —
`core/wavelet.py` (Morlet `W0`, the scale bank, the COI e-folding),
`core/detection.py` (the count/window/gate chain and the two deliberate
deviations from v1), `filters/block_signal.py` (σ = 2.0, the LK solve before
reduction, auto block from 64 source px), `filters/normalize.py`, and
`filters/rescale.py`.

**This is the only item anywhere that produces evidence the rewrite did not
lose signal**, which is worth weighing against its position in an ordering.

---

## Why it is deferred, and what it is not

Not a scoping problem — the brief above is specific enough to execute.
The blocker is that **v1 is not in this repository and cannot be made to be**:
it lives in the sibling `antscihub-optical-flow-detector` folder, which is
outside any working directory a session is granted, and the four modules that
matter (`../antscihub-optical-flow-detector/core/wavelet.py`,
`../antscihub-optical-flow-detector/core/detection.py`,
`../antscihub-optical-flow-detector/core/tensor_channels.py`,
`../antscihub-optical-flow-detector/core/structure_tensor.py`) are reachable only from a shell that already has
it checked out. The second half compounds it: "interaction latencies" means a
hand on a slider, which no headless run produces.

So the seated session is unavoidable. What is *not* settled — and what this
item now exists to have decided in one read — is what that session is spent on,
because the three options cost very different amounts of Kendrick's time and
leave behind very different assets.

## The decision

**A — Live two-GUI side-by-side.** Resurrect v1's environment (PyQt6 and its
deps, unpinned since the rewrite began), open both apps on the same clip with
matched settings, read numbers off both, stopwatch the interactions, write the
finding.

- *Costs:* the whole session, plus whatever v1's environment has bit-rotted
  into. Every number is produced once by hand and is not reproducible without
  repeating the whole thing.
- *Gains:* the only variant that can answer "does the rewrite actually feel
  faster", which is SIEVE's stated value (`VISION.md`), not a footnote to it.
- *Forecloses:* nothing, but buys nothing standing either — a dated document
  and no artifact.

**B — Headless numeric harness, no v1 GUI.** Make v1's four pure modules
importable from here (a path entry or a vendored snapshot), run both stacks
over the same decoded frames, report agreement per stage. Latencies come from
`bench/budgets.py`, which already publishes them under CI; the gained/lost list
is written from reading v1's source.

- *Costs:* a standing cross-repo dev dependency, or a vendored copy of code
  the rewrite exists to replace — a maintenance surface pointed backwards.
  v1's *GUI* semantics (the parts §3 says must not come over) never get
  exercised, so anything lost in the plumbing rather than the math is invisible.
- *Gains:* fully repeatable, and it is the only variant an agent can run.

**C — One v1 run that produces a fixture, then B forever.** The seated session
does exactly one thing: run v1 on the reference clip at the matched settings
(scale 0.25, block auto, zscore, matched band, matched D) and dump the count
and gate series to `videos-testing/` as a parity fixture. Everything after that
— agreement, drift, regression — is a headless comparison against the fixture,
runnable by any later session.

- *Costs:* one seated session, and the fixture pins v1's behaviour at one
  parameter set on one clip. A later question at different settings needs
  another dump.
- *Gains:* converts a one-time comparison into a standing regression asset.
  No cross-repo dependency, nothing vendored — the fixture is data, not code.
- *Forecloses:* the felt-interaction claim, unless the same session also
  spends ten minutes dragging both sliders and writing a paragraph of prose
  (it should; that paragraph is cheap and is the part B can never produce).

## What constrains the choice

- **`docs/todo/downsample-or-rescale.md` is gated on this landing**, and reads
  it narrowly: it needs to know whether anything still depends on v1's exact
  `round(src × scale)` / INTER_AREA geometry. A numeric fixture answers that;
  a stopwatch does not. That item is the only declared consumer.
- **`bench/budgets.py` already owns latency** under rule 4 — every interaction
  budget has a producer and CI enforces it. Hand-timing v2's interactions in a
  seated session duplicates a number the repo publishes continuously and
  publishes *better*. The comparison against v1 is the only latency claim the
  bench table cannot make, and one honest paragraph covers it.
- **Rule 8, filesystem is truth at rest.** A dumped series is an artifact; if
  it is written, it should be written the way the rule now demands (read back
  and verified before being registered), not as an ad-hoc `.npy` beside the
  video.
- The `core/` and `filters/` ports had their claims already pinned by unit
  tests against v1's stated semantics. Parity is therefore a check on the
  *composition*, not on each function — which argues for comparing end-of-chain
  series (count, gate), exactly what C dumps, rather than instrumenting stages.

## Recommendation

**C.** Spend the seated session on the one thing only v1 can produce — its
count and gate series at the matched settings — and on a paragraph of prose
about how the two tabs feel. Everything else in item 9's brief is either
already published by the bench table or derivable headlessly from the fixture.

The reasoning is that A pays a full session for numbers that expire on
production, and B never gets the fixture at all because it needs v1 importable
*forever* to stay meaningful. C spends the scarce resource (a person with v1
running) on the scarce output, and leaves behind something a later agent can
re-run when the chain changes — which matters, because the risk this item
guards against is not "did the port land correctly in July" but "did the signal
quietly drift afterwards."

Concretely, when the trigger fires: dump `count` and `gate` for the matched
settings, write them next to the clip with the shape and the settings recorded
alongside, note the felt-interaction paragraph, and the follow-up work is a
`tests/integration/` comparison plus the finding — takeable by any later
session with no v1 present.
