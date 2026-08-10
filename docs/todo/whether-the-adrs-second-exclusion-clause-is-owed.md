---
title: Whether the ADR's second exclusion clause is a defect named or a property owed
priority: normal
phase: 11
status: deferred
deferred_for: decision
gated_on: "Kendrick ruling on the exclusion clause's second half in adr/a-users-file-wires-in-like-any-other-input.md"
opened: 2026-08-10
---

# Whether the ADR's second exclusion clause is a defect named or a property owed

Measured in
[the ADR's second exclusion clause names a defect and is read as a promise](../findings/2026.08.10-the-adrs-second-exclusion-clause-names-a-defect-and-is-read-as-a-promise.md):
`adr/a-users-file-wires-in-like-any-other-input.md` forbids two derivations —
"neither 'this exact path' nor 'the folder of this name beside the project'" —
and then prices each. The review reads both halves of that pricing as failure
modes. Four texts read the second half as a property a correct key delivers, and
so record `a1ce8d0` as discharging half a clause: `cache_key.picked_key`'s
docstring, the passage `a1ce8d0` added below it, that commit's amendment on
[the anchoring finding](../findings/2026.08.10-anchoring-puts-the-project-directory-into-the-node-key.md),
and the motivating sentence of
[a-projects-directory-is-inside-every-key-below-its-source](a-projects-directory-is-inside-every-key-below-its-source.md).

Deferred on a decision rather than open, because what a criterion here would
assert is the thing being decided: the first move is a ruling on a settled ADR's
own words and that is Kendrick's. The two branches want different work and
neither is `node_key`'s:

- The clause names two defects. Then `a1ce8d0` discharged it whole, the four
  texts want their "the other half" sentences struck, and what a user sees after
  moving a project folder is `source_identity` working as designed rather than a
  shortfall. The ADR itself may want one polarity word added, since a sentence
  three readers inverted in a row is a sentence that reads two ways.
- The clause promises portability across a folder reorganization. Then the
  promise is unmet by a mechanism the ADR does not touch — `source_identity`'s
  first field is the resolved absolute path — the four texts are right, and what
  is owed is a successor ADR reconciling the two, since no key derived from a
  file's identity can survive that file moving.

Either way the code stands. This is a correction to prose and, on the second
branch, a decision; nothing here asks for a digest to change.
