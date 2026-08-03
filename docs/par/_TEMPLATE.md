# The PAR template

Copy to `docs/par/NNNN-short-title.md`, delete the guidance, fill the
slots. Every section carries the test it has to survive, stated at the
top of its guidance in bold. Prose that survives none of them is the
freewheeling this form exists to stop.

The drafting session that produces the material is
`how-to/repo-work/draft-a-par.md`, run manually. This file is where its
output lands; that file is how the output is found. Governed by
PAR-0004.

**The bar for the whole rationale: if it is all cheap, it isn't a PAR.**

**Two mechanical rules, because `docs/par/` is a derived surface.** A
column-0 line beginning `Owed:` is enumerated into `DEBT-AUTO.md` by
`sieve.debt`, and an off-form one raises rather than being skipped. A
column-0 `Status: Proposed` line lands the file in
`grep -l "^Status: Proposed" docs/par/*.md`, the not-yet-governing
derivation. That is why every example below is indented and the stamp
placeholder is not a well-formed stamp. In a real PAR both lines sit at
column 0 and mean what they say.

---

## The skeleton

```
  # PAR-NNNN — <the system, not the ruling>

  Status: <Proposed | Accepted | Retired>
  Date: <YYYY-MM-DD>

  <marker line, stubs only — see "Stubs">

  > <Kendrick's own words, verbatim>
  >
  > — Kendrick, <date>

  ## Sessions
  ## Domain
  ## Inputs and outputs
  ## Responsible for
  ## Evidence
  ## Expensive
  ## Cheap
  ## Edges
  ## Outcomes
  ## Why this boundary
  ## Challenges
```

**The title test, three parts.** Is the name clear to a user — does it
identify the domain? Is it clear to someone working in the repo — does
it identify the responsibility? Would it be confused with, or
pattern-matched to, something else? Name the file for the system, not
the ruling: `0007-tool-contract`, not `0007-tools-are-pure`. The ruling
can change while the system stays, and numbers are never reused.

Cite every other rationale as `PAR-NNNN` at least once in that exact
form — the reverse index is `grep -rl "PAR-NNNN" docs/ README.md
AGENTS.md`, so a citation appearing only as a path is invisible to it.
Never store an inbound link.

**Plain language first.** Repo-specific terms and citations go in
parentheses, so what lands here does not inherit the session's
vocabulary. Do not simplify — keep it accurate and drop the jargon,
which are different operations.

---

## The epigraph

> **Test: is this Kendrick's, verbatim?**

His own statement of what the system is for, blockquoted, attributed
and dated.

**Written by nobody else, ever.** If no such statement exists — every
distillation of a founding decision is this case, since the source is
the design session rather than a person in the room — the slot is
absent. An agent filling it with synthesized prose in his voice is the
worst failure this system can produce, worse than an empty slot,
because a reread cannot tell it from the real thing.

## Sessions

> **Test: does every claim here trace to a filed primary?**

The records in `docs/archive/` that resolved this, each with what it
settled and where:

```
  `SESSION-<date>-<slug>.md` — the boundary named (Exchange 1); the
  adversarial pass and what it killed (3); the naming call (6).
```

A rationale argued live files its primary in the same commit. One with
no primary is a rationale the living-records argument does not cover:
the archaeological function is discharged one tier down, and with
nothing down there it is discharged nowhere.

A distillation is reading its primary rather than filing one, and adds
the source passages and the decision's **original** date. It reports
the decision as made and never improves it — daylight between the
distillation and its source is named before acceptance, never silently
resolved. Improving on a founding decision is a new decision at its own
number.

Session files written under the drafting how-to tag their outcomes
`[TYPE][STATUS]`, so a citation can name an outcome rather than only an
exchange.

## Domain

> **Test: dense interactions inside, sparse across — and the straddle
> test, which a doubt landing equally on two rationale has already
> failed.**

The named system this owns, and where its boundary runs.

State the far side explicitly and whose it is: *what an operation owns
is PAR-0020's; how the panel is drawn is PAR-0013's.* A boundary that
says only what is inside cannot be tested by anyone.

State the occasion — what made this need deciding now. "It seemed time"
is a rationale that did not need writing.

Apply the revision test before you accept the boundary: simulate this
decision reversing. If rewriting this rationale forces substantially
rewriting another, the boundary leaked — merge the two, or turn the
dependency into a citation.

## Inputs and outputs

> **Test: does anything cross this domain's edge? If nothing does, say
> why — do not omit the section.**

What may pass in, what may pass out, and what may never pass either
way.

Some domains have no traffic: a convention, a rationale class, a naming
rule. Those state that they have none and why, because an absent
section is ambiguous — a reader cannot tell "none" from "forgotten" —
while a stated absence is evidence, the same reason a placeholder is
the debt entry rather than a note about one.

## Responsible for

> **Test: may this system change the thing? If it only declares it
> under rules held elsewhere, it does not own it.**

What this system is answerable for. Usually short, and usually shorter
than it first looks.

Where the distinction carries weight, use the verbs consistently and
say so — *declares* under rules held elsewhere, *interprets* values it
did not author, *owns* only what it may change. PAR-0007 is the worked
example.

## Evidence

> **Test: for each system cited, what transfers and what does not? One
> cited without that is decoration.**

The drafting session sweeps four classes: systems that worked *because
of* this seam, systems that failed because of it, systems that refused
it and failed, and systems that refused it and succeeded anyway. That
sweep belongs in the session file.

What lands here is the distillation — what applies to this repo, with
concrete examples, and what does not. The fourth class is the one that
earns its keep: if something succeeded without this seam, either the
seam is not generally good practice and you must name the specific
commitments that force it here, or the argument is weaker than it
looks.

## Expensive

> **Test: does being wrong about this later cost a rewrite of every
> caller, a schema migration, or a store migration?**

This is the decision section, named for the filter it has to pass.
Signatures, return types, what enters a hash, where identity lives.

State the reversal cost in the sentence that makes the claim. Not "this
is important" — *"a knob in the wrong file is a schema migration plus a
changed hash for every result that used it."*

A claim that can be added later without touching what already exists
has not earned admission here, however true and however important. It
is a citizen of the domain and goes below, or it belongs to another
domain and goes there, or it waits. A rationale that settles cheap
claims alongside expensive ones settles an empty room, and the cheap
ones are exactly what turns out wrong once something real exists to
argue against.

## Cheap

> **Test: can this move without anything else having to move with it?**

The domain's citizens: what lives inside it and does the work.

Cheap is not a verdict on importance — it is a statement about
mobility, and it is why the record can govern without these being
settled. A cheap internal is often more central to daily use than
anything above it. It is admitted to the domain on the same terms; what
it has not done is earn admission to *Expensive*, and the only thing
that earns that is carrying the weight of a future rewrite.

This list grows after acceptance, and its growth is not a gap.

**An entry lands as the answer to a question that arose, never as an
inventory somebody sat down to write.** Someone asked whether this
lived in the domain and the answer was yes; that exchange is the entry.
Without the trigger the section has no terminal form and grows by whim.

## Edges

> **Two flags. Sharing both an upstream and a downstream with another
> record means you scoped one domain as two. Identical expensive
> internals means you shuffled things to look different.**

Every relation to another rationale, one per line, direction first.
`A → B` reads *A constrains B*.

```
  PAR-0005 → this   an op is a value; fixes what `lower` returns
  this → PAR-0012   the yardstick a tool suggests, consumed there
  this ↔ PAR-0020   the placement rule, stated from both sides
```

Inbound edges are what this record was decided against and must cite.
Outbound edges are **bequests**. A double arrow is a shared border
deliberately stated twice.

A bequest is provisional and must read that way. The receiving
rationale may refuse it on evidence this one did not have, and refusal
amends this record rather than being overridden by it. A bequest to a
stub goes to a file that cannot answer yet — write it as a question the
stub will settle, not a ruling it will inherit.

Draw no diagram by hand. A figure is a rendering of this list, so a
hand-drawn one is a second copy to keep in sync — and if it overlaps a
figure in `ARCHITECTURE.md`, two documents now have to agree edge for
edge forever.

## Outcomes

> **Test: does each one name something that can be done, or checked, by
> somebody who is not you?**

Two classes, because a generic outcome accepts any prose while these
two do not.

**For working in the repo.** What rules follow from this. What becomes
easier. Which how-tos reference it — their titles and one or two
sentences on what following them accomplishes — and, the part that
bites, whether those how-tos can actually deliver what you just said
they deliver.

**For the user.** How it makes SIEVE easier to use. How it makes SIEVE
easier to *trust*, which is the separate and usually harder question.
And what this component does so that other components can do their job
accurately and efficiently.

Phrased as intention rather than current fact. These are the yardstick
later proposals against the system are judged by, which is why they
must be operable rather than admirable.

## Why this boundary

> **Test: what does it cost to not do it this way?**

The closing argument, in two parts: what is paid by drawing the
boundary somewhere else or not at all, and why this seam is a natural
one rather than a line someone chose.

Short. If it cannot be made short, the boundary is not yet understood.

## Challenges

> **Test: does this doubt break the decision? If it does, it is not an
> entry — the record is rewritten.**

The tradeoff log: doubts and frictions deliberately stated against the
decision, with their resolution or the lack of one.

```
  | Date | Raised by | Doubt | Standing |
  | --- | --- | --- | --- |
  | 2026-08-03 | Kendrick | The record has no teeth — no test fails
    today because it exists. | Held; enforcement arrives through the
    property tests it derives. |
```

Long arguments spill to a bullet under the table rather than swelling a
cell. Three further rules:

- Friction is stated, never inferred. An agent may point it out; a
  human confirms before it lands, and *Raised by* is there so a reread
  sees at a glance which entries survived that.
- Bare friction — evidence that something rubbed, with no argument — is
  not an entry. It lands with the reason it is friction, or it is
  dismissed and enters as the record withstanding it.
- Confirming evidence enters only paired with the doubt it answers.
  Free-floating vindication has no trigger and no terminal form.

Entries report; they never govern. This section is what repays the
apparatus: a doubt that recurs — and they recur, the same objection
three times in a year — is re-litigated from scratch every time it
lands nowhere.

---

## Stubs

A system owed a rationale is a stub at its own number: the skeleton
above with a marker in place of the body, at column 0 in the real file.

```
  Owed: <stamp>: rationale for <system>; governs until acceptance:
  <what currently governs>
```

A marker states what is **owed**. It cannot state what is **claimed** —
one marker per file under rule v2 means anything else stuffed in there
becomes a single unreadable run-on line, and nobody scanning for "does
someone already own this?" reads marker prose. Compare PAR-0019, whose
borders are buried in a 300-word marker sentence, with PAR-0020, which
put them in the body.

So a stub fills `Domain`, `Responsible for`, and `Edges` at whatever
fidelity is honest the day it is filed — from the sitting that filed
it, never from a later guess. `Expensive` may be a list of the
questions that will be expensive. Everything else stays empty.

**"Unknown — here is the question" is a valid entry.** PAR-0019's seam
against PAR-0012 is genuinely its first open question; itemizing a
border for it would be inventing one. Borders are backfilled when the
stub is next touched, never in a sweep across every stub at once.

What this buys is narrower than it looks, and overclaiming it is the
error this template was written after. It does not stop another
document asserting into unclaimed territory. It makes the territory
greppable while it is still unsettled, so the assertion is visible
rather than silent.

---

## Before accepting

Acceptance means the record governs and the roll-up is owed that
moment — `ARCHITECTURE.md` for architecture, `README.md` or `AGENTS.md`
for repo mechanisms, amended in the same commit. A `Proposed` record
amends nothing, which is what makes it free to sit.

Four checks, each catching a failure that has actually happened here:

- Every claim in `Expensive` states its reversal cost. Any that does
  not is in the wrong section.
- Nothing in `Expensive` is there because it is important. Importance
  is not the filter; reversal cost is.
- Neither Edges flag fires.
- The reader finishes the file convinced without opening another. A
  decision split across three cross-citing files makes the reader do
  the assembly, which is the work this tier exists to have already
  done.
