---
title: Reusing an answer after its definition changed is solved by TBD
group: Substrate
position: 10
status: unsettled
decided: 2026-08-28
---

Two runs either side of an edit to a `field` are different answers under one
name and nothing in the key is placed to notice; what closes it has candidates
and no measurement.

## Candidates

Luigi's version parameter — an ordinary `luigi.Parameter` folded into `task_id`
and bumped by hand, with a third-party solver staying in `params` since a
version honestly covers only what its author can see change. Would have to be
measured on what it trades on: how often an owed bump did not happen, over this
tree's commits.

The same, plus a text-baseline tripwire in `checks/` that notices a step's text
moving and makes the author say whether the answer moved. What the tree
implements now; unmeasured is whether the tripwire moves the missed-bump rate
enough to pay for the baseline.

## Rejected

Make cautionary tale: a target depends on its sources and never on the recipe,
and the workaround culture that fills the gap — `make clean` on suspicion — is
what a tuning loop cannot afford, since wiping stored series forfeits the
accumulated work the loop exists to reuse.

joblib's source hashing cautionary tale: over- and under-invalidates at once —
a rename invalidates answers that did not change, an edited helper outside the
hashed body reuses answers that did.

Nix and Bazel cautionary tale: hashing made correct by making hermeticity the
product, paying rebuild-on-formatting as the going rate. SIEVE is not buying
hermeticity, and every edit minting a new identity is what makes *the same
pipeline, corrected* inexpressible.
