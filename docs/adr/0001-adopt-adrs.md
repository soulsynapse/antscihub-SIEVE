# ADR-0001 — Adopt architecture decision records

Status: Accepted
Date: 2026-08-01

## Context

The founding architecture was argued in one recorded session (the design
session, archived) and synthesized into `ARCHITECTURE.md`. Decisions made
after that session lived in plan gate decisions and in conversation — the
reasoning compressed to a few sentences inside a frozen sequencing
document, or lost when the session ended. A 2026-08-01 audit reconstructed
the full decision chain from citations and found it intact but scattered
across four documents; the reconstruction cost is what this record class
removes. The repo is expected to grow past the size where rereading the
primary records per question is workable. This is the third rewrite; this
apparatus is part of the defense against a fourth.

Two further failure modes shape the rest of this record. A challenge that
succeeds produces a new decision and leaves a trail; a challenge that is
raised and *fails* produces nothing, so the reasoning that fended it off
dies with the session and the next doubter re-litigates from scratch. And
a decision recorded only in a frozen plan or a monolithic transcript gives
either kind of challenge nowhere to land, which makes absence from
`docs/adr/` ambiguous: it stops meaning "not an architecture decision" and
starts meaning "possibly founding — go read a transcript."

## Decision

Architecture decisions are recorded in `docs/adr/`, one file per decision,
named `NNNN-short-title.md`, with a status line (Proposed / Accepted /
Superseded by NNNN), a date, context, the decision, and consequences.

**Scope: architecture decisions only.** An ADR records a decision about
the architecture — the component decomposition, where a responsibility
lives, a mechanism the repo runs on (authority, debt, records), or why the
repo does something the way it does. Cycle-sequencing calls stay in their
plan's gates; tool-level design lives in the code and its cycle's records;
process rules live in `AGENTS.md`. Once the architecture is settled the
directory goes quiet: ADRs are written rarely and superseded more rarely.
A settled decision is not revisited; nothing prompts reopening one except
a genuine architectural conflict.

**Three ways a record changes, and only three.** An accepted ADR is
otherwise immutable.

1. **Revision** — the text is improved and nothing else in the repo
   changes: a clarification, tightened wording, an internal contradiction
   repaired, a consequence made explicit that was already implied. Edited
   in place, with a line appended to the `## Revisions` section. The
   test is mechanical and the commit proves it: a revision commit touches
   this file and nothing else. If the edit requires another file to
   change, it was never a revision.
2. **Challenge** — a doubt was raised against the decision and did not
   survive. The decision text is untouched; an entry is appended to the
   `## Challenges` section.
3. **Supersession** — anything that changes what gets built or how a
   decision is adjudicated. A new ADR, dated later, cites this one; this
   record's status line is updated and its text is left alone.

Both sections are append-only and their entries are immutable once
landed — every entry is true at its date forever, the same terminal
character that justifies location-as-status for the archive. Neither
stores a commit hash: `git log -- <file>` derives the diffs, and a line
cannot carry the hash of the commit that writes it.

Challenges entries obey four rules. **Only settled challenges the
decision survived** — a pending doubt is not recorded, and one that
succeeds is recorded by the superseding ADR and the status line, never
here. **Entry form:** date, the occasion, the doubt in a sentence or two,
why it held, and a pointer to the fuller record when one exists.
**Entries report; they never govern** — authority stays in the Decision
section, and if repelling a challenge required materially new reasoning
(the decision stands but its stated grounds were wrong or incomplete in a
way that changes consequences) that is a supersession carrying the same
decision with richer context, not an entry. **No roll-up:** a survived
challenge changes no current state, so an entry lands without touching
`ARCHITECTURE.md`. A revision likewise rolls up to nothing — by its own
test, there is nothing to roll up to.

**The walking path.** Three tiers, read downward only until convinced:

1. `docs/ARCHITECTURE.md` — the synthesis, always current, the one-stop
   shop. Read first; usually sufficient.
2. `docs/adr/` — the reasoning, per decision, dated. Read when the
   synthesis doesn't explain or doesn't convince.
3. `docs/archive/` — the primary records: session transcripts, briefs,
   exhausted plans, the reasoning verbatim. Frozen. Read when the ADR
   doesn't settle it.

**Authority runs down; readability rolls up.** `ARCHITECTURE.md` reports,
it never governs: on any conflict the deeper record wins, and the conflict
is a defect repaired at the synthesis — mismatch-runbook logic — never
adjudicated in the synthesis's favor. Among dated records the later
decision supersedes the earlier: a dated ADR supersedes the passage of any
record it cites, including the design session. The archive governs only
where no ADR speaks. Within the design session itself, later exchanges
supersede earlier ones, and its "Where things stand" list is the session's
own settlement.

**The roll-up discipline.** A change that accepts or supersedes an ADR
amends the tier-1 document that cites it in the same commit, the way the
regenerated ledger travels with the marker change it reflects. That is
`ARCHITECTURE.md` for the architecture itself, and `README.md` or
`AGENTS.md` for the mechanisms the repo runs on — the map and the working
instructions are tier 1 for those. This is what keeps tier 1 sufficient:
the synthesis may be momentarily wrong but never authoritatively wrong,
and when a decision is superseded everything rolls back up so that only
the tier-1 document needs to be read.

**Terminal records.** `docs/archive/` holds the primary records — session
transcripts, briefs, exhausted plans: a record moves there once, never
transitions again, and is never edited (mechanical link repairs at the
moment of moving excepted). A superseded ADR is terminal too, but it is
not a primary record — it is a distillation that died — so it retires to
`docs/adr/retired/` instead, and `docs/adr/` is kept to live decisions
only. It governs nothing once retired: a successor carries forward
everything of the old decision it keeps, which is what makes the roll-up
lossless, so "the archive governs only where no ADR speaks" never reaches
a retired ADR. What retirement preserves is the reasoning trail. Citable
names are bare filenames — "DESIGN-SESSION.md Exchange 5" — which survive
either move, and a retired name is never reused. Location-as-status was
previously rejected for records with live status (see Consequences); it is
sound in both places because frozen is terminal — there is no status left
to maintain.

**Every architecture decision gets an ADR, retrospectively too.** The
founding decisions — the ones `docs/ARCHITECTURE.md` cites by exchange
number — and the architecture decisions recorded in plan gates before this
tier existed are distilled into retrospective ADRs, numbered normally from
the next free number. There is no separate class, prefix, or numbering
range; uniformity is the point, because it is what lets absence from
`docs/adr/` mean something. Each distillation obeys four rules:

- **Provenance in Context.** It opens by naming the source record and
  passages (e.g. "DESIGN-SESSION.md, Exchanges 3 and 5", "archive/PLAN.md
  Phase 2 decision 4") and the decision's original date.
- **Governing on acceptance.** Per the standing rule above, a dated ADR
  supersedes the passages of the records it cites — so once accepted the
  distillation is the governing record for its decision, and the source
  remains the tier-3 primary holding the reasoning verbatim.
- **Fidelity at acceptance.** A distillation reports the decision as made;
  it does not revise it. Any daylight between the distillation and its
  source, or between it and an existing ADR, is named before acceptance —
  never silently resolved. Improving on a founding decision is a genuine
  new decision and takes its own ADR.
- **Roll-up per decision.** Each distillation amends the corresponding
  tier-1 citation — exchange number or plan gate to ADR number — in the
  same commit.

The work list is derived, not hand-maintained: it is exactly the set of
record citations pointing below tier 2 in `docs/ARCHITECTURE.md`,
`README.md`, and `AGENTS.md`. Sequencing calls that are genuinely a plan's
own — scope, order, build sequence, definition of done — are not
architecture decisions and stay in their plans.

## Consequences

- `DESIGN-SESSION.md`, `DESIGN-BRIEF.md`, and the exhausted `PLAN.md` move
  to `docs/archive/`. `PLAN-TOOL-CONTRACT.md` moves when it freezes, as
  does any future plan when exhausted. They stay frozen, citable by
  exchange or by gate, and are never edited; distillation reads them, it
  does not touch them.
- Resolves two `DEFERRED.md` entries, which move out: *within-record
  authority for the design session* (the rule is stated above, without
  ever amending the frozen record) and *how frozen planning documents
  remain discoverable* (its trigger — reassessing the layout when a second
  plan freezes — fired early, here; its two objections are answered above:
  citable names survive the move, and archive status is terminal, not
  maintained).
- A plan gate that makes an architecture-touching decision records it as
  an ADR and cites it; the plan keeps what is genuinely its own — scope,
  sequence, definition of done.
- `ARCHITECTURE.md` carries pointers to the records governing each
  component, so the walk down starts from wherever doubt arises.
- The gap between decided and distilled is present debt: filed in
  `DEBT.md`, retired one entry of work at a time as distillations land.
  Until a decision's ADR exists, its exchange or gate citation remains the
  governing pointer. Sequence and working rules: `docs/PLAN-DISTILL.md`.
- The debt and records machinery settled in archived `PLAN.md` — marker
  form rule v1, the classification rule, the layout settlement — is on
  that work list rather than waiting on an evolution trigger. It is the
  most-doubted mechanism in the repo and has been fended off three times
  with nothing recorded; distilled, it gains a challenge surface, and its
  anticipated additive v2 evolves against a live record.
- A doubt against a founding decision lands on a normal ADR and either
  falls (a Challenges entry) or succeeds (a supersession) — without
  either path touching the archive.
- Confirming evidence that arrives without a challenge is not recorded.
  It has no natural trigger and no terminal form; a curated scrapbook of
  vindications is exactly the hand-maintained state the anti-bureaucracy
  invariant forbids.

## Challenges

- **2026-08-01 — "The costs are real: accepted distillations govern, so a
  reinterpretation error legislates instead of misreporting;
  individuation is lossy even at perfect sentence fidelity; and the
  fidelity gate is a single acceptance review."** Raised in session the
  day retrospective distillation was accepted. Held: the ADRs are working
  memory — reread carefully and repeatedly until internalized — so review
  is continuous rather than a one-time gate; and the payoff is immediate
  even short-term, because only a governing tier-2 record carries a
  challenge surface, and undistilled decisions leave recurring doubts (the
  debt system, three times over) re-litigated and unrecorded. What
  survived of the challenge became working rules and sequencing in
  `docs/PLAN-DISTILL.md`: front-load while session memory is fresh, order
  by doubt traffic, quote decisive source sentences verbatim. Fuller
  record: none filed (2026-08-01 session).

## Revisions

- **2026-08-01 — A superseded ADR retires to `docs/adr/retired/` rather
  than `docs/archive/`.** The archive is defined as the primary records —
  transcripts, briefs, exhausted plans — and a dead distillation is not
  one of those; filing it there put a tier-2 record in tier 3, where the
  walk down lands in something that is itself walked down from. Made
  explicit alongside it, because the move would otherwise leave it
  ambiguous: a retired ADR governs nothing, which holds only because a
  successor carries forward everything of the old decision it keeps.
  Repaired at the same time: two sections could not both be "final."
