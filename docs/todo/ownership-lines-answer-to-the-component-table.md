---
title: A package's ownership line answers to the component table
status: done
phase: 0
priority: normal
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py -q"
opened: 2026-08-06
---

# A package's ownership line answers to the component table

`src/sieve/core/__init__.py` claims "the dimensioned types, the tool contract,
and spec-free array math". VISION.md's component table and ADR-6 both say core
also owns schema v1. Nothing in the repo notices —
`2026.08.06-derived-docs-prove-the-copy-not-the-decision.md` has the shape and
the two smaller cases (`decode` drops decoder identity, `gui` drops holding
view state).

Fix the three lines, and then decide whether the agreement is checkable. The
hard half is that "Owns" is prose with inline links, so either the table stops
being prose or the check degrades to "every package named in the table has a
directory and vice versa" — which would not have caught this one. Say which in
the commit; a weaker check installed without saying so is worse than none,
because the next reader believes the line was verified.

Not gated on anything and nothing is gated on it: the tree is right, only the
sentences describing it are short. It wants doing before Phase 1 puts real
modules under these packages and multiplies the annotations.
