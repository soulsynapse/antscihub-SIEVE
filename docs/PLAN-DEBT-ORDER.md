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
5. `20260802T225559Z` — the executor (PAR-0008), second after the roots.
6. Then dependency order, roots first, overriding intuition about
   importance — resolved here as each session closes: PAR-0009..0017
   (`20260802T225600Z`..`20260802T225608Z`), order not yet judged.
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
3. `20260802T225559Z` — the executor (PAR-0008), the head of the
   enumerated order and the next distillation proper.
