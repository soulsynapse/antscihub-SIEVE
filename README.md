# SIEVE

Signal Isolation for Ethological Video Events (SIEVE) isolates behavior from
video using interpretable signal-processing filters. The user builds a
pipeline; SIEVE runs it.

The repo is mid-rewrite: the architecture is settled, the skeleton is placed,
and real code lands next. This README is the map — where things are and which
record governs them. It restates nothing a governing doc or the tree already
records; when it seems to disagree with one of them, the other is right.

## The records

Three tiers, read downward only until convinced. The walking path and the
authority order — deeper governs, the synthesis reports and rolls up — are
[PAR-0001](docs/par/0001-project-architecture-rationale.md). Above the walk
sits tier 0, for doing rather than understanding: task-oriented guides in
[how-to/](how-to/), one domain folder per major seam
([PAR-0003](docs/par/0003-how-to-layer.md)); a guide that fails degrades to
one tier's walk down this chain, never to being stranded.

1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the synthesis: seven
   components, the authoring and execution flows, five invariants with
   their failure modes. The one-stop shop; read this first, usually last.
2. [docs/par/](docs/par/) — project architecture rationale (`PAR-NNNN`): the
   dated long-form reasoning, one named system per file, coarse enough that
   a record reads whole. These are living documents, not ADRs — edited in
   place whenever a reread finds them wanting, because the frozen record
   is one tier down. Each carries the doubts it has survived. A record no
   longer part of the architecture retires to `docs/par/retired/`.
3. `docs/archive/` — the frozen primary records:
   [DESIGN-BRIEF.md](docs/archive/DESIGN-BRIEF.md) (the design prompts,
   verbatim, including the rejected §8 EDIT kept as a recorded
   alternative), [DESIGN-SESSION.md](docs/archive/DESIGN-SESSION.md) (the
   argument that determines the code, in nine exchanges), and
   [PLAN.md](docs/archive/PLAN.md) (the exhausted conformance plan:
   phase gates, the settled layout, marker form rule v1, the definition
   of done).

The live planning cycle is
[docs/PLAN-TOOL-CONTRACT.md](docs/PLAN-TOOL-CONTRACT.md); a plan moves to
the archive when exhausted.

## The tree

Real code (the debt machinery,
[PAR-0002](docs/par/0002-debt-is-derived-from-the-tree.md) — the closed
class that gives every placeholder its meaning):

- `src/sieve/debt.py` — the `Owed` marker exception, the rule-v2
  enumerator (the Python AST surface and the text surface, walking the
  git index), the ledger serializer, and the regen command.
- `tests/conftest.py` — the adapter: a caught marker becomes a skip carrying
  its reason; one the enumerator can't see fails.
- `tests/_sentinel/` — the marker the enumerator must always find, so "no
  debt" and "enumerator dead" stay distinguishable.
- `tests/test_debt.py`, `test_automatic_ledger.py`, `test_adapter.py`,
  `test_import.py` — the machinery's own tests, including the mismatch test.

The components (which of these are still placeholders is `DEBT-AUTO.md`'s
job to say, not this list's; a placeholder's docstring and reason point at
the governing sections — follow the pointer before building):

- `src/sieve/kernel.py` — ops as values and the proved forms, one design
  unit (PAR-0005).
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
contracts aren't interfaces at all but *forms*: to be the affine coordinate
map you must write an op with nowhere to put state, so misclassification is
inexpressible rather than tested for (PAR-0005). Enforcement lives in
tests, never convention (Exchange 6). The three formats consumed by git
history — the pipeline file, the automatic ledger, equivalence signatures —
carry their version inside the bytes and evolve additive-only. Until a
contract's code exists, it lives in the session record, and its placeholder's
docstring points at the section that holds it.

## Debt

Three files with three meanings; never "the ledger" unqualified:

- `DEBT.md` — hand-authored. Present debt with no better file to carry
  its marker, stated as a column-0 `Owed:` line like any other text
  surface — so even the last resort enumerates, and the automatic
  ledger is the only file ever read for present debt.
- `DEFERRED.md` — hand-authored. Not-yet-due intentions, each with the
  trigger that makes it due. Building from this file goes poorly.
- `DEBT-AUTO.md` — generated, never hand-edited. The automatic ledger of
  every in-tree marker, keyed by location (path, qualname), identified
  by its UTC statement stamp, rule version pinned.

A placeholder *is* its debt entry: a real module at its real import path
raising `Owed("<stamp>: <reason>")` in marker form rule v2 (PAR-0002).
Any other tracked text file states one debt the same way — a column-0
`Owed: <stamp>: <reason>` line — which is how a settled system's owed
rationale lives as a stub record in `docs/par/`. Presence in the tree is
the authorization — there are no status fields anywhere. Test-tree
markers appear in the suite as skips carrying their reason.

### Mismatch how-to

The suite goes red when `DEBT-AUTO.md` disagrees with a fresh enumeration,
and the failure output is the entry-level diff — added, removed, changed.
If the change is one you made on purpose: `python -m sieve.debt write`, then
commit the regenerated ledger with the change it reflects. If it isn't:
investigate before regenerating — a reflexive regen launders real signal
("unintended debt change") into noise ("stale ledger").

## Working here

`pip install -e .` (Python 3.11, `src/` layout), then `pytest`. Green
includes placeholder skips exactly matching the automatic ledger's test-tree
entries. The working instructions — the loop, where records go, the
never-do list, session boundaries — are in [AGENTS.md](AGENTS.md).
