# SESSION-2026-08-02 — The distillation work list is stated debt

Status: Frozen
Date: 2026-08-02

One argument, from a skeptic review of `docs/PLAN-DISTILL.md`: how the
distillation work list is known. The scope directions that surrounded it
in the same sitting — which systems, what order, what each awaits — are
direction rather than argument and live where they landed, in the
`DEBT.md` entry.

## Exchange 1 — The citation-derived work list leaks

PAR-0001 defined the work list as exactly the set of record citations
pointing below tier 2 in `docs/ARCHITECTURE.md`, `README.md`, and
`AGENTS.md`. The review checked the plan against that list; Kendrick
checked the list against the source:

> "nah wait a second it is genuinely necessary, there's no governing
> record of a boatload of systems named in design session."

A sweep of `DESIGN-SESSION.md` confirmed it. Two settled systems carry
no tier-1 citation at all — file-format versioning and migration
(Exchange 1: additive-only discipline, migrate-then-validate, the
fixture corpus, unknown-field preservation) and handles/materialization
(Exchange 2) — and the selection mechanism (Exchange 7), though in the
session's own settled list, was owned by no plan unit. The mechanism of
the leak: a conclusion stated in tier 1 *without* a citation (README's
"three formats... evolve additive-only" names no exchange) or not
stated there at all never enters a citation-derived list, so the plan's
done condition could pass with settled systems never distilled.

## Exchange 2 — Drafts-as-worklist rejected; the list is stated debt

The agent proposed landing every system as a `Proposed` stub so the
work list would be derivable — `grep -l "^Status: Proposed" docs/par/`,
a system unable to escape its own draft, the placeholder doctrine
applied at tier 2. Rejected:

> "drafts are a new mechanism btw, and aren't necessary, stated debt
> should be picked up, and the argued necessity for any kind of todo
> list is argument for a more exacting debt system"

Resolution: the enumerated systems are stated debt in `DEBT.md`. That
is the file's charter — a present gap no marker can carry — and
non-derivability is exactly the entry criterion; a hole in a derivation
is evidence the debt system should be more exacting, never that a
parallel mechanism should exist. The below-tier-2 citation set survives
as the roll-up checklist each acceptance amends, not as the work list's
definition.

What lost, with reasons: the citation-derived work list (incomplete by
construction — it cannot see a never-cited system); stub drafts as
tier-2 placeholders (new machinery duplicating `DEBT.md`'s job, and a
sheaf of ceremonial records landing at once is the apparatus
elaborating faster than the content it holds).

Consequences carried with this record: PAR-0001's work-list paragraph
rewritten citing this primary; the `DEBT.md` entry now enumerates the
systems; `PLAN-DISTILL.md`, its sequencing superseded by that entry,
froze under a supersession note and moved to `docs/archive/`. The
plan's own added working rules lapse with it — quote-verbatim at
load-bearing points judged not important (2026-08-02) — leaving
PAR-0001's three distillation rules standing alone.
