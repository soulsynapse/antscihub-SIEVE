---
title: The dag propagation cases answer a mutation
priority: normal
phase: 3
status: open
gated_on: nothing
opened: 2026-08-07
---

# The dag propagation cases answer a mutation

The open question left by
[findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md](../findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md):
03.4's suite passed with `node_key`'s ancestry fold destroyed, because it
asserted only the direction that must not propagate. `dag.py` carries the same
shape of claim — meaning carries forward through preserving nodes, a rate change
unindexes everything after it, the earliest loss wins — and its cases were read
for coverage, never probed.

Reading the names says nothing either way: `a_branch_that_does_not_feed_the_asker
_is_not_blamed` is the negative and `meaning_carries_through_every_preserving
_node_after_a_redefinition` looks like its complement, which is exactly the
arrangement 03.4 also appeared to have. What settles it is the mutation, run
within the declared shape rather than by deleting a field: make the forward walk
stop one node early, make the loss attach to the node that asked rather than the
node that lost it, and see whether anything goes red.

Done when each propagating claim in `dag.py` has a mutation recorded against it
— the surviving ones repaired with a case, the rest noted as already covered so
the next reader does not re-run the probe.
