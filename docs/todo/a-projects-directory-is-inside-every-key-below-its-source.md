---
title: A project's own directory is inside every key below its source root
priority: high
phase: 11
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_key.py -q -k a_projects_location_and_the_key_below_its_source"
opened: 2026-08-10
---

# A project's own directory is inside every key below its source root

Measured in
[anchoring puts the project directory into the node key](../findings/2026.08.10-anchoring-puts-the-project-directory-into-the-node-key.md):
`resolve_source.anchored` rewrites a source node's relative path parameter to an
absolute one before `Dag.build`, `node_key` digests the resolved parameters, and
so the folder the project file happens to sit in is inside the key of every node
below the source. One `pick` node with one picked identity keys three different
ways as held, anchored on one folder, and anchored on another.

This is the first of the two rules
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
forbids by name — "neither 'this exact path' nor 'the folder of this name beside
the project'". The ADR's *ordering* clause is satisfied and its *exclusion*
clause is not.

It is minted here rather than staying folded into
[the-field-that-names-footage-leaves-the-schema](the-field-that-names-footage-leaves-the-schema.md),
where the 2026-08-10 review left it, because that item closed on 2026-08-10
having landed the removal and not this. What the removal changed is the scope:
ADR 34 requires the stored path to be relative to the project file, so relative
stops being the spelling a few documents happen to use and becomes the only one
— and relative was the one spelling whose key did not move when the folder did.
What a user sees after moving a project folder is a document that opens, every
file resolving, and every node below the source recomputing.

The fork, restated from the review that measured it rather than reopened:
either a source-tool node's `ToolSpec.path_params` are excluded from `node_key`'s
digest — defensible without a new ruling, since the file the parameter resolved
to is already in the key as the `picked_key` on the node's `upstream` pair — or
the cost is accepted and a successor ADR says so. Nothing in the tree pins key
stability across a project's location either way, so whichever branch is taken
owes a case that would go red if the other were built.

**The `done_when` names the case and not the answer, because the two branches
want the same case with opposite assertions.** One document, its node keys taken
from two directories: the exclusion branch asserts they are equal, the accept-it
branch asserts they move and cites the successor ADR beside it. Red today at
exit 5 — nothing in `tests/unit/test_cache_key.py` matches the name, which is
the whole of the gap:

    $ uv run pytest tests/unit/test_cache_key.py -q -k a_projects_location_and_the_key_below_its_source
    13 deselected in 0.14s
    exit: 5

Write which assertion into the case before writing code, so it is not derived
from what the code turned out to do.
