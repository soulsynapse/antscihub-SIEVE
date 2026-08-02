# Session record — 2026-08-02 — the record class

A frozen primary record (tier 3). It holds the argument that produced
ARCH-0001's rewrite from the ADR class to architecture rationale, and the
first record written under it. Never edited.

Form, per ARCH-0001: Kendrick's positions are verbatim; the surrounding
argument is compressed, including the positions that lost. Exchanges are
numbered so passages are citable — "SESSION-2026-08-02-record-class.md
Exchange 5". The session opened on the distillation plan (`PLAN-DISTILL.md`
Phase 2) and never reached it; what it reached instead was the apparatus
that plan runs on.

State at the start: `docs/adr/` held one record, ADR-0001, adopting
architecture decision records on the Nygard model — immutable once
accepted, three change classes and only three, superseded rather than
edited. Nothing had ever been superseded or retired.

---

## Exchange 1 — Retirement location

> "one improvement to adr0001, retired adrs go into a different folder
> please. just keeps it easy to browse the standing records without having
> to dig through adrs that are no longer active"

Answered that ADR-0001 already moved superseded records out of `docs/adr/`,
so the stated motivation was met — but that a different defect justified
the same change: `docs/archive/` was defined as *primary records*
(transcripts, briefs, exhausted plans), and a dead ADR is a tier-2
distillation, so filing it there put a tier-2 record in tier 3 where the
walk-down lands in something itself walked down from.

Two homes considered. `docs/archive/adr/` preserves one rule — terminal
records live in the archive — which plans also obey. `docs/adr/retired/`
keeps the archive meaning strictly *primary*. Kendrick took the second:

> "yeah, i agree on the 2nd. you don't have to add the adr/retired this
> session since there's nothing to retire so yes it gets a revision
> section"

One sentence had to be added either way, because "the archive governs only
where no ADR speaks" would otherwise hand a retired record governing power
on any point its successor dropped. Settled: a superseded record governs
nothing. Landed as commit `629d7bc`, then superseded wholesale by
Exchange 9.

## Exchange 2 — Cross-citation

> "we can also update the adr-0001 for a potential cross-citing mechanism.
> any ideas?"

Proposed: **back-cites are derived, never stored.** A forward citation is
authored; the reverse link is grepped. The argument is not convenience but
the anti-bureaucracy invariant — a stored back-link is hand-maintained
state already present in the tree — and ADR-0001 had already done this
once in the same shape ("Neither stores a commit hash: `git log -- <file>`
derives the diffs"). Requires a canonical citation token, which the corpus
already used universally.

Rejected: an append-only `## Cited by` section (hand-maintained derivable
state, and a fourth change class where ADR-0001 permitted three).

Then a long adjudication of which change class the edit fell into,
concluding it was a new ADR rather than a supersession because ADR-0001
was silent on cross-citation. That adjudication is what Exchange 3
attacked. It produced nothing and is recorded here only because its
failure is the finding.

## Exchange 3 — The apparatus outgrowing the content

> "Genuinely if the system for the ADRs undermines the ability for the ADRs
> to be clear then there's a problem with the ADR system itself"

Conceded, with the evidence: two turns spent on the rules of the record
system, zero architecture decisions distilled; `docs/adr/` holding one
file governed by ~200 lines of constitution; nothing ever superseded or
retired. The repo already names this shape — the anti-bureaucracy
invariant, and "ceremony ahead of need" in `archive/PLAN.md`.

Split named at the time: part was mishandling (a one-paragraph mechanism
followed by three paragraphs of unasked-for constitutional adjudication),
part was genuine over-specification — rules written against imagined cases
failing at the rate such rules fail.

Two claims from this exchange were later withdrawn. The suggestion to
"drop the closure" (permit a fourth change class) died in Exchange 4 when
supersession turned out to be cheap. The claim that supersession
granularity equalling record granularity was a *defect* was withdrawn as
wrong — it is true of every versioned-document system.

## Exchange 4 — Granularity, and what supersession costs

> "A plan is not an ADR. The ADR plan didn't codify anything, and the cross
> citing wasn't an accepted ADR, as you said. I don't think ADRs should be
> particularly granular either. I don't mind if an ADR that needs to be
> refined is retired, it costs nothing. And if the refinement wasn't to
> enable a change, the refinement is free per ADR-0001 to begin with"

The decisive move is "it costs nothing." The case for fine granularity
rested entirely on wholesale supersession being expensive; it is a copy,
an edit, a redate, a move. Two consequences followed immediately:

1. Coarse beats fine, because a wholesale rewrite yields a record that
   **reads whole**, where fine records with cross-cites make the reader
   assemble the decision from fragments.
2. The proposal standing at the time — three records for the debt
   machinery (doctrine / form / enforcement, individuated by what could be
   superseded independently) — was wrong and collapsed to one.

Also correct and conceded: ADR-0001's mechanical revision test said
"another file," not "another record," which is why a *plan* amendment had
been read as disqualifying a revision. Noted as over-broad.

One caveat kept: the cost of a wholesale rewrite is silent drift in the
parts meant to carry forward, so a substantial rewrite is reviewed as a
diff.

## Exchange 5 — What these records are for

> "ADRs need to read as whole. That's pretty important. They serve as (more
> or less) the long-form reasoning that rolls up to the short form that
> exists in ARCHITECTURE.md."

The drafting consequence: this cuts against `PLAN-DISTILL.md` working rule
1 ("quote, don't paraphrase, at the load-bearing points") if that rule is
applied hard — a quilt of verbatim quotations is fragment-assembly by
another route. Resolved: the quotes carry the decisions, the prose carries
the argument, and the argument must stand if only the prose is read.

ARCH-0002 was drafted against this constraint (Exchange 10).

## Exchange 6 — Not ADRs at all

> "It's not finding something wrong with it, it's living the reasoning you
> just suggested. Maybe we shouldn't even call it ADR? I feel like just
> Reasoning-0001 or something is accurate, and calling it ADR will be
> pattern matched to all the baggage ADR carries with it until the actual
> file is read and acknowledged as 'literally not ADR except in name'"

> "so maybe R-0001 actually, with R standing for reasoning"

Two findings here, and the first is the correction. Framing the day's
edits as four *defects found in ADR-0001* was itself the immutability lens
leaking back in — under a living-record model, refining a record is the
normal operation, not a defect report.

The second is the structural argument that settled the whole question.
Nygard's immutability is **archaeological**: a future reader needs to know
what was believed at the time, and editing retrofits present knowledge
into a past decision. But an ADR is the bottom of its own stack — nothing
underneath carries the historical record. Here `docs/archive/` does. The
archaeological function is already discharged one tier down, so importing
immutability buys a guarantee the repo already has, at the price of an
apparatus around every edit.

Therefore: keep the ADR form (one decision per file, status, context /
decision / consequences), drop the doctrine. What is lost is diff
legibility — a wording tweak and a reversal are no longer distinguishable
by status line — judged small, with one author.

Precedent noted: the repo already argues this way about names. `Owed` was
named as it was "because a marker is not a fault and should not
pattern-match visually to real exceptions."

## Exchange 7 — Naming

> "Give me some good recommendations for alternative names then that
> capture the architecture stuff too. Unfortunately architecture decision
> reasons won't work.. for obvious reasons lol"

Constraint identified: a three-letter, A-initial acronym ending in R is the
ADR silhouette and gets misread before it gets read.

Four offered. `ARCH-0001` — "Architecture Reasoning", scope carried in the
token, four letters, no trailing R. `AR-0001` — "Architecture Rationale",
technically the most correct name, since *rationale* is the term of art in
the design rationale literature (QOC; MacLean and colleagues) for exactly
this distinction, but two letters and A-initial. `R-0001` with scope
carried by the directory. `GROUNDS-0001` — no baggage at all, in the repo's
habit of plain precise words, but loses architecture entirely.

Recommended `ARCH-`; flagged that `docs/architecture/` beside
`docs/ARCHITECTURE.md` differs only by extension and would confuse
listings, so `docs/arch/`.

> "I think ARCH-0001 with Rationale works nicely. Lets do that."

Token and word taken from different candidates: `ARCH-NNNN`, "architecture
rationale."

## Exchange 8 — The granularity heuristic

> "Just as a general heuristic, the ARs are the smallest chunk that carries
> all the relevant things with it. They're almost wikipedia pages -
> summaries, they can be wrong, so they cite the source."

Replaced the weaker "granularity: coarse" wording. The heuristic is
two-sided where "coarse" was one-sided: a record needing a sibling read
alongside it is one record cut in two; a record that swallowed a
neighbouring decision it did not need is two fused. The test is whether a
reader finishes the file convinced without opening another.

The Wikipedia framing generalized past its occasion: every tier is a
fallible summary of the tier below that cites it for exactly that reason.
That is the authority rule the repo already had — deeper record wins, the
summary is repaired — restated once instead of separately per tier.

## Exchange 9 — Convergence

> "Then the ARCHITECTURE.md is basically the same way. Did the rationale
> that once a rationale is pretty bulletproof it will stop being edited get
> carried into the 0001?"

It had not. ARCH-0001 said the *directory* goes quiet — records written
rarely, retired more rarely — which is a write rate, not a claim about
edits to an existing record converging. Without it, "edited whenever a
reread finds it wanting" reads as a standing licence.

Added: editing asymptotes, and that is the point rather than a hope. The
edit rate is a *measurement* of how settled the reasoning is. A record
still being reworked is one not yet internalized; a record gone quiet
while collecting Challenges entries is bulletproof — and nothing declares
it so, because `git log -- <file>` already says it, which is the only
place such a claim can live without becoming a maturity field somebody
maintains.

Landed with the rename as commit `fcfbf6f`.

## Exchange 10 — ARCH-0002, the first record under the new class

Drafted from `archive/PLAN.md` — the anti-bureaucracy invariant, the
placeholder doctrine, the classification rule, the three-file taxonomy,
marker form rule v1 with its narrowings, the two instruments, enforcement,
the closed machinery class. One record, per Exchange 4. Commit `a6de72f`,
**Proposed**, so `archive/PLAN.md` still governs and no tier-1 citation
has moved.

Twenty-six quoted passages machine-verified verbatim against the source.
Four places where the record supplies reasoning the source left implicit
were named rather than resolved silently, per the fidelity rule: why a
placeholder never invents a signature; why the mismatch test must not
self-heal; the generalization that every leniency in an enumerator is a
way for debt to vanish; and the connection of the closed machinery class
to the invariant's "exemption to adjudicate."

Two deliberate omissions: no Challenges section (pending reconstructed
doubts), and the layout settlement excluded as component decomposition
rather than debt machinery — moved to `PLAN-DISTILL.md` Phase 5.

## Exchange 11 — This record's own convention

> "we need to adopt the convention that when architecture reasoning is
> written then you need to make the archive file and point to it. you can
> extract my quotes if you want, I don't think the verbatim is
> particularly useful when it is back and forth like this. but I could be
> wrong and I think that you would do a better job of deciding how to take
> this transcript down so that re-examination and reinterpretation
> survive"

The gap is load-bearing rather than procedural: Exchange 6's argument for
living records is that the archaeological function is discharged one tier
down, so a rationale with no primary underneath it is a rationale the
argument does not cover. ARCH-0001 was in that state at the moment it was
rewritten.

Form decided as delegated. Not a transcript (an agentic session is mostly
tool calls and drafting) and not a summary (a summary bakes in one
interpretation and discards the material a different reading would need).
Instead: **quote the person, compress the argument, keep what lost.** The
human positions are short and did the steering, so they are verbatim; the
machine's prose was revised in flight and its conclusions are now in the
rationale, so it is compressed; and the positions that lost are kept,
because a record showing only the winner cannot be re-examined.

## Exchange 12 — Curated record versus raw transcript

> "because if you consider how many times the design documents had to be
> revisited in order to really harden the architecture as is, it might be
> worthwhile. but I'm not sure."

The counter-consideration, offered at the time: `DESIGN-SESSION.md` is
itself curated — nine exchanges, not a transcript — and it is what
supported all those revisits. So the revisit history is evidence that the
curated form worked, unless those revisits involved reconstruction pain a
raw record would have spared, which only Kendrick can say.

What settled the practical question was checking rather than asserting.
Claude Code already writes a raw JSONL transcript per session to
`~/.claude/projects/<slug>/`, so no capture work exists. Two findings
followed. First, the three 2026-08-01 sessions that produced the record
class survive — `d289f467`, `14545adb`, `78389c66` — so the claim made
earlier in this same record, that the record class's own origin was
unreconstructable, was wrong and is corrected below. Second,
`cleanupPeriodDays` is unset, so default retention applies and every one
of them expires on a timer measured in weeks. "It exists on disk" is not
durability.

That asymmetry is the argument: retention costs about a megabyte per
session of a file nobody reads, and loss is irreversible and already
scheduled. Against it, a raw transcript holds everything said, unedited,
permanently, in a repo that may later be shared.

Proposed: retain them outside the tier structure, not citable and not
governing, as fidelity evidence for the curated record beside them.

Ruled against:

> "yeah we don't want to have the wholesale transcripts lol"

So the curated record is the only primary — and the reason holds
independently of repo hygiene or the sharing concern. A transcript is not
a cheaper primary but a worse one: unreadable at length, and usable only
by reconstructing the argument out of it, which is exactly the cost this
tier exists to remove. What guarantees the curated record's fidelity is
that it is written while the session is live and the reasoning is still
in hand, not a raw copy behind it, which would only move the
reconstruction later. The design-session precedent points the same way —
nine curated exchanges carried every revisit.

One contradiction surfaced here and was repaired rather than fudged: this
record was committed mid-session while ARCH-0001 called archived records
frozen and never edited. Settled — a session record is live for the
duration of its session and freezes at close, the way a plan freezes when
exhausted.

---

## Where things stand

- The record class is architecture rationale, `docs/arch/`, cited
  `ARCH-NNNN`. Living documents, not ADRs. ARCH-0001 governs.
- Granularity is the smallest chunk that carries everything relevant with
  it. Records read whole. Rewriting wholesale is cheap and normal.
- Every tier is a fallible summary of the tier below and cites it; on
  conflict the deeper record wins and the summary is repaired.
- Editing asymptotes; the edit rate measures how settled the reasoning is.
- A rationale written from a session files its session record here and
  cites it; a distillation does not, already having its primary. The
  record is live for its session and freezes at close. Raw transcripts
  are never retained. Operationalized in `AGENTS.md` ("Where records go",
  and the never-do list).
- ARCH-0002 sits **Proposed**. `archive/PLAN.md` still governs the debt
  machinery. Accepting it moves `README.md` lines 41 and 98 and
  `AGENTS.md` line 18, and retires three citations from the `DEBT.md`
  distillation entry.
- Open, carried out of this session: the three reconstructed doubts
  against the debt system and whether they belong in Challenges or
  Context (`PLAN-DISTILL.md` Phase 2 gate); the four fidelity flags in
  ARCH-0002; the layout settlement's new home in Phase 5.
- The 2026-08-01 sessions that adopted the record class have no curated
  primary, and their raw transcripts will expire on the default retention
  timer unread. That reasoning survives only as ARCH-0001's own text and
  git history. Accepted, not filed as debt: the convention exists so it
  does not recur, and curating them now would be reconstruction from
  transcript — the thing this tier removes.
