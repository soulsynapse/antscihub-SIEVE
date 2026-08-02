# SIEVE

Signal Isolation for Ethological Video Events (SIEVE) isolates behavior from
video using interpretable signal-processing filters. The user builds a
pipeline; SIEVE runs it.

The repo is mid-rewrite: the architecture is settled, the skeleton is placed,
and real code lands next. This README is the map — where things are and which
record governs them. It restates nothing a governing doc or the tree already
records; when it seems to disagree with one of them, the other is right.

## The four documents

- [docs/DESIGN-BRIEF.md](docs/DESIGN-BRIEF.md) — the design prompts, verbatim,
  including the rejected §8 EDIT kept as a recorded alternative.
- [docs/DESIGN-SESSION.md](docs/DESIGN-SESSION.md) — the argument that
  determines the code, in nine exchanges. **The authoritative record**: where
  any other document is silent or conflicts, this one governs.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the synthesis: seven
  components, the authoring and execution flows, five invariants with their
  failure modes. Read this first when writing code.
- [docs/PLAN.md](docs/PLAN.md) — the conformance plan: phase gates, the
  settled layout, marker form rule v1, and the definition of done.

## The tree

Real code (the debt machinery, PLAN.md Phase 2 — the closed class that gives
every placeholder its meaning):

- `src/sieve/debt.py` — the `Owed` marker exception, the rule-v1 enumerator,
  the ledger serializer, and the regen command.
- `tests/conftest.py` — the adapter: a caught marker becomes a skip carrying
  its reason; one the enumerator can't see fails.
- `tests/_sentinel/` — the marker the enumerator must always find, so "no
  debt" and "enumerator dead" stay distinguishable.
- `tests/test_debt.py`, `test_automatic_ledger.py`, `test_adapter.py`,
  `test_import.py` — the machinery's own tests, including the mismatch test.

Placeholders (each a module raising `Owed`; the docstring and reason point at
the governing sections — follow the pointer before building):

- `src/sieve/kernel.py` — the five-shape op algebra, one design unit.
- `src/sieve/tools/` — one file per tool (invariant 1): `base.py` the Tool
  contract, `crop.py` the milestone tool.
- `src/sieve/views.py` — the closed view vocabulary: the language between
  tools and the GUI, owned by neither.
- `src/sieve/executor.py` — `render` only; `sweep` is not yet due.
- `src/sieve/store.py` — the content-addressed store.
- `src/sieve/pipeline.py` — the pipeline file format and loader.
- `src/sieve/gui.py` — the two panes and the ROI overlay.
- `tests/test_conformance.py` — the conformance suite, skipping whole at
  collection until real.

The harness has deliberately no file: not reached by the crop milestone, it is
a not-yet-due entry in `DEFERRED.md` with its trigger.

## Where contracts live

There is no contracts directory and no interfaces module, deliberately. Each
contract exists once, in code, at the boundary it governs, and everything else
derives from it — the GUI form, the validator, and the task hash are all
computed from a tool's `Params`, never restated (Exchange 1). Several
contracts aren't interfaces at all but *shapes*: to be a `Resample` you must
write a function with nowhere to put state, so misclassification is
inexpressible rather than tested for (Exchange 5). Enforcement lives in
tests, never convention (Exchange 6). The three formats consumed by git
history — the pipeline file, the automatic ledger, equivalence signatures —
carry their version inside the bytes and evolve additive-only. Until a
contract's code exists, it lives in the session record, and its placeholder's
docstring points at the section that holds it.

## Debt

Three files with three meanings; never "the ledger" unqualified:

- `DEBT.md` — hand-authored. Present debt no in-tree marker can carry.
- `DEFERRED.md` — hand-authored. Not-yet-due intentions, each with the
  trigger that makes it due. Building from this file goes poorly.
- `DEBT-AUTO.txt` — generated, never hand-edited. The automatic ledger of
  every in-tree marker, keyed (path, qualname), rule version pinned.

A placeholder *is* its debt entry: a real module at its real import path
raising `Owed("<reason>")` in marker form rule v1 (PLAN.md, Phase 2, decision
4). Presence in the tree is the authorization — there are no status fields
anywhere. Test-tree markers appear in the suite as skips carrying their
reason.

### Mismatch runbook

The suite goes red when `DEBT-AUTO.txt` disagrees with a fresh enumeration,
and the failure output is the entry-level diff — added, removed, changed.
If the change is one you made on purpose: `python -m sieve.debt write`, then
commit the regenerated ledger with the change it reflects. If it isn't:
investigate before regenerating — a reflexive regen launders real signal
("unintended debt change") into noise ("stale ledger").

## Working here

`pip install -e .` (Python 3.11, `src/` layout), then `pytest`. Green
includes placeholder skips exactly matching the automatic ledger's test-tree
entries. One decision at a time; a proposal is the deliverable — see the
working loop the plan encodes.
