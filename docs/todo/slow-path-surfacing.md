---
title: Sessions log how the app was used, and changes are scored against a moving baseline
status: open
serves: [A1]
opened: 2026-07-28
gated_on: >
  nothing — the trigger fired 2026-07-28 when ledger-producers landed
  (docs/completed-todo/2026.07.28-ledger-producers.md): the resource probe and
  the pool meters now publish, so there is something to aggregate.
reads:
  - docs/completed-todo/2026.07.28-ledger-producers.md
  - src/sieve/bench/budgets.py
  - src/sieve/bench/retention_trace.py
  - tools/doc_index.py
  - docs/.state.md
---

# A measurement nobody reads is not an instrument

Raised 2026-07-28, in three passes that widen the same requirement:

1. "some tool that monitors the usage, which things are laggy and need to be
   optimized or *potentially* addressed, with gates for ones that can be
   flagged for potential revisit if there's a way to fix them"
2. "this needs to automatically get into your .state file or you'll never
   find it"
3. "this information on how the app is used should absolutely all be logged
   automatically — if you have to tell me about how I'm using stuff it should
   genuinely all be logged and automatically summarized against a moving
   sample between changes to raise potential issues"

The third pass is the one that changes the shape. The first two are about
*performance* reaching a reader. The third is about *usage* — what was
touched, in what mode, over what window — and about scoring it across code
changes rather than reporting it once.

The session of 2026-07-28 is the standing argument. Three facts decided how
its data could be read, and a human had to reconstruct every one of them by
hand afterwards from a JSONL file:

- the session produced **16 scrub events** against 12671 playback gets, which
  is why `docs/findings/2026.07.28-capacity-beats-policy-in-the-render-ring.md`
  can answer the throughput half of a question and not the latency half;
- the working **window was shrunk partway through**, so the retention curve
  pools two working-set regimes;
- memory grew to 4.7 GB under the large window and sat flat at 1.65 GB under
  the small one, which is the whole content of
  `docs/findings/2026.07.28-the-session-floor-is-the-window.md`.

Every one of those is a fact about *how the app was used*. None of them was
available to the app, which knew all three at the time.

## The constraint that decides the shape

`docs/.state.md` is committed (`git ls-files` confirms it) and
`tests/docs/test_doc_index.py::test_every_index_matches_its_folder` asserts
the committed file matches regeneration. So:

**Machine-local telemetry cannot be written into `.state.md`.** It would fail
the gate on every machine whose numbers differ from the committed ones, and
leave the tree dirty after every session. The file's own header — "every line
here is derived; nothing is unique to this file" — is the same rule stated
from the other side.

The resolution is a promotion boundary, and it is the design rather than a
workaround:

- **The raw store is machine-local and gitignored.** Samples accumulate per
  session, keyed by machine fingerprint **and by commit** (the second is what
  makes the moving baseline possible at all). Rule 8 applies to the writer: it
  reads its own output back before registering it, and an unverifiable sample
  file is deleted rather than recorded.
- **Promotion is explicit and produces a committed artifact**, with
  frontmatter a tool can parse, like everything else in `docs/`.
- **`.state.md` carries the promoted set only.** The count of unpromoted local
  observations is machine-local in value, so it cannot be baked into the
  generated doc; the honest form is a line the tool prints at session start.

## What a sample has to carry

Not just timings. The 2026-07-28 session shows what an under-specified sample
costs, so the schema is the load-bearing design decision here.

- **Mode.** A render-fed playback sample and a plain playback sample are not
  comparable. The earlier session of the same day scored 4633 of 4633 requests
  served from decode, which reads as catastrophic and was in fact a mode where
  the ring is not in play by design (`feed_bounds` does not engage outside a
  filling window render). Aggregating across modes would have promoted a
  non-problem to the top of the primer.
- **Workload shape.** Window extent, block count, node count, source
  resolution. Without these, two sessions differ for reasons no reader can
  recover — and the window in particular turned out to determine memory
  outright.
- **Gesture mix.** Counts by kind: scrub, playback, exact, parameter edits,
  materialisations. This is the part that would have told us the retention
  session could not answer its own question *while it was still running*,
  rather than a day later.
- **Commit.** Without it there is no baseline to move against.

## The moving baseline, and why it can only ever suggest

The ask is that a change be scored against a rolling sample of prior sessions
so a degradation raises itself. That is worth building and it has a
methodological ceiling that must be stated in the design rather than
discovered later:

**This is observational, not experimental.** Sessions differ in workload, and
workload differences are large — larger, on this evidence, than most code
changes. A naive diff between "sessions before commit X" and "sessions after"
attributes to the change whatever the user happened to do differently that
week. The 4.7 GB / 1.65 GB memory split within a *single* session came
entirely from the window, not from any code at all.

Three consequences for the design:

1. **Condition before comparing.** Compare within mode and within a workload
   bucket, never pooled. A comparison that cannot find a matching bucket
   reports "no comparable baseline", which is a useful output.
2. **Require n, and report spread.** One session is never a signal. The report
   carries n and distribution, never a single number, per rule 6.
3. **Label the output as a candidate, not a regression.** A flagged item says
   "this moved, here is the bucket and the n" and never "commit X caused
   this". The confirming step is a deliberate measurement, which is what
   `docs/findings/` is already for. A telemetry system that announces causes
   will be wrong often enough to be ignored entirely, which costs more than
   not having it.

## The gate between "slow" and "worth fixing"

The request distinguishes things needing optimisation from things only
*potentially* needing it, and asks for a way to flag the second for revisit.
The repo has the pattern twice — `WITHOUT_PRODUCER` and `IN_DEBT` in
`bench/budgets.py`, both lists that only shrink, both machine-checked. A third
instance should look the same rather than inventing a mechanism.

Three states, and an observation is in exactly one:

- **A miss.** Exceeded a declared budget. Has machinery; what is new is that
  it survives the session it occurred in.
- **Unbudgeted and slow.** No budget covers this path and it was an outlier.
  This is the class the request is really about, and the class rule 4 cannot
  currently see at all — a path with no ceiling cannot miss one.
- **Known and accepted.** Measured, understood, not worth fixing.
  `docs/findings/2026.07.25-the-seek-is-irreducible.md` is exactly this.
  Without this state the report re-raises it forever and trains the reader to
  skim. An accepted entry cites the finding that accepted it, so acceptance is
  an argument rather than a mute.

## What this is not

Not a profiler. `docs/todo/profiling-as-a-module.md` attributes a known miss
to a cause and stays deferred on its own trigger. This one answers "what
should somebody look at" and hands off.

Not a governor. `docs/todo/adaptive-worker-allocation.md` is the item for
acting on this data automatically, and it is deferred behind exactly the
evidence this produces.
