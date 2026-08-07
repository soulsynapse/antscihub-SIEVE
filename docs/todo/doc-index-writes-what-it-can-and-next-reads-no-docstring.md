---
title: doc_index writes what it can, and `--next` never reads a docstring
priority: high
phase: 0
status: done
gated_on: nothing
done_when: "uv run pytest tests/docs -q"
opened: 2026-08-06
---

# doc_index writes what it can, and `--next` never reads a docstring

Two decouplings in `scripts/doc_index.py`, found when one over-limit
docstring stopped the whole derived-docs run (the last probe in
`findings/2026.08.06-the-scaffold-annotation-does-not-fit-a-ported-module.md`):

1. Render each of the four targets independently: write every one that
   renders, report every failure, exit 1 if any failed. Today a single bad
   module leaves all four files stale while refusing only SCAFFOLD.md.
2. Compute `--next` from the items alone. Selection has no dependency on
   module docstrings, yet it runs after `collect_modules()` — so a bad
   docstring takes down the loop's selection rule, and an item cannot record
   its own blocker in the tree that blocked it.

Each lands with a test shown failing first: a module with an over-limit
docstring in a tmp tree must still get `--next` answered and
`todo/.index.md` written, with exit 1 and the refusal naming SCAFFOLD.md.
