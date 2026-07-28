---
title: SCAFFOLD's annotations should come from the module docstrings
status: deferred
opened: 2026-07-28

gated_on: >
  a module whose SCAFFOLD annotation and docstring first line have visibly
  diverged — the failure this prevents has not been observed yet, and the
  migration costs one edit per module in Built

reads:
  - docs/SCAFFOLD.md
  - tests/docs/test_scaffold.py
  - tools/doc_index.py
---

# SCAFFOLD's annotations should come from the module docstrings

The obvious version of this idea — generate the Built tree from the
filesystem — **deletes the only enforcement the file has**. Today, adding a
module and forgetting its line breaks `tests/docs/test_scaffold.py` and you
notice. Generate the paths and that becomes a silent auto-append, trading the
gate for one line of typing per module.

The tree is also not where the value is. The one-line annotation saying what
each module *owns* is, and that is the half no generator can produce and the
half that actually decays. Generating paths while hand-maintaining annotations
gives the worst split: the checked half automated, the unchecked half still
manual.

## The version that works changes the source, not the target

Make the **module docstring's first line** the single home for "what this
module owns", and generate Built's annotations from it. That:

- satisfies one-home-per-fact, which the settled table just had to be rebuilt
  around (`docs/completed-todo/2026.07.28-*` for that change);
- keeps a human writing the sentence;
- puts the sentence where whoever edits the module will see it, rather than in
  a file they have no reason to open;
- is consistent with `CLAUDE.md` already routing interface contracts to
  docstrings.

Projected stays hand-written. It is an intention, and nothing in the tree can
generate an intention.

Keep a test that fails on a Built module whose docstring first line is missing
or merely restates the filename — otherwise the annotation degrades to
`"""Filter registry."""` and the file becomes a directory listing with extra
steps.

## Why not now

The migration is one edit per module in Built, which is most of `src/sieve/`,
and it buys nothing until an annotation and a docstring have actually
diverged. Nobody has seen that happen. The line to watch is the one this item
would have caught: `pipeline_model.py` read "schema v2 with Edge.port" three
schema versions in, fixed by hand on 2026.07.28 — a second instance of that
class is the trigger.
