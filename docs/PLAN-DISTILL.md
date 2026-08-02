# Distillation plan

Scope: retire the `DEBT.md` entry filed under ARCH-0001 — every record
citation pointing below tier 2 in `docs/ARCHITECTURE.md`, `README.md`, or
`AGENTS.md` becomes an `ARCH-NNNN` citation — including the debt-and-records
machinery, whose absence from the rationale tier is where the doubt traffic
actually lands. No code. No marker is touched anywhere in this plan;
regen stays a no-op throughout.

This plan is a map, not a build authorization. Per the working loop each
distillation is proposed and confirmed individually before it lands.
Approving this plan settles the sequence, the working rules, and the
definition of done, nothing else.

This cycle runs concurrently with `docs/PLAN-TOOL-CONTRACT.md`: record
work and code work, separable under the chunking rule, neither blocking
the other. Distillation is front-loaded deliberately — the fidelity
check at acceptance leans on session memory that is depreciating, which
is the operative reason not to let this plan idle behind the code cycle.

## Working rules

Every distillation in this plan obeys ARCH-0001's three distillation rules
(provenance in Context, fidelity at acceptance, roll-up per decision) plus
four rules this plan adds:

1. **Quote, don't paraphrase, at the load-bearing points.** The decisive
   source sentences appear verbatim; the record's own prose is connective
   tissue. Drift then surfaces as a diffable misquote, and the quotes
   double as rereading anchors. Pushed to its limit this rule defeats
   itself — a quilt of quotations is exactly the fragment-assembly a
   rationale exists to spare the reader — so the quotes carry the
   decisions and the prose carries the argument, which has to stand up if
   only the prose is read.
2. **Each proposal names its decision boundary** — which decisions it
   contains, which neighbours it touches. Boundaries follow ARCH-0001's
   test — the smallest chunk that carries everything relevant with it —
   so a record needing a sibling read alongside it is one record cut in
   two, and one that has swallowed a decision it doesn't need is two
   fused. Forward citations are authored; back-links are grepped, never
   stored.
3. **Doubt traffic outranks the listed order.** The sequence below is a
   default. A decision Kendrick is currently doubting jumps the queue —
   that is the read loop working, not the plan failing.
4. **One distillation, one commit**: the record and its `ARCHITECTURE.md`
   citation amendment land together; the `DEBT.md` entry retires citation
   by citation as they land.

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
failure ARCH-0001 exists to remove. Leaving those decisions in tier 3
also made the `DEBT.md` done condition unreachable: invariant 1 cites
`archive/PLAN.md` Phase 1 decision 2, so a below-tier-2 citation sat in
the synthesis with no way to retire.

Resolution as recorded in ARCH-0001: the work list derives from the
below-tier-2 citations in `docs/ARCHITECTURE.md`, `README.md`, and
`AGENTS.md`, and plan-gate architecture decisions are on it. Sequencing
calls genuinely a plan's own — scope, order, build sequence, definition
of done — stay in their plans.

Exit: settled. Phase 2 proceeds.

---

## Phase 2 — The debt and records machinery

Distills, from `docs/archive/PLAN.md` and the practices AGENTS.md points
at: the anti-bureaucracy invariant, the placeholder doctrine (the
placeholder *is* the debt entry, which is what makes `DEBT-AUTO.txt`
derivable), the classification rule, the three-file taxonomy, marker form
rule v1, and the instruments. **One record — `ARCH-0002` — drafted
2026-08-02 and sitting Proposed.** The layout settlement, named alongside
these in `AGENTS.md`, is component decomposition rather than debt
machinery and moves to Phase 5.

**Gate (one decision): seeding reconstructed challenges.** Kendrick has
doubted the debt system roughly three times; those fend-offs predate the
machinery and exist only in his memory. The proposal is to seed the
record's Challenges section with the doubts he can still reconstruct —
elicited from him in that session, dated approximately, and marked
*reconstructed* so they are never mistaken for contemporaneous entries.
ARCH-0001 neither provides for nor forbids this; the alternative is
folding them into Context as objections considered, at the cost of not
being formatted where doubt #4 will look.

Exit: the debt machinery is governed from tier 2; its challenge surface
exists; the reconstructed entries are in whichever home the gate chose.

---

## Phase 3 — Core semantics

The decisions everything else leans on. Three units:

1. **Shape taxonomy and classification-by-form** (Exchanges 3 and 5;
   invariant 3): the five shapes, `Opaque` as the escape hatch,
   reshaping as semantics-preserving.
2. **The intent/progress split and the store** (Exchanges 1 and 5):
   pipeline holds intent only; recipe-hash addressing, no invalidation,
   completeness as a query. Recorded as one unit — the split is what the
   store's design follows from, so they do not read apart.
3. **Param versus preference** (Exchange 2; invariant 5), including
   "anything ambiguous is a param."

Exit: the units above are recorded, each with its citation amendment.

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

Exit: the units above are recorded, each with its citation amendment.

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
4. **The layout settlement** (`archive/PLAN.md` Phase 3), moved here from
   Phase 2: flat modules except `tools/`, the five-shape algebra as one
   design unit, `views.py` as the tool↔GUI boundary language, `render`
   without `sweep`. It lands last because it cites the component records
   above and reads better once they exist.

Exit: the units above are recorded, each with its citation amendment.

---

## Phase 6 — Exit

Final pass against the definition of done. Anything failing it is fixed
or entered as present debt.

**Definition of done** (approving this plan confirms this scope
reading):

- [ ] `docs/ARCHITECTURE.md`, `README.md`, and `AGENTS.md` cite nothing
      deeper than `docs/arch/`; the distillation entry in `DEBT.md` is
      retired.
- [ ] Every distillation quotes its decisive source sentences verbatim
      and names its provenance (source passages, original date) in
      Context.
- [ ] No decision boundary was drawn silently: each record names what
      it was decided against, and reads whole.
- [x] The Phase 1 gate is resolved on the record (2026-08-01, above).
- [ ] The debt machinery is governed from tier 2, with its challenge
      surface in place.
- [ ] Every gate decision above is recorded in this document at the
      phase that made it — the decision, the reasoning, the date.
- [ ] Suite green, regen a no-op, working tree clean.

---

## After this plan

The directory goes quiet, now for the ARCH-0001 reason and truly:
distillation is complete, records are written rarely, and challenge
entries accumulate organically wherever the read loop lands. This plan
freezes under its name and moves to `docs/archive/` when exhausted.

## Known risks

- **Individuation drift.** The session's decisions are entangled;
  one-file-per-decision imposes boundaries the source doesn't have.
  Coarse boundaries and living records make this far cheaper than it
  was under the immutable reading — a wrong boundary is repaired by
  rewriting the records, not by superseding several at once — but the
  unit lists in Phases 3–5 predate the coarse-granularity call and are
  re-judged at each phase's proposal rather than taken as settled.
- **The oracle depreciates.** Fidelity at acceptance leans on session
  memory that fades; this is the front-loading argument, and it means
  the risk grows with every session this plan idles. A stalled Phase 5
  is reviewed by a weaker oracle than a prompt one.
- **Date flattening.** All distillations will carry near-identical
  dates, so the later-supersedes-earlier rule loses its tiebreaker
  among them, and the session's internal ordering ("later exchanges
  supersede earlier ones") goes flat. Mitigation: any genuine tension
  between founding decisions is resolved explicitly at distillation
  time, on the record — never left to the date rule.
- **Reconstructed challenges are the paraphrase risk in its purest
  form** — memory of an argument, formatted as a record. Mitigation:
  elicited from Kendrick directly, marked reconstructed, and carrying
  approximate dates; if his reconstruction is too dim to state a doubt
  crisply, the entry is not written.
