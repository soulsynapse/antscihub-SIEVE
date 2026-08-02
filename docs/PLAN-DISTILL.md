# Distillation plan

Scope: retire the `DEBT.md` entry filed under ADR-0001 — every record
citation pointing below tier 2 in `docs/ARCHITECTURE.md`, `README.md`, or
`AGENTS.md` becomes an ADR citation — including the debt-and-records
machinery, whose absence from the ADR tier is where the doubt traffic
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

Every distillation in this plan obeys ADR-0001's four distillation rules
(provenance in Context, governing on acceptance, fidelity at acceptance,
roll-up per decision) plus four rules this plan adds:

1. **Quote, don't paraphrase, at the load-bearing points.** The decisive
   source sentences appear verbatim; the ADR's own prose is connective
   tissue. Drift then surfaces as a diffable misquote, and the quotes
   double as rereading anchors.
2. **Each proposal names its decision boundary** — which decisions it
   contains, which entangled siblings it touches — and entangled ADRs
   cross-cite each other, so superseding one flags the others.
3. **Doubt traffic outranks the listed order.** The sequence below is a
   default. A decision Kendrick is currently doubting jumps the queue —
   that is the read loop working, not the plan failing.
4. **One distillation, one commit**: the ADR, its `ARCHITECTURE.md`
   citation amendment, and its cross-cites land together; the `DEBT.md`
   entry retires citation by citation as they land.

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
failure ADR-0001 exists to remove. Leaving those decisions in tier 3
also made the `DEBT.md` done condition unreachable: invariant 1 cites
`archive/PLAN.md` Phase 1 decision 2, so a below-tier-2 citation sat in
the synthesis with no way to retire.

Resolution as recorded in ADR-0001: the work list derives from the
below-tier-2 citations in `docs/ARCHITECTURE.md`, `README.md`, and
`AGENTS.md`, and plan-gate architecture decisions are on it. Sequencing
calls genuinely a plan's own — scope, order, build sequence, definition
of done — stay in their plans.

Exit: settled. Phase 2 proceeds.

---

## Phase 2 — The debt and records machinery

Distills, from `docs/archive/PLAN.md` and the
practices AGENTS.md points at: marker form rule v1, the placeholder
doctrine (the placeholder *is* the debt entry, which is what makes
`DEBT-AUTO.txt` derivable), the classification rule, and the layout
settlement — individuated at proposal time, likely two to three ADRs.

**Gate (one decision): seeding reconstructed challenges.** Kendrick has
doubted the debt system roughly three times; those fend-offs predate the
machinery and exist only in his memory. The proposal is to seed the new
ADR's Challenges section with the doubts he can still reconstruct —
elicited from him in that session, dated approximately, and marked
*reconstructed* so they are never mistaken for contemporaneous entries.
ADR-0001 neither provides for nor forbids this; the alternative is
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
2. **The intent/progress split and the store** (Exchanges 1 and 5;
   entangled pair, cross-cited): pipeline holds intent only;
   recipe-hash addressing, no invalidation, completeness as a query.
3. **Param versus preference** (Exchange 2; invariant 5), including
   "anything ambiguous is a param."

Exit: three to four ADRs landed, each with its citation amendment.

---

## Phase 4 — Components

1. **Tools as pure front-ends** (Exchange 5 rebuilt version; naming —
   Tool / Step / Task — Exchange 2). Cross-cites the shape ADR
   (`lower()` returns into its vocabulary).
2. **The executor as the sole coupler** (Exchanges 4 and 6): naive
   evaluator plus profiled peepholes, not a planner.
3. **The harness** (Exchange 8; invariant 4): equivalence earned by
   measurement, rankings measured, sensitivity bounds; the user-exposed
   equivalence question stays in `DEFERRED.md` with its trigger.

Exit: three ADRs landed, each with its citation amendment.

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

Exit: three ADRs landed, each with its citation amendment.

---

## Phase 6 — Exit

Final pass against the definition of done. Anything failing it is fixed
or entered as present debt.

**Definition of done** (approving this plan confirms this scope
reading):

- [ ] `docs/ARCHITECTURE.md`, `README.md`, and `AGENTS.md` cite nothing
      deeper than `docs/adr/`; the distillation entry in `DEBT.md` is
      retired.
- [ ] Every distillation quotes its decisive source sentences verbatim
      and names its provenance (source passages, original date) in
      Context.
- [ ] Entangled ADRs cross-cite; no decision boundary was drawn
      silently.
- [x] The Phase 1 gate is resolved on the record (2026-08-01, above).
- [ ] The debt machinery is governed from tier 2, with its challenge
      surface in place.
- [ ] Every gate decision above is recorded in this document at the
      phase that made it — the decision, the reasoning, the date.
- [ ] Suite green, regen a no-op, working tree clean.

---

## After this plan

The directory goes quiet, now for the ADR-0001 reason and truly:
distillation is complete, ADRs are written rarely, and challenge
entries accumulate organically wherever the read loop lands. This plan
freezes under its name and moves to `docs/archive/` when exhausted.

## Known risks

- **Individuation drift.** The session's decisions are entangled;
  one-file-per-decision imposes boundaries the source doesn't have, and
  the boundaries determine what can later be superseded independently.
  Mitigation: working rule 2 — but a boundary can be named out loud and
  still be wrong, and repairing one later means superseding more than
  one record at once.
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
