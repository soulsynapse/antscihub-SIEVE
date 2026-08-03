# PAR-0003 — The runbook layer

Status: Proposed
Date: 2026-08-02

Owed: 20260802T210348Z: the runbook layer's design session — form, home, naming, and the derivation-and-test discipline — after which this record is rewritten to govern the settled system; open directions: SESSION-2026-08-02-runbook-gap.md

## Context

The tiers as they stand: `docs/ARCHITECTURE.md` holds the settled what,
`docs/par/` the why, `docs/archive/` the frozen record. How execution in
the repo should respect the rationale is left to the reader. In diataxis
terms, tutorials arrive by convention from working in the repo, and PAR
carries the explanation and the reference for working in the repo
directly; the how-to guides — task-oriented, the derived-and-tested
runbooks of the systems the rationales speak to — have no named home.

The gap is already leaking, which is the evidence it is real: the repo
holds orphaned how-to fragments — `README.md`'s mismatch runbook,
`AGENTS.md`'s Procedures — living where they landed rather than where a
system would put them, which under PAR-0001's granularity rule is
exactly what "no named system" looks like.

Primary: `SESSION-2026-08-02-runbook-gap.md`, which is also where the
open design directions live.

## Decision

Three things are decided; everything else is deliberately open.

1. **The how-to layer exists as a named system**, and this record is its
   anchor. Its purpose: codify how agents and people improve, use, and
   otherwise leverage the benefit each governed system exists to provide
   — closing the diataxis loop.
2. **It is outside PAR.** A rationale explains why; execution guidance
   folded into rationales is the ballooning force arriving by another
   door. Tightening what `ARCHITECTURE.md` explicitly points to may be
   handy, but it does not meet this need and is not this system.
3. **The answer is nebulous, and this record says so** rather than
   settling it thin. Open, owed to a design session before this record
   can govern: the form (per-system runbooks or a tier of their own),
   the home, the naming, and above all the derivation-and-test
   discipline — "derived-and-tested" is the constraint that separates
   this from ordinary documentation, because a hand-maintained runbook
   describing a moving tree is the drift failure PAR-0002 exists to
   kill, and how much of a runbook can be derived or verified without
   the verifier itself becoming bureaucracy is the central question.

## Consequences

- The design work is present debt: the `Owed:` marker above (statement
  event e32966b), retired when the design session lands and this record
  is rewritten to govern the settled system. The status line says this
  record does not yet govern; the marker carries the design debt, which
  `Proposed` alone does not name.
- Until the design lands, nothing moves: the existing how-to fragments
  stay where they are as inventory for the design session, not as
  errors.
