# DEBT — present, correct debt (hand-authored)

Type-1 debt: real gaps that exist right now. A placeholder in the tree is
one category of this type, tracked automatically in DEBT-AUTO.txt; entries
here are the gaps no marker can carry. Nothing goes here that is not
presently owed.

- **Founding decisions not yet distilled** (2026-08-01, PAR-0001; work
  list restated as this enumeration 2026-08-02, primary:
  `SESSION-2026-08-02-distill-worklist.md` — the citation-derived list
  proved incomplete, two settled systems having no tier-1 citation at
  all). Each system below is owed its rationale, drafted and assessed in
  its own session; the exchange or gate citation governs until then.
  Retired system by system, each acceptance amending the tier-1
  citations in the same commit. Done when every system here is governed
  from `docs/par/` and the three tier-1 documents cite nothing deeper.
  Priority: PAR-0003's design session first; then dependency order,
  roots first, overriding intuition about importance. The systems:
  - shape algebra and classification-by-form (Ex 3, 5) — root
  - param vs. preference (Ex 2) — root; discussion owed
  - the tool contract (Ex 5 rebuilt, Ex 2; claims invariant 1's
    `archive/PLAN.md` Phase 1 decision 2 citation) — first after the roots
  - the executor (Ex 3, 4, 6) — second
  - intent/progress split and the store (Ex 1, 5) — discussion owed
  - handles and materialization (Ex 2) — merge-into-store question open
  - the selection mechanism (Ex 7 as rebuilt by Ex 8) — needs refinement;
    merge-into-executor question open
  - the harness (Ex 8, 9) — whether it genuinely exists as a system,
    unbuilt and possibly argued against elsewhere, is its first question
  - GUI type-dispatch and the closed vocabularies (Ex 1, 2) — owed
    elaboration to be perfectly clear
  - pipeline construction (Ex 2, 6, 7)
  - run semantics (Ex 3, 4) — boundary against shape algebra open
  - SIEVE format versioning and migration (Ex 1, 9) — SIEVE-facing
    formats only, likely stricter; repo-machinery formats are PAR-0002's
  - enforcement lives in tests, never convention (Ex 1, 5, 6) — gated on
    PAR-0003's design settling what the explicit enforcement is
  - the layout settlement (`archive/PLAN.md` Phase 3) — last; cites the
    component records
  Unclaimed tier-1 citations to assign at the owning distillation:
  README's Exchange 1 (contracts derive from `Params`) and Exchange 6
  (enforcement in tests).

- **The runbook layer is named but not designed** (2026-08-02,
  PAR-0003). The how-to guides — derived-and-tested runbooks for the
  systems the rationales govern — have no form, home, or verification
  discipline; how execution should respect the rationale is left to the
  reader, with the orphaned fragments (README's mismatch runbook,
  AGENTS.md's Procedures) as the leak's evidence. Retired when a design
  session settles the system and PAR-0003 is rewritten to govern it.
  Primary: `SESSION-2026-08-02-runbook-gap.md`.

- **The v2 dissolution of this file is pending** (2026-08-03,
  PAR-0002 as amended; primary:
  `SESSION-2026-08-02-debt-advance.md`). Marker rule v2 and its
  machinery govern and are landed; what has not landed: the fourteen
  stub records (PAR-0005..0018, stamps 20260802T225556Z+i, statement
  event b5cce1b) replacing the distillation entry above; PAR-0003's
  own `Owed:` line (stamp 20260802T210348Z, statement event e32966b)
  replacing the runbook entry; the first planning decision
  (`docs/PLAN-DEBT-ORDER.md`) carrying the priority line above; and
  the then-stale passages — `AGENTS.md` "Distillation runs system by
  system from its DEBT.md entry" and PAR-0001's "filed in DEBT.md /
  enumerated systems live in that entry" and "cannot be derived"
  paragraphs — repointed at the stubs. Retired when this file holds
  nothing and the suite is green. Stub form: title + `Status:
  Proposed` + date + the `Owed:` marker + provenance citation, never
  rationale prose.

(The adapter naming asymmetry recorded here on 2026-08-01 was resolved
the same day by the step 6.5 collection-time rework.)
