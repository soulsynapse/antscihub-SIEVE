---
title: Reusing an answer after its definition changed is solved by TBD
group: Substrate
position: 10
status: unsettled
decided: 2026-08-28
---

Two runs either side of an edit to a `field` are different answers under one
name, and nothing in the key is in a position to notice — the same silent-reuse
defect ADR-0005 records, arrived at from the code side rather than the data
side. What closes it has candidates and no measurement.

## Candidates

Luigi's version parameter — an ordinary `luigi.Parameter` on the task, folded
into `task_id` alongside every other parameter and bumped by hand when the
task's logic changes; a third-party solver an answer depends on stays in
`params`, since a version can only honestly cover what its author can see
change. Would have to be measured for the thing it trades on: how often a bump
that was owed did not happen, over this tree's own commits.

Luigi's version parameter with a text-baseline tripwire — the same key, plus a
check in `checks/` that notices when a step's text moves against a recorded
baseline and makes the author say whether the answer moved, by bumping or by
re-recording. The hash decides nothing and never reaches a key. This is the
arrangement the tree currently implements; what is unmeasured is whether the
tripwire changes the missed-bump rate enough to be worth the baseline it has
to carry.

## Rejected

Make cautionary tale: a target depends on its sources and never on the recipe,
so an edited rule reuses answers built under the old one. The workaround
culture that fills the gap — `make clean`, clean builds on suspicion — is what
a tuning loop cannot afford, since wiping stored series forfeits precisely the
accumulated work the loop exists to reuse.

joblib's source hashing cautionary tale: it hashes the decorated function's
source, which over- and under-invalidates at once — a rename invalidates
answers that did not change, and an edited helper outside the hashed body
reuses answers that did.

Nix and Bazel cautionary tale: they make hashing correct by making hermeticity
the product and paying rebuild-on-formatting as the going rate. SIEVE is not
buying hermeticity; its product constraint is a loop where stored work is the
asset, and every edit minting a new identity is exactly what makes *the same
pipeline, corrected* inexpressible.
