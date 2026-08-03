# Session — the PAR form, redesigned around admission by cost

Status: Frozen
Date: 2026-08-03

The argument that produced `docs/par/_TEMPLATE.md`. Kendrick and Claude
(Fable 5). It began from the PAR-0007 scope cut, which files its own
primary; this record holds only the form.

Kendrick is quoted verbatim. Exchanges are numbered for citation.

---

## Exchange 1 — The occasion

The scope cut had found PAR-0007 stating an admission filter in prose
and then failing it three times. The stub-position finding — PAR-0020
putting its borders in the body where PAR-0008..0019 leave them in
marker text — was to be adopted and cited as evidence for PAR-0004. The
decision was then made to draw the form itself:

> "Lets actually write the template now, it's an architectural decision
> yes and it is kinda costly to change later but not *that* costly for
> things that are docs. Instead of any one PAR, scan all the pars, and
> draft the template that sits in the PAR directory using a cohesive
> format, clear format instructions, optimized for readibility, the
> role of EVERY par, etc."

## Exchange 2 — The form, stated

Kendrick's design, given whole rather than derived:

> "PARs distill: at the top, my explanation. Then list the sessions
> that resolved it. Then name the domain. Name what it is responsible
> for. What are the expensive internals? What are the cheap internals,
> but still in the domain? That last one is a growing list, not
> necessarily required for the bar for something being an accepted PAR
> (by definition, since it's cheap). Then say how it interacts with
> other things. This dissolves the context section, I think. Challenges
> should have a specific form: probably a table, since it's more
> readable for me."

And on the section the form appears to drop:

> "We want to have outcomes dissolved too, or have the stuff I said,
> since outcomes can be anything and specific outcomes by class
> automatically names how to operationalize things."

## Exchange 3 — Expensive is the Decision section renamed

The strongest consequence of the form, argued and accepted: there is no
`Decision` heading. What was the decision now has to enter through a
slot named for the filter it must pass. PAR-0007 had to state that
filter in prose and then police itself, and did not; a section *named*
for it makes a claim that costs nothing to reverse visibly in the wrong
place.

The rule that came with it: state the reversal cost in the sentence
that makes the claim. Not "this is important" but "a knob in the wrong
file is a schema migration plus a changed hash for every result that
used it."

## Exchange 4 — Cheap is citizenship, not a lower bar

The first draft described the cheap list as things that "did not meet
the bar above," which Kendrick rejected:

> "Cheap list is the admission ticket to the domain. It's important,
> but they're like the citizens of the domain; they can move cheaply,
> so they don't have to be declared for the PAR to be governing. The
> expensive ones are the ones that gain admission to being expensive by
> carrying the weight of a future rewrite."

So both sections are admissions, on different tickets. Cheap is a
statement about mobility and not about importance — a cheap internal is
often more central to daily use than anything above it. What it has not
done is earn admission to *Expensive*, and the only thing that earns
that is carrying the weight of a future rewrite.

The scrapbook objection was raised against the growing list: PAR-0001
forbids exactly this shape in Challenges, where free-floating
accumulation has no trigger and no terminal form. Answered with a
trigger rather than a cap — an entry lands as the answer to a question
that arose, never as an inventory somebody sat down to write.

## Exchange 5 — Edges, and the diagram that derives

> "So maybe the PARs should also have a section calling out the edges
> to other PARs explicitly - yeah actually, let's add that to the
> template. That makes drafting the diagram free basically."

Edges are an authored list, direction first, `A → B` reading *A
constrains B*. Inbound edges are what the rationale was decided
against; outbound edges are bequests; a double arrow is a border
deliberately stated twice. A figure is then a rendering of the list, so
no hand-drawn diagram is a second copy to keep in sync — which is the
contradiction the scope cut had just found in PAR-0007.

One constraint stated so it is not lost: only edges this rationale
asserts belong in the list. PAR-0001's rule that cross-citation is
derived still holds, and an inbound-link inventory would be the
hand-maintained state it forbids.

## Exchange 6 — Outcomes returns, split by class

The drafting how-to Kendrick hand-wrote during the sitting
(`how-to/repo-work/draft-a-par.md`) proved the first draft of the
template incomplete: it asks what a rationale means for working in the
repo — the rules, and whether the how-tos naming it can deliver what is
claimed of them — and separately what it means for the user, where
being easier to *use* and easier to *trust* are distinct questions.

That is what "specific outcomes by class automatically names how to
operationalize things" meant. Outcomes did not need dissolving, it
needed splitting: a generic outcome accepts any prose, and those two
classes do not. The first draft had dropped the section and lost both.

The same how-to supplied the four-class evidence sweep — systems that
worked because of the seam, failed because of it, refused it and
failed, refused it and succeeded anyway. Settled: the sweep belongs in
the session file, and what reaches the rationale is the distillation of
what applies and what does not. The fourth class is the one that earns
its keep.

## Exchange 7 — Inputs and outputs, and naming the tests

Two refinements, both tightening rather than adding:

> "inputs outputs optional with the test, good. They should be included
> no matter what and explicitly stated for why they fail the test if
> theres nothing"

An absent section is ambiguous — a reader cannot tell "none" from
"forgotten" — while a stated absence is evidence. The same reason a
placeholder is the debt entry rather than a note about one.

> "Also, name the test in the template, either cleverly by section
> name or section name + hints in the template itself."

Every section opens with the test it has to survive. Coining a dozen
capital-T test names was rejected as the apparatus elaborating faster
than the content it holds; the two that already exist in PAR-0001 —
straddle and revision — are reused by name, and the rest are stated as
one-line questions.

## Exchange 8 — The mechanical constraint

`docs/par/` is a derived surface and is not in `sieve.debt`'s exclusion
list, so a template living there is enumerated like any other file.
Three constraints followed, and all three are stated inside the
template because a hint that teaches its own constraint is worth more
than a rule stated elsewhere: a column-0 `Owed:` line is enumerated and
an off-form one raises rather than being skipped; two files sharing a
stamp is an enumeration error, so a template carrying a well-formed
example stamp would collide the first time it was copied; and a
column-0 `Status: Proposed` line would land the template in the
not-yet-governing derivation, which PAR-0001 anchors precisely because
an unanchored match also finds files quoting the query.

Verified rather than asserted: absent from the derivation, no column-0
marker, `python -m sieve.debt write` a no-op at 25 entries.

## Exchange 9 — The word, and the tooling question

Five instances of *record* meaning *rationale* reached the template and
were caught by Kendrick reading it live.

> "fix the template, you're doing the stuff with record vs rationale
> again, and in like the worst place possible. Any tools at your
> disposal to catch yourself making that mistake so it doesn't
> permanently infiltrate stuff?"

The worst place is exact: the template is copied into every future
rationale, so an error there propagates rather than sitting still.

The honest finding is that the standing correction was already in the
agent's context for the whole sitting and did not hold — advisory
context loses to generation pressure, especially when the source
material being read (PAR-0001, PAR-0005) is itself full of the retired
word. Proposed instead, not yet built: a test over
`docs/par/_TEMPLATE.md` and `how-to/**` requiring any line containing
*record* to also contain *archive*, *primary*, *frozen*, or *session*.
Deliberately not repo-wide, because PAR-0001 carries the old word on
purpose and cleans at its next rewrite rather than in a sweep, so a
wider rule would force either that sweep or an allowlist. Line 99 was
reworded from "living-records" to "living-document" so the rule needs
no exemption at all. The limit is that it catches the word and not the
concept.

## Exchange 10 — What the boundary with the how-to layer turned out to be

PAR-0004's second challenge — whether the template convention folds
into PAR-0003 — was resolved at PAR-0003's acceptance in favour of
staying separate, and was reopened here with a new argument: a how-to
can be derived from a template, so it is one format rather than two.

It does not hold, and the reason is concrete rather than doctrinal.
`accepting-a-par.md`'s one real instruction is that the procedure is
executed manually because agents get PARs wrong, and the drafting
protocol is a message-by-message interaction script. No template can
carry that. The split is: the template holds the form and what goes in
each slot; the how-to holds the protocol. PAR-0004 stays its own
record.

The file's own history is the evidence. It was written by an agent
distilling one session, that did not work, Kendrick hand-wrote the
derivation procedure that replaced it, and the same pass found the file
misnamed — what it contains clears the bar for a solid draft, not for
acceptance. It split into `draft-a-par.md`, and `accepting-a-par.md`
remains to be hand-written as the Proposed-to-Accepted guide it was
always named for.

That episode was logged into PAR-0004's first challenge on Kendrick's
confirmation, as adjacent rather than direct evidence: a how-to
distilled from a session is not a template drawn from requirements, so
the doubt stands.

## What lost

**A `TEMPLATE.md` filename.** Superseded by the repo convention,
`_TEMPLATE.md`.

**Twelve stubs backfilled in one pass.** Rejected at Exchange 7 of the
scope-cut primary and restated here: borders are filled from the
sitting that filed the stub, never from a later guess, so they are
backfilled on touch.

**A dozen named tests.** Rejected as apparatus growth; one-line
questions instead.

## Owed from this sitting

PAR-0004's Decision still reads "the template form, its home, and how
conformance is checked — is open," which the template now answers. That
rewrite, and the migration of the form rules out of PAR-0001 that it
implies, are this sitting's undelivered work and are not recorded as a
marker anywhere, because `DEBT.md` holds one entry under rule v2 and
already has one.
