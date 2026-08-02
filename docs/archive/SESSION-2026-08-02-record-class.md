# Session record — 2026-08-02 — the record class

A primary record (tier 3), live until this session closes and frozen
after. It holds the argument that produced ARCH-0001's rewrite from the
ADR class to architecture rationale.

It deliberately does **not** restate what ARCH-0001 now says. Tier 3's job
is what tier 2 drops: the alternatives that died, and the route by which a
position was overturned. Where a conclusion is fully carried in ARCH-0001
this record points at it rather than repeating it. Kendrick's positions
are verbatim; exchanges are numbered so passages are citable.

The session opened on `PLAN-DISTILL.md` Phase 2 and never reached it; what
it reached instead was the apparatus that plan runs on.

State at the start: `docs/adr/` held one record, ADR-0001, adopting
architecture decision records on the Nygard model — immutable once
accepted, three change classes and only three, superseded rather than
edited. Nothing had ever been superseded or retired.

---

## Exchange 1 — Retirement location

> "one improvement to adr0001, retired adrs go into a different folder
> please. just keeps it easy to browse the standing records without having
> to dig through adrs that are no longer active"

ADR-0001 already moved superseded records out of `docs/adr/`, so the
stated motivation was met. A different defect justified the same change:
`docs/archive/` was defined as *primary records*, and a dead ADR is a
tier-2 distillation, so filing it there put a tier-2 record in tier 3
where the walk-down lands in something itself walked down from.

Rejected: `docs/archive/adr/`, which would have preserved the single rule
that terminal records live in the archive — the rule plans also obey. Lost
to `docs/adr/retired/` on Kendrick's ground that the archive should mean
one kind of thing.

The whole outcome was superseded by Exchange 9. Only the tier-mismatch
reasoning survives into ARCH-0001.

## Exchange 2 — Cross-citation

> "we can also update the adr-0001 for a potential cross-citing mechanism.
> any ideas?"

Produced the derive-don't-store mechanism now in ARCH-0001. Rejected: an
append-only `## Cited by` section — hand-maintained state already present
in the tree, and a fourth change class where ADR-0001 permitted three.

Then three paragraphs adjudicating which change class the edit fell into.
It produced nothing and is recorded only because its failure is what
Exchange 3 attacked.

## Exchange 3 — The apparatus outgrowing the content

> "Genuinely if the system for the ADRs undermines the ability for the ADRs
> to be clear then there's a problem with the ADR system itself"

Conceded, with the evidence: two turns on the rules of the record system
and zero architecture decisions distilled; `docs/adr/` holding one file
governed by ~200 lines of constitution; nothing ever superseded or
retired. The repo already names this shape — the anti-bureaucracy
invariant, and "ceremony ahead of need" in `archive/PLAN.md`.

Split named at the time: part mishandling (a one-paragraph mechanism
followed by unasked-for constitutional adjudication), part genuine
over-specification — rules written against imagined cases, failing at the
rate such rules fail.

Two claims from this exchange were withdrawn later. "Drop the closure"
(permit a fourth change class) died in Exchange 4 once supersession turned
out to be cheap. And the claim that supersession granularity equalling
record granularity was a *defect* was simply wrong — it is true of every
versioned-document system.

## Exchange 4 — Granularity, and what supersession costs

> "A plan is not an ADR. The ADR plan didn't codify anything, and the cross
> citing wasn't an accepted ADR, as you said. I don't think ADRs should be
> particularly granular either. I don't mind if an ADR that needs to be
> refined is retired, it costs nothing. And if the refinement wasn't to
> enable a change, the refinement is free per ADR-0001 to begin with"

The decisive move is "it costs nothing." The case for fine granularity
rested entirely on wholesale supersession being expensive; it is a copy,
an edit, a redate, a move. The position it overturned was mine and it had
been argued twice: three separate records for the debt machinery —
doctrine, form, enforcement — individuated by what could be superseded
independently. Wrong premise, so the split collapsed to one record, and
coarse beat fine because a wholesale rewrite yields a record that reads
whole.

Also conceded: ADR-0001's mechanical revision test said "another file,"
not "another record," which is why a *plan* amendment had been read as
disqualifying a revision. Over-broad as written.

## Exchange 5 — What these records are for

> "ADRs need to read as whole. That's pretty important. They serve as (more
> or less) the long-form reasoning that rolls up to the short form that
> exists in ARCHITECTURE.md."

Surfaced a live tension: `PLAN-DISTILL.md` working rule 1 ("quote, don't
paraphrase, at the load-bearing points") defeats itself if pushed, since a
quilt of verbatim quotations is fragment-assembly by another route.
Resolved in the plan — quotes carry the decisions, prose carries the
argument, and the argument must stand if only the prose is read.

## Exchange 6 — Not ADRs at all

> "It's not finding something wrong with it, it's living the reasoning you
> just suggested. Maybe we shouldn't even call it ADR? I feel like just
> Reasoning-0001 or something is accurate, and calling it ADR will be
> pattern matched to all the baggage ADR carries with it until the actual
> file is read and acknowledged as 'literally not ADR except in name'"

> "so maybe R-0001 actually, with R standing for reasoning"

The correction first: framing the day's edits as four *defects found in
ADR-0001* was the immutability lens leaking back in. Under a living-record
model, refining a record is the normal operation, not a defect report.

The structural argument that settled it — archaeological immutability
being redundant when a tier 3 exists — is carried in full by ARCH-0001's
Context and not repeated here.

What the decision cost, recorded because ARCH-0001 does not dwell on it:
diff legibility. With free editing, a wording tweak and a reversal are no
longer distinguishable by status line; you have to read the diff. Judged
small with one author, and that judgment is the exposed one.

Precedent noted at the time: `Owed` was named as it was "because a marker
is not a fault and should not pattern-match visually to real exceptions" —
the same argument about names, one level down.

## Exchange 7 — Naming

> "Give me some good recommendations for alternative names then that
> capture the architecture stuff too. Unfortunately architecture decision
> reasons won't work.. for obvious reasons lol"

Constraint identified: a three-letter, A-initial acronym ending in R is the
ADR silhouette and gets misread before it gets read.

The three that lost, none of which appears anywhere else:

- **`AR-0001`, "Architecture Rationale"** — technically the most correct
  name, since *rationale* is the term of art in the design rationale
  literature (QOC; MacLean and colleagues) for exactly this distinction:
  recorded reasoning behind a choice, as against a decision log. Lost on
  shape — two letters, A-initial, readable as a typo for ADR.
- **`R-0001`, "Reasoning"** — Kendrick's own first proposal, scope carried
  by the directory instead of the token. Maximum distance from ADR; lost
  because the token then says nothing about scope, leaving the
  architecture-only rule resting entirely on the record's text.
- **`GROUNDS-0001`** — no baggage at all and in the repo's habit of plain
  precise words. Lost by dropping architecture entirely.

Also flagged: `docs/architecture/` beside `docs/ARCHITECTURE.md` differs
only by extension and would confuse listings and tab-completion, hence
`docs/arch/`.

> "I think ARCH-0001 with Rationale works nicely. Lets do that."

Token and word taken from different candidates.

## Exchange 8 — The granularity heuristic

> "Just as a general heuristic, the ARs are the smallest chunk that carries
> all the relevant things with it. They're almost wikipedia pages -
> summaries, they can be wrong, so they cite the source."

Replaced "granularity: coarse," which was one-sided where this is
two-sided — it bounds a record from above as well as below. The Wikipedia
framing then generalized past its occasion, into the statement now in
ARCH-0001 that every tier is a fallible summary of the tier below and
cites it for that reason. That was already the repo's authority rule;
what changed is that it is stated once instead of per tier.

## Exchange 9 — Convergence

> "Then the ARCHITECTURE.md is basically the same way. Did the rationale
> that once a rationale is pretty bulletproof it will stop being edited get
> carried into the 0001?"

It had not. ARCH-0001 claimed only that the *directory* goes quiet — a
write rate — which left "edited whenever a reread finds it wanting"
reading as a standing licence. The asymptote property was added in
response and is now in ARCH-0001. Worth noting as a near-miss: nothing in
the draft flagged its own absence, and it was caught by being asked for.

## Exchange 10 — ARCH-0002, the first record under the new class

Distilled from `archive/PLAN.md`, one record per Exchange 4, **Proposed**,
so `archive/PLAN.md` still governs. Twenty-six quoted passages
machine-verified verbatim against the source.

Four places where the record supplies reasoning its source left implicit,
named rather than resolved silently, per the fidelity rule — recorded here
because they exist nowhere else and are what its acceptance review must
settle:

1. Why a placeholder never invents a signature (source says only "never
   inventing one").
2. Why the mismatch test must not self-heal (source gives the rule
   parenthetically, without a reason).
3. The generalization that every leniency in an enumerator is a way for
   debt to vanish quietly (source gives one specific instance).
4. The connection of the closed machinery class to the invariant's
   "exemption to adjudicate" (source leaves these as separate passages).

Also deliberate: the layout settlement excluded as component decomposition
rather than debt machinery, moved to `PLAN-DISTILL.md` Phase 5.

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
down, so a rationale with no primary underneath it is one that argument
does not cover. ARCH-0001 was in that state at the moment it was rewritten.

Form decided as delegated, and both alternatives were rejected explicitly.
A raw transcript: an agentic session is mostly tool calls and drafting. A
summary: it bakes in one reading and discards the material a different one
would need. What survived is the rule now in ARCH-0001 — quote the person,
compress the argument, keep what lost.

## Exchange 12 — Curated record versus raw transcript

> "because if you consider how many times the design documents had to be
> revisited in order to really harden the architecture as is, it might be
> worthwhile. but I'm not sure."

Settled by checking rather than asserting, and the checking produced two
findings that no other record holds.

First, the three 2026-08-01 sessions that produced the record class
survive on disk — `d289f467`, `14545adb`, `78389c66` — which falsified a
claim made earlier in this very record, that the class's own origin was
unreconstructable. Second, `cleanupPeriodDays` is unset, so default
retention applies and all of them expire on a timer measured in weeks.
"It exists on disk" is not durability.

Proposed on that asymmetry — about a megabyte per session against
irreversible and already-scheduled loss — that transcripts be retained
outside the tier structure, not citable and not governing, as fidelity
evidence. Ruled against:

> "yeah we don't want to have the wholesale transcripts lol"

The supporting reason holds independently of repo hygiene and is in
ARCH-0001. An appeal to the design-session precedent was also made here —
nine curated exchanges carried every revisit — and does not hold as
stated; corrected in Exchange 13.

One contradiction surfaced and was repaired rather than fudged: this
record was committed mid-session while ARCH-0001 called archived records
frozen and never edited. Settled — a session record is live for its
session and freezes at close.

## Exchange 13 — The design session is not the template

> "the original decision sessions that are documented in the design
> documents are not wholesale verbatim either, they just look like it.
> those sessions were the deliberate decision outcomes from the entirety
> of version 1 and version 2 so the heavy distilled reasoning isn't
> necessarily going to really be the norm. it works for those because I
> already knew the answers and knew where you would mess up and also had
> a good idea of how to get you to understand it in like 10 messages."

Corrects an appeal made twice in this record and once in a commit message:
that `DESIGN-SESSION.md`'s nine curated exchanges prove the curated form
sufficient in general. They prove it sufficient for a session of that
kind — one transmitting conclusions already reached across two prior
rewrites, with a working model of where the machine would go wrong. The
record reads like a verbatim transcript and is not one.

Two consequences, pulling opposite ways. The proportionality rule is now
in ARCH-0001. The other is not, and is the uncomfortable half: in the
design session Kendrick could check any distillation instantly against an
answer he already held, whereas in a session where reasoning is discovered
live neither party has the answer in advance, so whatever the record
judged unimportant is simply gone. Not an argument for transcripts, which
failed on their own merits — an argument for writing the record live,
which was already the rule but had rested only on memory decay.

Noted against `PLAN-DISTILL.md`'s risk register and not yet acted on: "the
oracle depreciates" is weaker than stated for the founding decisions,
whose answers have survived two rewrites and are not session memory. What
depreciates is the argument shape — which alternative was rejected and
why — so the front-loading case narrows rather than disappears.

## Exchange 14 — Formulation and hardening as separate sessions

Kendrick's proposal, answering Exchange 13's problem directly: draft the
rationale in the messy session, then harden it in a later deliberate one
run like the design sessions — arriving holding the answer and attacking
the draft. This fixes the unchecked-curator problem structurally rather
than mitigating it, by ensuring the record that matters is written when it
can be checked instantly.

Objection raised: a hardening session attacks what is in the draft rather
than re-deriving what already died in formulation, so the reversals that
made this session valuable would go unrecorded if only the hardening
session filed a record.

> "because these aren't adrs I'm fine with having at least two if not
> more transcripts for this. just make sure that it's not all the messy
> fluff. having the hardening session can be debt and that's fine, and
> come due when the architectural decision is truly load-bearing"

Making the hardening session *debt with a trigger*, rather than a gate
every rationale must pass, resolved a scoping worry without adding a rule
— and landed on machinery already present, the status line as its own
marker. The rest is in ARCH-0001.

Two things went wrong immediately, both worth keeping.

The derivation was defective on first run: unanchored, `grep -l "Status:
Proposed"` matched ARCH-0001, because ARCH-0001 quotes the query in its
own text. Anchoring fixed it. The rule had been correct in the abstract
for ten minutes and wrong the first time it executed — Exchange 3's lesson
arriving on schedule.

And ARCH-0001 cannot be marked Proposed at all, because "Proposed does not
govern, the prior source still does" presupposes a prior source and the
founding record has none; marking it so would leave the tier ungoverned.
It is therefore Accepted while still owing its hardening — the one record
the derivation misses, named explicitly in `DEFERRED.md` rather than
finessed.

## Exchange 15 — The reconstructed-challenges gate, closed

> "I'll fill out the doubts against the debt system whenever, don't leave
> it open because I might not remember, but I'm sure it'll come up again."

`PLAN-DISTILL.md` Phase 2 had offered two homes for the three doubts
Kendrick has raised against the debt system: seeded into ARCH-0002's
Challenges section marked *reconstructed*, or folded into Context as
objections considered. Neither taken, and the reason beats both.

A doubt that genuinely recurs does not need reconstructing — it arrives on
its own and lands as an ordinary contemporaneous entry, which is what the
section is for. Reconstruction would have pre-filled a section that fills
itself, using the weakest material available (the plan's own risk
register: memory of an argument, formatted as a record). Closed rather
than left pending, because a pending gate depends on recall and the
mechanism does not.

ARCH-0002 therefore lands with no Challenges section, which is correct
rather than an omission: the challenge surface is the record existing at
tier 2, not entries in it.

---

## Where things stand

Doctrine is in ARCH-0001 and not repeated. What this session leaves
behind:

- ARCH-0002 sits **Proposed**, so `archive/PLAN.md` still governs the debt
  machinery. Accepting it moves `README.md` lines 41 and 98 and
  `AGENTS.md` line 18, and retires three citations from the `DEBT.md`
  distillation entry. Its acceptance review must settle the four fidelity
  flags in Exchange 10.
- ARCH-0001 is Accepted and governs, but was formulated here and never
  attacked. Its hardening session is owed, not yet due, and named in
  `DEFERRED.md`.
- The reconstructed-challenges gate is closed; nothing is reconstructed.
- Still open: the layout settlement's new home in `PLAN-DISTILL.md`
  Phase 5, and the overstated "oracle depreciates" risk in that plan.
- The 2026-08-01 sessions that adopted the record class have no curated
  primary, and their raw transcripts will expire unread. That reasoning
  survives only as ARCH-0001's text and git history. Accepted rather than
  filed as debt: the convention exists so it does not recur, and curating
  them now would be reconstruction from transcript.
