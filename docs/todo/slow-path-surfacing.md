---
title: What was slow, promoted to somewhere a session will actually find it
status: deferred
opened: 2026-07-28
gated_on: >
  docs/todo/ledger-producers.md landing — there is nothing to aggregate until
  something publishes. Taking this first would build a reporting path over an
  empty bus.
reads:
  - docs/todo/ledger-producers.md
  - src/sieve/bench/budgets.py
  - tools/doc_index.py
  - docs/.state.md
---

# A measurement nobody reads is not an instrument

Raised 2026-07-28: "some tool that monitors the usage, which things are laggy
and need to be optimized or *potentially* addressed, with gates for ones that
can be flagged for potential revisit if there's a way to fix them, but this
needs to automatically get into your .state file or you'll never find it."

The last clause is the item. `docs/todo/ledger-producers.md` gets numbers onto
the metrics bus and into the HUD, which makes them visible to a person who is
looking at the HUD at the moment they occur. It does nothing for the session
that opens this repo next week — and `docs/.state.md` exists precisely because
that session orients in one read. A slow path that is not in the primer will
not be found, however well it was measured.

## The constraint that decides the shape

`docs/.state.md` is committed (`git ls-files` confirms it) and
`tests/docs/test_doc_index.py::test_every_index_matches_its_folder` asserts
the committed file matches regeneration. So:

**Machine-local telemetry cannot be written into `.state.md`.** It would fail
the gate on every machine whose numbers differ from the committed ones, and
leave the tree dirty after every session. The file's own header — "every line
here is derived; nothing is unique to this file" — is the same rule stated
from the other side.

The resolution is a promotion boundary, and it is worth being explicit that
this is the design, not a workaround:

- **The raw store is machine-local and gitignored.** Samples accumulate per
  session, keyed by machine fingerprint. Rule 8 applies to the writer: it
  reads its own output back before registering it, and an unverifiable sample
  file is deleted rather than recorded.
- **Promotion is explicit and produces a committed artifact.** A promoted
  observation is a small committed file — the same shape as everything else
  in `docs/`, with frontmatter a tool can parse.
- **`.state.md` carries the promoted set, plus one derived line naming the
  count of unpromoted local observations.** That line is machine-local in
  *value*, so it cannot be in the committed file either; the honest form is a
  pointer — "N observations pending review; `uv run ... review`" — emitted by
  the tool at session start rather than baked into the generated doc.

That last point is the one to get right and the easiest to fudge. If the
count went into `.state.md`, the file would be dirty on every machine. If it
goes nowhere, the whole item fails at its stated purpose.

## The gate between "slow" and "worth fixing"

The request distinguishes things that need optimising from things that only
*potentially* do, and asks for a way to flag the second class for revisit.
The repo already has the pattern twice — `WITHOUT_PRODUCER` and `IN_DEBT` in
`bench/budgets.py`, both lists that only shrink and both machine-checked. A
third instance should look the same rather than inventing a mechanism.

Three states, and an observation must be in exactly one:

- **A miss.** Exceeded a declared budget. Already has machinery; what is new
  is that it survives the session it occurred in.
- **Unbudgeted and slow.** No budget covers this path and it was an outlier.
  This is the class the request is really about, and it is the class rule 4
  cannot currently see at all — a path with no ceiling cannot miss one.
- **Known and accepted.** Measured, understood, and not worth fixing.
  `docs/findings/2026.07.25-the-seek-is-irreducible.md` is exactly this: a
  path that is slow for a reason nobody can remove. Without this state the
  report re-raises it forever and trains the reader to skim.

An accepted entry must cite the finding that accepted it, so the list can be
audited and so acceptance is an argument rather than a mute.

## Rule 6 governs what counts as an observation

One slow frame is not a finding, and a report that presents it as one is the
failure this rule names. Minimum bar, to be set concretely when the sample
shape is known: a path is reportable when it recurs across separate sessions,
and the report carries n and spread rather than a single number. A one-session
outlier belongs in the local store, not in a promoted file.

The 2026-07-28 retention session is the cautionary case and should be kept in
mind while designing the sample schema: 4633 of 4633 requests served from
decode, which reads as catastrophic and was in fact a mode where the ring is
not in play by design. **A sample must carry the mode that produced it.**
Aggregating across modes would have promoted a non-problem to the top of the
primer.

## What this is not

Not a profiler. `docs/todo/profiling-as-a-module.md` is the item for
attributing a known miss to a cause, and it stays deferred on its own
trigger. This one only answers "what should somebody look at", and hands off.
