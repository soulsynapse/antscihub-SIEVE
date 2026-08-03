# PAR-0001 — Project architecture rationale records

Status: Accepted
Date: 2026-08-02

## Outcomes

What this record system looks like working as intended: every
architecture decision is governed from `docs/par/`, with the three
tier-1 documents citing nothing deeper. A doubt — recurring or fresh —
has exactly one place to land and finds the reasoning that answered it
last time. Rereading a rationale convinces without opening a sibling.
And the apparatus stays quiet: records written rarely, retired more
rarely, the directory's silence meaning the architecture is settled
rather than the record class abandoned.

## Context

The founding architecture was argued in one recorded session (the design
session, archived) and synthesized into `ARCHITECTURE.md`. Decisions made
after that session lived in plan gate decisions and in conversation — the
reasoning compressed to a few sentences inside a frozen sequencing
document, or lost when the session ended. A 2026-08-01 audit reconstructed
the full decision chain from citations and found it intact but scattered
across four documents; the reconstruction cost is what this record class
removes. This is the third rewrite; this apparatus is part of the defense
against a fourth.

Two failure modes shape the rest. A challenge that succeeds produces a new
decision and leaves a trail; a challenge that is raised and *fails*
produces nothing, so the reasoning that fended it off dies with the session
and the next doubter re-litigates from scratch. And a decision recorded
only in a frozen plan or a monolithic transcript gives either kind of
challenge nowhere to land, which makes absence from `docs/par/`
ambiguous: it stops meaning "not an architecture decision" and starts
meaning "possibly founding — go read a transcript."

**These are not ADRs, and the name is deliberate.** This class was
originally adopted as architecture decision records (2026-08-01), and the
convention's central rule came with it: an accepted record is immutable,
superseded rather than edited. That rule exists for a reason that does not
hold here. Nygard's immutability is archaeological — a future reader needs
to know what was believed *at the time*, which constraints were live and
what was unknown, and editing retrofits present knowledge into a past
decision and destroys exactly that. But an ADR is the bottom of its own
stack; nothing underneath it carries the historical record. Here something
does. `docs/archive/` holds the design session verbatim and frozen
forever, so the archaeological function is discharged one tier down, and
importing immutability into this tier buys a guarantee the repo already
has at the price of an apparatus around every edit.

What these records actually are is long-form reasoning, reread repeatedly
as working memory until the architecture is internalized, rolling up to
the short form in `ARCHITECTURE.md`. That reader is served by the clearest
current statement of the reasoning, not the historically faithful one.
Keeping the ADR name would have every reader import immutability, brevity,
and one-page skimmability before opening a file that honors none of them.

Primary record for this rewrite: `SESSION-2026-08-02-record-class.md`,
which holds the argument above in full, including the positions that
lost. The original 2026-08-01 adoption predates the rule below requiring
one and has no curated primary; its raw session transcripts survive but
were never filed.

## Decision

**Form and name.** A project architecture rationale (PAR) lives in
`docs/par/`, one file per decision, named `NNNN-short-title.md`, cited as
`PAR-NNNN`. It carries a status line, a date, outcomes, context, the
decision, and consequences. Every record-to-record citation names its
target as `PAR-NNNN` at least once, in that form; paths and links are
optional alongside it.

**Outcomes.** A record opens with what its system looks like working as
intended — an `## Outcomes` section directly after the status and date,
before Context, the first thing a reader meets (2026-08-02; primary:
`SESSION-2026-08-02-record-outcomes.md`). Outcomes are the yardstick
later proposals against the system are judged by, and they are what
dies first when it lives only in conversation — the occasion for this
rule was the debt system's two stated end states being dropped
mid-sitting by the agent that had just argued them. They differ from
Consequences by direction: Consequences report what follows from the
decision as made; outcomes state the end state it steers toward,
readable without the argument. Phrased as intention, not current fact,
and edited like everything else in a living record. Existing records
gain theirs at their next substantive edit, never in a retro-stamping
sweep.

The name does double duty, and the pun is the mnemonic. PAR is how the
ability to work in this project is kept *up to par* — the defense against
the degradation agentic workflows otherwise impose, which is the failure
mode the Context above describes. And the PAR system exists to keep the
project agile and documented — PAD — under the heuristic of minimal
PADding, which is the anti-bureaucracy invariant (PAR-0002) wearing its
nickname. The class was cited as `ARCH-NNNN` until 2026-08-02, when it was
renamed (primary: `SESSION-2026-08-02-par-rename.md`); frozen records
still use that form, and the numbers are unchanged, so an archival
`ARCH-NNNN` citation resolves as `PAR-NNNN`. The name is intended
terminal: every rename taxes the frozen tier with another citation
mapping, so a successor would have to beat PAR by more than that costs.

**Scope: architecture only.** A rationale records a decision about the
architecture — the component decomposition, where a responsibility lives,
a mechanism the repo runs on (authority, debt, records), or why the repo
does something the way it does. Cycle-sequencing calls stay in their
plan's gates; tool-level design lives in the code and its cycle's records;
process rules live in `AGENTS.md`. The name carries this rule less than
"architecture decision record" did, so it is stated here and held by
judgment: general reasoning does not belong in `docs/par/`, because
absence from the directory is only meaningful if presence is disciplined.
Once the architecture is settled the directory goes quiet — records are
written rarely and retired more rarely. The system also serves SIEVE
alone: a record written with one eye on reuse beyond this repo is
carrying generality nobody here needs, which is PADding of the purest
kind.

**Records are living.** A rationale is edited in place whenever a reread
finds it unclear, incomplete, or wrong, and that is the normal operation
rather than evidence of a defect. There is no change taxonomy, no revision
log, and no ceremony around an edit: git holds the history, and a
hand-maintained log of changes would be derivable state maintained by hand
— the anti-bureaucracy invariant tripping on itself. A decision that
genuinely reverses is rewritten to say what is now true, with the date
updated. An edit that changes what the record says owes the roll-up,
below; one that changes what the record *decides* also carries its
argument — a decision never moves for free: the session that argued
the change files its primary and the rewrite cites it, the same rule a
fresh rationale obeys (2026-08-02,
`SESSION-2026-08-02-hardening-dissolved.md`). Reread clarity owes
nothing.

Editing is expected to asymptote, and that is the point rather than a
hope. A rationale that has survived enough rereads and enough doubts
stops changing; the edit rate is therefore a measurement of how settled
the reasoning is, not a standing licence. A record still being reworked
is one not yet internalized. A record that has gone quiet while
collecting Challenges entries is bulletproof — and nothing declares it
so, because `git log -- <file>` already says it, which is the only place
such a claim can live without becoming a maturity field somebody
maintains.

**Status.** *Proposed* or *Accepted*, and *Retired* for a record no longer
part of the architecture. A proposed record does not govern: until it is
accepted, whatever governed before it still does, and `ARCHITECTURE.md`
keeps citing that. This is what makes a proposed record free — it can
sit, and nothing in the repo is inconsistent while it does. *Proposed*
means not yet ready to govern: drafted and unchecked, or naming a system
not yet designed (PAR-0003). *Accepted* means the record governs — the
moment the roll-up is owed — and it is the ordinary living state:
effectively implemented, open to argued improvement, which is every
accepted record, because they are living documents.

Acceptance is a judgment that the record is ready to govern. For a
distillation that judgment is the fidelity review against its source;
for a rationale argued fresh it is the author's call. A deliberate
attack session — arriving holding the answer and trying to break the
draft — is one route to it, convened at judgment when a record must
govern before organic challenge could accumulate, and it is never
owed: nothing carries a hardening debt, no trigger makes one due, and
a record's bulletproofness is otherwise earned the organic way, entry
by entry in its tradeoff log (2026-08-02; primary:
`SESSION-2026-08-02-hardening-dissolved.md`, which also records the
accepted exposure — a judgment can be late where a trigger would have
fired).

**Granularity: one PAR is one named system.** The boundary is drawn by
near-decomposability, in Simon's sense: dense interactions inside the
unit, sparse across it — what the system touches and what needs to know
about it (2026-08-02; primary: `SESSION-2026-08-02-par-scope.md`). This
is what makes the apparatus's trigger operational for the author and an
agent alike: a decision gets a record when it settles the shape of a
named system, and the scoped purpose is what stops a record ballooning —
load it was never scoped to bear goes to the record, or the new record,
whose system it belongs to. Within that boundary the unit is still the
smallest *self-sufficient* chunk rather than the smallest one: a
rationale has to read whole, because the reader is assembling an
understanding and a decision split across three cross-citing files makes
them do the assembly; but a record that has swallowed a neighbouring
system it does not need is harder to reread and harder to rewrite. The
reader-side test is unchanged — a reader finishes the file convinced
without opening another.

A boundary is a hypothesis, and it is falsifiable from the tree. The
revision test is Parnas's criterion applied to reasoning — records are
modules of it, decomposed by what can be revised independently: simulate
the decision reversing, and if rewriting this record forces
substantially rewriting another, the boundary leaked — merge, or make
the dependency a citation, which is the interface between records. The
evidence accumulates in the Challenges sections: doubts that repeatedly
straddle two records are one system cut in half; entries clustering into
separable concerns inside one record are two systems sharing a file. A
boundary drawn wrong is repaired by re-individuating the living records,
losslessly, numbers never reused. The same boundary is what keeps each
tradeoff log assessable: the accumulated cons in a record all weigh
against the worth of one system.

Sub-systems split cleanly, and the split is a clarity gain rather than
proliferation (2026-08-02). A large record earns its size only while it
cannot be understood without each of its parts; once one part's
reasoning touches nothing else, splitting it out is the gain. A system
in service to a larger one may hold its own record — templates in
service to the runbook layer (PAR-0004, PAR-0003) — provided every
pointer stays unambiguous: exactly one place the sub-system lives,
exactly one way to cite it, so subset status costs nothing.

The nearest familiar shape is a Wikipedia article: a summary that stands
on its own, can be wrong, and cites its sources for exactly that reason.
When a rationale and the record it distils disagree, the deeper record
wins and the rationale is repaired — the same relation the synthesis has
to the rationale, one tier up.

When part of a record changes, the whole record is rewritten to stay
coherent, which is cheap and is also an occasion to reread it. The one
cost is silent drift in the parts meant to carry forward, so a
substantial rewrite is reviewed as a diff.

**Challenges.** A record carries a final `## Challenges` section: the
decision's tradeoff log — literally pros and cons. Every architectural
decision has tradeoffs, and a decision needs a way of pointing at what
they are without having to change in response to them; this section is
that pointer. An entry is a doubt or a friction deliberately stated
against the decision, together with its resolution or the lack of one:
the date, the occasion, the doubt or the cost in a sentence or two, and
either why the decision held or that the doubt stands — real,
unresolved, and not rising to change. Each entry is assessed as breaking
or not breaking; a doubt that *breaks* is not an entry, because it
changes the decision and the record is rewritten. Entries report; they
never govern. This is the section that repays the apparatus: a doubt
that recurs — and they do recur, the same objection arriving three times
over a year — is re-litigated from scratch every time it lands nowhere,
and the reasoning that answered it the first time is gone.

Friction is stated, never inferred. An agent may point friction out, but
a human confirms it before it lands — every entry in these sections has
arrived that way. The log is breadcrumbs for the human more than the
agent: an agent follows the architecture by default, precisely because
it is architecture, so the tipping point where accumulated entries mean
a rationale *needs* improving is a human read of this section, never a
computable threshold. Bare friction — un-argued evidence that something
rubbed — is not an entry either: it lands with the reason it is
friction, a doubt that exists but is not changing the decision, or it is
dismissed and enters as the record withstanding it.

Confirming evidence arriving without a challenge is still not recorded:
a pro enters only paired with the con it answers. Free-floating
vindication has no natural trigger and no terminal form; a curated
scrapbook of it is exactly the hand-maintained state the
anti-bureaucracy invariant forbids. This section creeps toward a log,
and that is its design; it must never creep toward a scrapbook.

**The walking path.** Three tiers, read downward only until convinced:

1. `docs/ARCHITECTURE.md` — the synthesis, always current, the one-stop
   shop. Read first; usually sufficient.
2. `docs/par/` — the reasoning, per decision, dated. Read when the
   synthesis doesn't explain or doesn't convince.
3. `docs/archive/` — the primary records: session transcripts, briefs,
   exhausted plans, the reasoning verbatim. Frozen. Read when the
   rationale doesn't settle it.

**Authority runs down; readability rolls up.** `ARCHITECTURE.md` reports,
it never governs: on any conflict the deeper record wins, and the conflict
is a defect repaired at the synthesis — mismatch-runbook logic — never
adjudicated in the synthesis's favor. Among dated records the later
decision supersedes the earlier: an accepted rationale supersedes the
passage of any record it cites, including the design session. The archive
governs only where no rationale speaks, and never reaches a retired one.
Within the design session itself, later exchanges supersede earlier ones,
and its "Where things stand" list is the session's own settlement.

**The roll-up discipline.** Accepting a rationale, or editing one in a way
that changes what it says, amends the tier-1 document that cites it in the
same commit — the way the regenerated ledger travels with the marker
change it reflects. That is `ARCHITECTURE.md` for the architecture itself,
and `README.md` or `AGENTS.md` for the mechanisms the repo runs on. This
is what keeps tier 1 sufficient: the synthesis may be momentarily wrong
but never authoritatively wrong.

**Cross-citation is derived.** A record cites the records it was decided
against; the reverse link is never stored, because it is already in the
tree. `grep -rl "PAR-0002" docs/ README.md AGENTS.md` is the list of
records leaning on PAR-0002, and it is where a substantial rewrite of
PAR-0002 starts. A stored back-link would be hand-maintained derivable
state.

**Retirement.** A rationale no longer part of the architecture moves to
`docs/par/retired/` and stops governing entirely; whatever replaces it
carries forward everything of the old decision it keeps, which is what
makes retirement lossless. It keeps its number, which is never reused, so
citations still resolve. `docs/archive/` is not its home: the archive is
the primary records — transcripts, briefs, exhausted plans — and a retired
rationale is none of those.

**Every architecture decision gets a record, retrospectively too.** The
founding decisions — the ones `docs/ARCHITECTURE.md` cites by exchange
number — and the architecture decisions recorded in plan gates before this
tier existed are distilled into retrospective rationales, numbered
normally from the next free number. There is no separate class, prefix, or
numbering range; uniformity is what lets absence from `docs/par/` mean
something. Each distillation obeys three rules:

- **Provenance in Context.** It opens by naming the source record and
  passages (e.g. "DESIGN-SESSION.md, Exchanges 3 and 5", "archive/PLAN.md
  Phase 2 decision 4") and the decision's original date.
- **Fidelity at acceptance.** A distillation reports the decision as made;
  it does not revise it. Any daylight between the distillation and its
  source, or between it and an existing rationale, is named before
  acceptance — never silently resolved. Improving on a founding decision
  is a genuine new decision and takes its own record.
- **Roll-up per decision.** Each distillation amends the corresponding
  tier-1 citation — exchange number or plan gate to `PAR-NNNN` — in
  the same commit as its acceptance, the moment it starts governing; a
  draft sitting `Proposed` amends nothing.

**A rationale argued out in a session files its primary.** A distillation
already has one — it is reading it. A rationale reasoned out live does
not, and writing one without filing the session record leaves that
decision with nothing underneath it. This is not a courtesy: the case for
living records above is that the archaeological function is discharged
one tier down, so a rationale with no primary is a rationale that argument
does not cover. The session record is written into `docs/archive/` as
`SESSION-<date>-<slug>.md`, in the same commit as the rationale it
produced, and cited from that rationale's Context.

Its form follows from what it has to survive — re-examination by a reader
who may reach a different conclusion than the rationale did. So it is
neither a transcript nor a summary: a transcript of a working session is
mostly tool calls and drafting, and a summary bakes in one reading and
discards the material a different one would need. **Quote the person,
compress the argument, keep what lost.** Human positions appear verbatim,
because they are short and they do the steering; the surrounding argument
is compressed; and the positions that were rejected are kept with their
reasons, because a record showing only the winner cannot be re-examined at
all. Numbered exchanges make passages citable, as in the design session.

Its unit is the argument, not the sitting (2026-08-02). One working
session that settles two separable arguments files two primaries, and a
record freezes when its argument closes even if the conversation
continues — `SESSION-2026-08-02-par-rename.md` froze while the same
conversation went on to produce `SESSION-2026-08-02-par-scope.md`. This
is the granularity rule reaching tier 3: a frozen primary is loaded to
re-examine one decision, so the file should be that argument and nothing
else. A monolithic session log charges every future re-examination the
context cost of the whole session; per-argument primaries keep the
frozen log clean and addressable in decision-sized pieces. Decisions
argued inseparably share one primary — near-decomposability again.

A session record is live for the duration of its argument — written as
the argument lands and appended to as it continues — and freezes when
the argument closes, the way a plan freezes when exhausted. After that
it is never edited.

Freezing is deliberate, and the record announces its own state
(2026-08-02). A session record opens with `Status: Open` and stays
editable at will for as long as the argument runs — the temptation is
to freeze as soon as a decision lands, but the back-and-forth dictates
closure, not the first decision. Closing is a wrap: a deliberate pass
confirming the logic all landed, which flips the line to
`Status: Frozen` and starts the never-edited rule. The marker is the
debt entry, placeholder doctrine again: `grep -l "^Status: Open"
docs/archive/SESSION-*.md` derives the arguments never wrapped, each
announcing that its logic may not have landed. The derivation cannot
tell an argument deliberately spanning sittings from an abandoned one —
an old date on an Open record is the alarm, a young one is a session in
progress, and the read is the human's. Records predating the convention
carry no status line and were all deliberately closed; they are
grandfathered rather than retro-edited, because frozen records are
never edited, even for metadata. The residual leniency is named: a
record created without a status line escapes the derivation, and the
form rule here and in `AGENTS.md` is the only guard.

Its weight is proportional to what the session decided, and
`DESIGN-SESSION.md` is not the template. That record is unusually dense
because its sessions were transmitting conclusions already reached across
two prior rewrites, not discovering them; most sessions settle far less
and get a far shorter record. Where reasoning *is* discovered live the
record matters more, not less — nobody holds the answer in advance to
check it against, so whatever the curator judged unimportant is gone.
That is the real reason it is written while the session is live rather
than reconstructed afterwards.

**Two kinds of session; more than one record per decision.** A decision
is usually *formulated* in a messy session, where the reasoning is being
discovered and several positions die, and may later be *attacked* in a
deliberate one, where the author already holds the answer and tries to
break the draft — convened at judgment, never owed (see Status). Both
kinds file records, and a decision may carry several — these are
not ADRs and nothing here wants one record per decision. What a record
must not carry is the *process*: it keeps the decisions and the
alternatives that died with their reasons, never the route taken to reach
them.

`grep -l "^Status: Proposed" docs/par/*.md` derives the records not
yet governing — anchored, because an unanchored match also finds
records that merely quote the query, this one included. It is state,
not a debt list: what a Proposed record awaits is named in its own
text or its own `Owed:` marker (PAR-0003's design session), and no
trigger elsewhere makes anything due.

**Raw transcripts are not retained.** The tooling writes one per session
and expires it on its own timer; the curated record is what survives, and
that is deliberate. A transcript is not a cheaper primary but a worse one:
unreadable at length, and usable only by reconstructing the argument out
of it, which is the cost this tier exists to remove. What guarantees the
curated record's fidelity is that it is written while the session is live
and the reasoning is still in hand — not a raw copy sitting behind it,
which would only move the reconstruction later.

The retrospective work list cannot be derived from citations: a sweep of
the below-tier-2 citations in tier 1 misses any settled system tier 1
never cited, and two escaped it before this was caught (2026-08-02;
primary: `SESSION-2026-08-02-distill-worklist.md`, with the rejected
alternative — `Proposed` stubs as tier-2 placeholders — and why
todo-list pressure argues for a sharper debt system instead). That
sharper system arrived as marker rule v2: each system owed its rationale
is a stub record at its own number carrying its `Owed:` marker
(PAR-0002, "What counts as debt"), so the work list is derived after all
— the ledger's `docs/par/` entries — and the order is
`docs/PLAN-DEBT-ORDER.md`'s. Sequencing calls that are genuinely a
plan's own — scope, order, build sequence, definition of done — are not
architecture decisions and stay in their plans.

## Consequences

- `DESIGN-SESSION.md`, `DESIGN-BRIEF.md`, and the exhausted `PLAN.md` live
  in `docs/archive/`. `PLAN-TOOL-CONTRACT.md` moves there when it
  freezes; `PLAN-DISTILL.md` froze, superseded, on 2026-08-02. They are
  never edited; distillation reads them, it does not touch them.
- Resolves two `DEFERRED.md` entries, which move out: *within-record
  authority for the design session* (the rule is stated above, without
  ever amending the frozen record) and *how frozen planning documents
  remain discoverable* (citable names are bare filenames —
  "DESIGN-SESSION.md Exchange 5" — which survive the move, and archive
  status is terminal rather than maintained).
- A plan gate that makes an architecture-touching decision records it as a
  rationale and cites it; the plan keeps what is genuinely its own.
- The gap between decided and distilled is present debt: each owed
  system is a stub record in `docs/par/` carrying its `Owed:` marker
  (PAR-0005..0018), retired one marker at a time as distillations land.
  Until a decision's rationale exists, its exchange or gate citation
  remains the governing pointer — named in the stub's marker reason. The
  order lives in `docs/PLAN-DEBT-ORDER.md`;
  `docs/archive/PLAN-DISTILL.md` sequenced this before it was superseded
  (2026-08-02).
- The debt and records machinery settled in archived `PLAN.md` was
  distilled first rather than waiting on an evolution trigger — the
  most-doubted mechanism in the repo, fended off three times with
  nothing recorded; distilled, it gained its challenge surface
  (PAR-0002).
- A doubt against a founding decision lands on a normal rationale and
  either falls (a Challenges entry) or succeeds (the record is rewritten)
  — without either path touching the archive.
- A doubt that matters but changes nothing has a landing place. The
  tradeoff stays visible without the decision moving, and when a
  rationale does need improving, the accumulated entries are the
  evidence — read by the human, who alone calls the tipping point.

## Challenges

- **2026-08-01 — "The costs are real: accepted distillations govern, so a
  reinterpretation error legislates instead of misreporting;
  individuation is lossy even at perfect sentence fidelity; and the
  fidelity gate is a single acceptance review."** Raised in session the
  day retrospective distillation was accepted. Held: these records are
  working memory — reread carefully and repeatedly until internalized —
  so review is continuous rather than a one-time gate; and the payoff is
  immediate even short-term, because only a governing tier-2 record
  carries a challenge surface, and undistilled decisions leave recurring
  doubts (the debt system, three times over) re-litigated and unrecorded.
  What survived of the challenge became working rules and sequencing in
  `docs/archive/PLAN-DISTILL.md`: front-load while session memory is
  fresh, order by doubt traffic, quote decisive source sentences
  verbatim. Fuller
  record: none filed (2026-08-01 session).
- **2026-08-02 — "Admitting friction evidence would creep the section
  toward the curated scrapbook the exclusion paragraph forbids."**
  Raised by the agent during the PAR-rename session, against the rewrite
  that made this section a tradeoff log. The occasion was itself an
  incident: the prior wording gave doubts that matter but change nothing
  no place to land, which was breaking and forced the rewrite — the PAR
  system tuned through its own living-record mechanism, landing here
  because a tradeoff log for decisions lands with nothing else.
  Dismissed by Kendrick: the section creeps toward a log, which is its
  design, not a scrapbook — friction is deliberately stated and
  human-confirmed, never inferred, and every entry carries its doubt
  with its resolution or the lack of one, so the trigger-less, unbounded
  character of a scrapbook never arrives. Fuller record:
  `SESSION-2026-08-02-par-rename.md`, Exchange 4.
- **2026-08-02 — "One primary per decision might be bad practice —
  shouldn't a session's argument land in one session record?"** Raised
  by Kendrick against the per-argument practice the PAR-rename and
  PAR-scope records had just established apropos, and resolved by him
  in its favor: a single record of a long session, "for long sessions,
  makes massive files that have to load into context" to assess any one
  decision — bloating exactly the resource the tier exists to spare —
  where per-argument primaries keep the frozen log clean and granularly
  addressable. Held, and the practice formalized above: the unit is the
  argument, not the sitting. Fuller record: none filed; the two
  per-argument records of 2026-08-02 are the demonstration.
