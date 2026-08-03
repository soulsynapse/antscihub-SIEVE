# Distillation order

Date: 2026-08-03

The first planning decision over the v2 ledger (PAR-0002, "The planning
surface"): the ordering judgment stated 2026-08-02 in the dissolved
`DEBT.md` enumeration, landed here citing stamps. IDs are stamps; a
cited stamp no longer enumerated means exactly one thing — discharged.
Insertion is an edit to this file; markers are never renumbered. This
plan orders the rationale debts only; code work is
`PLAN-TOOL-CONTRACT.md`'s.

Definition of done, carried from the statement: every system governed
from `docs/par/` and the three tier-1 documents citing nothing deeper,
each acceptance amending the tier-1 citations in the same commit; the
exchange or gate citation governs until then.

The order:

1. `20260802T210348Z` — PAR-0003's design session, first.
2. `20260802T225556Z` — shape algebra and classification by form
   (PAR-0005), root.
3. `20260802T225557Z` — param vs. preference (PAR-0006), root.
4. `20260802T225558Z` — the tool contract (PAR-0007), first after the
   roots.
5. `20260802T225559Z` — the executor (PAR-0008). **Demoted 2026-08-03**
   out of second-after-the-roots and into the as-the-repo-takes-shape
   group below. Its one irreversible decision — `render(node, frame)`
   primary, with batch a coarsening of the pull path, because building
   batch-first bolts on a second and subtly different preview path
   later — was settled in `DESIGN-SESSION.md` Exchange 4 and is already
   recorded in `ARCHITECTURE.md`. The rest is peephole work:
   individually justified, independently tested against the naive path,
   independently deletable. That is the whole argument for a peephole
   set rather than a planner, and it means nothing left in this
   rationale is expensive to get wrong later.
6. **The remaining order, judged 2026-08-03** by the one-way-door filter
   rather than by importance or dependency (PAR-0007's sitting, primary
   `SESSION-2026-08-03-tool-contract-scope.md` Exchange 4): a rationale
   is distilled *before* code when being wrong later costs a rewrite or
   a store migration, and lands as its system takes shape otherwise.
   Importance was the intuition this filter overrides — the harness and
   the executor feel central and neither is expensive to defer.

   Before code:

   - `20260802T225600Z` — the intent/progress split and the store
     (PAR-0009). The recipe hash *is* the store's address and the store
     never invalidates, so the address format is permanent by
     construction and changing it orphans every value ever stored. It is
     also concurrent with the tool contract rather than prior to it:
     `PLAN-TOOL-CONTRACT.md` Phase 2's ordering note calls the op
     representation feeding the hash the largest blast radius in that
     cycle. Its marker's "discussion owed before drafting" stands.
   - `20260802T225607Z` — SIEVE format versioning and migration
     (PAR-0016). The pipeline file is read by git history, old files
     exist forever, and a retired field name may never be reused, so the
     additive-only discipline and the migration key must be right before
     the first format ships. Alone among these, it cannot be repaired by
     editing code.

   As the repo takes shape, each because its door is already shut or
   there is none: PAR-0008 (`20260802T225559Z`), PAR-0010
   (`20260802T225601Z`), PAR-0011 (`20260802T225602Z`), PAR-0012
   (`20260802T225603Z`), PAR-0013 (`20260802T225604Z`), PAR-0014
   (`20260802T225605Z`), PAR-0015 (`20260802T225606Z`), PAR-0017
   (`20260802T225608Z`).

   Two riders, so they are not drifted into rather than decided. PAR-0014
   carries one irreversible clause — configuring a step applies to all
   its siblings, with per-branch override as the marked exception, and
   Exchange 2 states outright that a per-branch default can never be
   reversed — which becomes a gate item wherever the pipeline tree view
   is built, ahead of that rationale. And PAR-0012 sits last in practice
   whatever its position here: its trigger is the first second
   implementation of any op, and its own stub opens by asking whether it
   exists as a system at all.
7. `20260803T065949Z` — configuration interchange (PAR-0019), inserted
   2026-08-03, after PAR-0012 and PAR-0011: its first question is the
   seam against them, which cannot be judged before they are.
8. `20260802T225609Z` — the layout settlement (PAR-0018), last; it cites
   the component records.

## Next session (picked 2026-08-03)

Status is not restated here: `grep -l "^Status: Proposed" docs/par/*.md`
gives what is drafted and not yet governing, and the ledger gives what
remains stamped. Drafting discharges a stamp without making a rationale
govern, so those two lists diverge; the pick is the judgment over them.

1. **PAR-0006's argument, before PAR-0007's judgment.** Both were
   drafted without one. PAR-0006 is a root and PAR-0007 borrows from
   it — the tool contract's silence on preferences is load-bearing only
   if PAR-0006's boundary holds — so arguing it second makes the borrow
   circular.
2. **PAR-0007's judgment**, by attack rather than direct call: it was
   authored and judged by the same eyes in one sitting, which is the
   how-to's own criterion (§1). Its refusal of the voiding declaration
   is a correction to an accepted rationale, so PAR-0005 is amended or
   the refusal falls.
3. `20260802T225600Z` — the intent/progress split and the store
   (PAR-0009), which the 2026-08-03 judgment above puts before code
   alongside PAR-0016, and which its own marker says needs discussion
   before drafting.
