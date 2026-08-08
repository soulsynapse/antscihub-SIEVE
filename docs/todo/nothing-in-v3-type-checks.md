---
title: Nothing in v3 type-checks, and that has never been decided
status: open
gated_on: nothing
priority: normal
phase: "08"
done_when: "uv run pyright src/sieve"
opened: 2026-08-07
---

# Nothing in v3 type-checks, and that has never been decided

`mypy` is not in the dev group, the gate does not run it, and no ADR says v3
declines it. So the absence is an accident of nobody having asked, not a
position — which is the same shape as the formatter gap and was noticed in the
same breath as it (`ruff-format-drifts-because-ruff-is-unpinned.md`), but it is
a larger question and does not ride along with a formatter pin.

It is larger because the answer is not "add a tool to a list". v3's code is
annotated throughout and several contracts are stated in the type system rather
than in a test — `core/types.py`'s dimensioned quantities, the tool contract's
`ParamsBase`/`Frame`/`FrameSpan` signatures, the pydantic models the cache key
and the saved document are built on. If those annotations are load-bearing then
nothing checking them means a class of contract is declared and unverified,
which is the thing `declared-means-verified` exists to refuse. If they are
documentation, that is a defensible position and belongs in an ADR so the next
session stops rediscovering the gap.

What a session taking this owes: which checker (v2's history with one is the
evidence to read, not a default to inherit), what strictness, whether it gates
on the whole tree or on `src/` only, and what the first run costs — a checker
that reports hundreds of findings on a tree written without one is a project,
not a gate line, and the size of that number is part of the decision rather
than something to discover after committing to it.

Kendrick's, not a worker's: whether v3 gates on types at all.

## Ruled 2026-08-08 — v3 gates, in basic mode, and the first run is a finding

The repo's own rule decided it: `adr/declared-means-verified.md` refuses a
declaration nothing consumes, and the annotations are the largest unverified
declaration surface in the tree — prose wearing a contract's syntax. The
checker is pyright, because v2 ran pyright and that history is the evidence
this item said to read; the mode is basic, not v2's strict, because strict on
a numpy/pydantic tree makes workers fight the checker instead of the
behavior. The first run's report is minted as a `docs/findings/` file *before*
anything is fixed — the number is part of the record, and strictness is
revisited against it, not assumed. `src/sieve` only.

Two edits ride with the gate or it lies: CLAUDE.md's "No type checker is
installed; don't spawn one" ends when this lands and must go in the same
commit, and the gate line in CI grows the command. Re-filed to Phase 8 with
the rest of the debt: the ruling is made now, the run is not what the first
GUI cut stands on, and the report is most informative once Phase 7's Qt code
exists to be read.
