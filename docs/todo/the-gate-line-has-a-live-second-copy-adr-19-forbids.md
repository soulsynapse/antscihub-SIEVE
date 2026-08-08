---
title: The gate line has a live second copy, and ADR 19 names it without ruling on it
priority: normal
status: open
gated_on: nothing
phase: "00"
opened: 2026-08-07
---

# The gate line has a live second copy, and ADR 19 names it without ruling on it

[ADR 19](../adr/the-gate-is-one-line.md) settles that the gate is one
`&&`-joined command written once, and that a copy becomes a forbidden one
"exactly when something requires it to stay identical to the line". By that
clause `docs/todo/ci-runs-what-a-commit-must-pass.md`'s `done_when` is one: it
holds the line character-for-character, and it has been brought back into step
by hand twice, once per command added — `ruff format --check` and then
`actionlint`, the second time at `ae6e499`, whose own review note says nothing
compares the two lines so they agree only because a reviewer noticed. The ADR
cites that history as the evidence its rule rests on and then does not say what
becomes of the copy that produced it.

The prose beside that `done_when` has already drifted a third time and is
drifted now: 00.3's body reads "running exactly the `done_when` line — the
linter, the formatter, import-linter, pytest", four commands against a
`done_when` that holds five.

Three ways out, and which one is the decision: strike the copy, so 00.3's
`done_when` names the criterion rather than restates the line and the item's
body stops enumerating it; grandfather it, so ADR 19 says a completed item's
`done_when` is a dated record like a worker note and drift in it is not the
failure the rule is about; or keep it and pin it, so a test compares 00.3's
`done_when` to `ci.yml`'s `run:` line and the second copy is one the tree
maintains rather than a reviewer. The third is the only one that leaves two
enumerations standing, which is what ADR 19 refuses in a `paths:` entry for the
same reason — so it needs the argument the other two do not.

Not urgent: the two lines agree today, which the gate run at `8bfb2e7`
confirms. What is not sound is a settled rule whose one worked example is a
standing exception to it.
