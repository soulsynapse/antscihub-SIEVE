# Session record — 2026-08-02 — PAR scope: one record, one named system

Curated primary for the individuation rule now in PAR-0001's
Granularity. Follows `SESSION-2026-08-02-par-rename.md` in the same
working day; separate decision, separate record. Doctrine: PAR-0001.
Written live, frozen at session close.

## Exchange 1 — the question: what stops a PAR ballooning?

Kendrick, verbatim:

> "This is consistent with what any architectural decision's lifehistory
> should look like too: ironing out problems, refining, ideally before
> it is loadbearing and requires repo changes, probably pretty active
> logging of evidence and resolutions, and eventually all the basic
> problems within the scope of the architectural decision are answered
> or an accepted tradeoff. One thing, for the challenge section: the
> scope of any one PAR is basically wide open, and theres argumentation
> in the other literature such as ADR that it should be short. That's a
> real tradeoff, but the tradeoff itself is directly mitigated the more
> hardened the PAR entry is. A good PAR is scoped so that the
> load-bearing it has to do serves a scoped purpose or it will continue
> to balloon forever, taking on more and more responsibility. I think
> this does shift how PAR needs to be argued to be useful, and it is an
> open question that deserves an answer that isn't weakly argued or
> arbitrary. Given the goals of PAR, what are some clean ways to
> separate them? I have a few ideas but I'd like to hear your thinking"

The agent's candidates, compressed: (1) **one worth-it question per
record** — derived from the tradeoff-log function, since a ledger can
only be audited over one account; (2) **the Parnas cut** — records as
modules of reasoning, decomposed by what can be revised independently,
tested by simulating reversal and watching for forced rewrites in other
records; (3) **doubt-addressing** — every plausible doubt lands on
exactly one record, with boundaries refactorable from observed challenge
traffic. Synthesis offered: the three are one idea from three sides —
why the unit coheres, when it revises, how it is attacked — and a scope
is clean when all three agree.

Offered alongside and **not adopted** (unaddressed in the ruling below;
kept as open positions, not doctrine): a fold-versus-new-record
adjudicator via the worth-it test; boundary review as a formal part of
hardening; the observation that the tests, applied unflinchingly, would
indict PAR-0001's own bundling of session-record form, status lifecycle,
and walking path; and the argument that no length norm should exist
because ADR brevity is downstream of immutability, with the reread loop
already enforcing the real constraint.

## Exchange 2 — the ruling: named systems, independently converged

Kendrick, verbatim:

> "So here's what I think. One PAR is one named system, as defined by
> the near-decomposability. What it touches and what needs to know about
> it. An architectural decision eventually makes it's way into
> ARCHITECTURE.md, but it stops there. The logs of chats that are
> talking about architecture need to be represented in it if decisions
> happen or challenges are made, but that's clear. The goal of the PAR
> system, as stated, is to provide clarity to the repo in sensible
> chunks. Theres clear delineation of when the PAR system kicks in,
> which is directly operationalizable by both the author working in the
> repo as well as the agent via protocol hints. That matches exactly
> what PAR exists for. And hey, there's another cute tie in, Parnas..
> maybe even too cute. PAR-NAS, with NAS as 'not-a-system' lol. You
> literally said it as 'decomposed by what can be revised
> independently'. But yeah, I was writing this as you responded and we
> arrived at the same conclusion: why the unit coheres, and basically
> the machinery to falsify the hypothesis, including evidence
> accumulation. I like it. Don't write in your proposals from your last
> message as accepted except for the ones I addressed, but we genuinely
> independently landed in the same space. Solid."

Adopted, folded into PAR-0001's Granularity: one PAR is one named
system, bounded by near-decomposability (Simon) — what it touches and
what needs to know about it — which makes the apparatus's trigger
operational for author and agent alike and gives the scoped purpose that
stops ballooning; the Parnas reversal test and challenge-traffic
clustering as the falsification machinery; and the coherence rationale,
that the boundary is what keeps each tradeoff log assessable. Roll-up:
`README.md`'s tier-2 line becomes "one named system per file."

The convergence was independent — the named-system formulation was being
written while the agent's message arrived. Worth the breadcrumb: two
derivations from the system's stated goals landing on Simon's
near-decomposability and Parnas's criterion is evidence the boundary
rule is over-determined rather than arbitrary, which is what "an answer
that isn't weakly argued or arbitrary" asked for. The PAR-NAS pun was
floated and flagged by its own author as maybe too cute; it names
nothing and governs nothing.
