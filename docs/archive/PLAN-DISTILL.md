# Distillation plan

**Superseded and frozen, 2026-08-02.** Phases 3–6 never ran. The
citation-derived work list this plan sequenced proved incomplete —
settled systems never cited from tier 1 escaped it — and the work list
is now stated debt: the enumerated systems in `DEBT.md`, each drafted
and accepted in its own session. Primary:
`SESSION-2026-08-02-distill-worklist.md`. Nothing below this note is
edited again.

Scope: retire the distillation entry in `DEBT.md` — every record
citation pointing below tier 2 in `docs/ARCHITECTURE.md`, `README.md`,
or `AGENTS.md` becomes a `PAR-NNNN` citation. The debt-and-records
machinery led the queue because its absence from the rationale tier was
where the doubt traffic landed; it now has a drafted record awaiting
acceptance (Phase 2). The runbook entry in `DEBT.md` (PAR-0003) is a
different debt and not this plan's scope. No code. No marker is touched
anywhere in this plan; regen stays a no-op throughout — the marker
reasons that cite exchanges are the anticipated `changed`-entry case in
PAR-0002's Consequences, and repointing them waits past this plan.

This plan is a map, not a build authorization. Per the working loop each
distillation is proposed and confirmed individually before it lands.
Approving this plan settles the sequence, the working rules, and the
definition of done, nothing else.

This cycle runs concurrently with `docs/PLAN-TOOL-CONTRACT.md`: record
work and code work, separable under the chunking rule, neither blocking
the other. Distillation stays front-loaded, but on the narrowed ground
recorded in `SESSION-2026-08-02-record-class.md` Exchange 13: the
founding *answers* have survived two rewrites and are not session
memory; what depreciates is the argument shape — which alternatives
died, and why. Front-loading protects that, and only that.

Rewritten 2026-08-02 against PAR-0001 as it now stands (the record-class
and PAR sessions); git holds the prior version.

## Working rules

Every distillation obeys PAR-0001's three distillation rules —
provenance in Context, fidelity at acceptance, roll-up per decision —
plus four rules this plan adds:

1. **Quote, don't paraphrase, at the load-bearing points.** The decisive
   source sentences appear verbatim; the record's own prose is
   connective tissue. Drift then surfaces as a diffable misquote, and
   the quotes double as rereading anchors. Pushed to its limit this rule
   defeats itself — a quilt of quotations is exactly the
   fragment-assembly a rationale exists to spare the reader — so the
   quotes carry the decisions and the prose carries the argument, which
   has to stand up if only the prose is read.
2. **Each proposal names its decision boundary in PAR-0001's terms: one
   PAR is one named system.** Near-decomposability draws it — dense
   interactions inside the unit, sparse across it — and within the
   boundary the unit is the smallest *self-sufficient* chunk, so the
   record reads whole without a sibling open beside it. A proposal
   defends its boundary with the revision test: simulate the decision
   reversing, and if rewriting this record would force substantially
   rewriting another, merge or make the dependency a citation. A
   sub-system in service to a larger one may take its own record where
   the pointer criterion holds — exactly one place it lives, exactly one
   way to cite it. Forward citations are authored; back-links are
   grepped, never stored.
3. **Doubt traffic outranks the listed order.** The sequence below is a
   default. A decision Kendrick is currently doubting jumps the queue —
   that is the read loop working, not the plan failing.
4. **The roll-up travels with acceptance** (PAR-0001's rule, restated
   for the sequence here). A distillation drafts `Proposed` and does
   not govern; the exchange or gate citation stays the governing
   pointer, which is what makes drafting free — a draft can sit, and
   nothing in the repo is inconsistent while it does. Acceptance of a
   distillation is the fidelity review against its source, nothing
   else, and the accepting commit is the unit: it flips the status
   line, amends the tier-1 citations, and retires the corresponding
   `DEBT.md` citations together. Where a draft supplies reasoning its
   source leaves implicit, those places are enumerated when the draft
   lands — in the session primary when a session produced it,
   otherwise at the owning phase of this plan — and the review settles
   each one; PAR-0002's four flags
   (`SESSION-2026-08-02-record-class.md`, Exchange 10) are the live
   instance. Draft and acceptance landing in one sitting collapse to
   one commit — the expected common case.

---

## Phase 1 — The scope gate

**Gate (one decision): does distillation reach architecture decisions
recorded in plan gates? — settled 2026-08-01: yes, on the same eager
trigger as the founding decisions.** The substantive reason is the
challenge surface. The most-doubted decision in the repo — the debt
system — is settled in `docs/archive/PLAN.md`: marker form rule v1, the
classification rule, the layout settlement. A frozen plan can hold
neither a Challenges entry nor a supersession, so each doubt against it
re-litigates from scratch and leaves nothing behind, which is the
failure PAR-0001 exists to remove. Leaving those decisions in tier 3
also made the `DEBT.md` done condition unreachable: invariant 1 cites
`archive/PLAN.md` Phase 1 decision 2, so a below-tier-2 citation sat in
the synthesis with no way to retire.

Resolution as recorded in PAR-0001: the work list derives from the
below-tier-2 citations in `docs/ARCHITECTURE.md`, `README.md`, and
`AGENTS.md`, and plan-gate architecture decisions are on it. Sequencing
calls genuinely a plan's own — scope, order, build sequence, definition
of done — stay in their plans.

Exit: settled. Phase 2 proceeds.

---

## Phase 2 — The debt and records machinery

**PAR-0002 is Accepted (2026-08-02) and governs the debt machinery.**
It distills the anti-bureaucracy invariant, the placeholder doctrine,
the classification rule, the three-file taxonomy, marker form rule v1,
and the instruments. The layout settlement, named alongside these in
`AGENTS.md`, is component decomposition rather than debt machinery and
lands in Phase 5.

The acceptance review (2026-08-02, primary:
`SESSION-2026-08-02-par-0002-acceptance.md`) machine-verified every
quoted passage against `archive/PLAN.md` and against the code, upheld
the four daylight flags named in the record-class primary (Exchange 10)
as written, and fixed one paraphrase that misattributed a causal link
(fixture-tree testing follows from the enumerator's root-path
parameter, not from the single roots definition). The accepting commit
carried the roll-up: `README.md`'s two citations and `AGENTS.md`'s
pointer became `PAR-0002`, with `PLAN.md` still holding the layout
settlement until Phase 5. In-code docstring citations (`debt.py`,
`conftest.py`) repointed in a separate code-chunk commit — they were
outside the enumerated roll-up, decided at review. Deliberately not
tightened, per the governing-pending-improvement stance recorded in the
primary: `README.md`'s "Real code" heading folding the machinery's own
tests into the closed class, and two review narrowings (teardown
gating, non-empty reasons) carried by the code and `archive/PLAN.md`
step 6.5 rather than the record.

**Gate (one decision): seeding reconstructed challenges — settled
2026-08-02: no.** Neither offered option was taken. The doubts Kendrick
has raised against the debt system (roughly three, predating the
machinery and existing only in memory) are not reconstructed into a
Challenges section, nor folded into Context as objections considered.
His reason decided it: he may not recall them reliably, but they recur
on their own — three times already — and a recurrence lands as an
ordinary contemporaneous entry, which is what the section is for.
Reconstruction would have bought entries of the weakest available kind,
to fill a section that fills itself.

Consequence: PAR-0002 lands with no Challenges section, and that is
correct rather than an omission. The challenge surface is the record
existing at tier 2 — somewhere for doubt #4 to land — not entries in it.

Exit: reached 2026-08-02. PAR-0002 Accepted with its roll-up landed;
the debt machinery governed from tier 2 and its challenge surface in
place.

---

## Phase 3 — Core semantics

The decisions everything else leans on. Numbering continues from 0005 —
PAR-0003 and PAR-0004 went to live decisions mid-plan, which is the
uniform numbering doing its job, not a collision. Three units:

1. **Shape taxonomy and classification-by-form** (Exchanges 3 and 5;
   invariant 3): the five shapes, `Opaque` as the escape hatch,
   reshaping as semantics-preserving.
2. **The intent/progress split and the store** (Exchanges 1 and 5):
   pipeline holds intent only; recipe-hash addressing, no invalidation,
   completeness as a query. Recorded as one unit — the split is what the
   store's design follows from, so they do not read apart.
3. **Param versus preference** (Exchange 2; invariant 5), including
   "anything ambiguous is a param."

Exit: the units above are Accepted, each with its roll-up landed.

---

## Phase 4 — Components

1. **Tools as pure front-ends** (Exchange 5 rebuilt version; naming —
   Tool / Step / Task — Exchange 2). Cites the shape record
   (`lower()` returns into its vocabulary).
2. **The executor as the sole coupler** (Exchanges 4 and 6): naive
   evaluator plus profiled peepholes, not a planner.
3. **The harness** (Exchange 8; invariant 4): equivalence earned by
   measurement, rankings measured, sensitivity bounds; the user-exposed
   equivalence question stays in `DEFERRED.md` with its trigger.

Exit: the units above are Accepted, each with its roll-up landed.

---

## Phase 5 — Surface and run semantics

1. **GUI type-dispatch and the closed layer vocabulary** (Exchanges 1
   and 2; invariant 2).
2. **Building a pipeline** (Exchange 2; Exchange 6 condition 3;
   Exchange 7): branch-set mapping with marked overrides, eligibility
   as a dispatch query, greyed-with-reason.
3. **Run semantics** (Exchanges 3 and 4): fusion, decimation hoisting,
   fold-sweep persistence, invertible geometry and the free-floating
   base layer.
4. **The layout settlement** (`archive/PLAN.md` Phase 3), moved here
   from Phase 2: flat modules except `tools/`, the five-shape algebra as
   one design unit, `views.py` as the tool↔GUI boundary language,
   `render` without `sweep`. It lands last because it cites the
   component records above and reads better once they exist.

Exit: the units above are Accepted, each with its roll-up landed.

---

## Phase 6 — Exit

Final pass against the definition of done. Anything failing it is fixed
or entered as present debt.

**Definition of done** (approving this plan confirms this scope
reading):

- [ ] `docs/ARCHITECTURE.md`, `README.md`, and `AGENTS.md` cite nothing
      deeper than `docs/par/`; the distillation entry in `DEBT.md` is
      retired. (The runbook entry is PAR-0003's debt, not this plan's.)
- [ ] No distillation is left `Proposed`: every record this plan
      produced is Accepted, its daylight flags settled at review, its
      roll-up landed in the accepting commit.
- [ ] Every distillation quotes its decisive source sentences verbatim
      and names its provenance (source passages, original date) in
      Context.
- [ ] No decision boundary was drawn silently: each record names its
      system and what it was decided against, and reads whole.
- [x] The Phase 1 gate is resolved on the record (2026-08-01, above).
- [x] The Phase 2 reconstructed-challenges gate is resolved on the
      record (2026-08-02, above).
- [ ] Every gate decision above is recorded in this document at the
      phase that made it — the decision, the reasoning, the date.
- [ ] Suite green, regen a no-op, working tree clean.

---

## After this plan

The distillation debt is gone: the founding reasoning governs from
tier 2, doubts have somewhere to land, and no reader is sent below
`docs/par/` by a tier-1 document. The directory does not yet go quiet,
and this plan no longer claims it will — PAR-0003 owes its design
session (`DEBT.md`) and PAR-0004 its first templates once it governs.
That traffic belongs to those systems; what ends here is distillation. This
plan freezes under its name and moves to `docs/archive/` when exhausted.

## Known risks

- **Individuation drift.** The session's decisions are entangled, and
  record boundaries impose structure the source doesn't have. The unit
  lists in Phases 3–5 predate the named-system criterion and are
  re-judged at each phase's proposal rather than taken as settled. The
  residual risk is bounded from two sides: the revision test catches a
  leaked boundary at proposal time, and a boundary that ships wrong is
  falsifiable from the tree afterwards — Challenges entries straddling
  two records, or clustering into separable concerns inside one — and
  is repaired by re-individuating living records, losslessly, numbers
  never reused.
- **The curator is unchecked where reasoning was discovered live.** For
  the founding decisions the oracle-depreciation worry was overstated,
  and this rewrite acts on the correction flagged in
  `SESSION-2026-08-02-record-class.md` Exchange 13: the answers survived
  two rewrites and are not session memory. What does depreciate is the
  argument shape — which alternatives died, and why — and for decisions
  settled in plan gates rather than the design session, that shape has
  no dense primary underneath it. Front-loading protects a narrower
  thing than the original plan claimed, but still a real one.
- **Date flattening.** Distillations carry their decisions' original
  dates, which cluster tightly (the design session; 2026-08-01 for the
  plan gates), so the later-supersedes-earlier rule loses its tiebreaker
  among them, and the session's internal ordering ("later exchanges
  supersede earlier ones") goes flat. Mitigation: any genuine tension
  between founding decisions is resolved explicitly at distillation
  time, on the record — never left to the date rule.
- ~~**Reconstructed challenges are the paraphrase risk in its purest
  form**~~ — retired 2026-08-02 by the Phase 2 gate: nothing is
  reconstructed, so the risk has no surface. Challenges accumulate only
  as doubts actually recur.
