# Session: advancing the debt system — universal surface, identity, git-derived signal

Status: Frozen
Date: 2026-08-02

The argument that produced marker rule v2's design: the universal
surface, timestamp identity, the line-versus-git division, and the
planning-surface outcome. The separable record-form argument from the
same sitting is `SESSION-2026-08-02-record-outcomes.md`. Two
contemporaneous Challenges entries in PAR-0002 (adjacent-churn
conflation; `DEBT.md`'s nebulous role) cite this record.

## Exchange 1 — the charter, and the audit

Kendrick: "This session is for advancing the debt mechanism to be
completely formalized and automatic: the goals are: a system that can
be moved to auto-debt proper by way of some formalized convention to be
universally followed in the repo, and reasoning through how to sort
priorities. the goal of the priority sorting mechanism of the debt
isn't to get *perfect* sorting priority; it's to come up with potential
mechanisms of attaching information by construction to infer based on
*information that doesn't go stale at the time the debt is written or
reassessed*. Minimum is timestamp." He suspected the `DEBT.md` rewrite
had dropped genuine debts.

The audit found the suspicion half right, and the right half was the
important one. Entry-level: nothing unresolved was ever dropped —
`DEBT.md`'s whole history is three entries, one legitimately resolved.
What did drop in the rewrite: the pointer to `PLAN-DISTILL.md`'s
working rules, stranding rules 1–3 (quote-verbatim, decision-boundary,
doubt-traffic-outranks-order) in a superseded plan that PAR-0001's
first Challenges entry still cites as their home — with the new
priority line ("overriding intuition about importance") in unspoken
tension with the doubt-traffic rule. And the replacement — fourteen
hand-annotated items with hand ordinals — was hand-maintained state at
its purest, sitting in the last-resort file. Resolution of the
stranded-rules tension: under this session's design, priority moves out
of hand-priority lines into planning sessions (Exchange 5), where doubt
traffic is a judgment input to ordering — later derivable as a column
from Challenges-entry recency — so the tension dissolves rather than
being adjudicated.

The organizing principle for priority came out of this exchange and
governed everything after: **record facts and predicates at the event;
compute rankings at read time.** A stored ranking is a judgment about a
moving world and rots; a fact about the event cannot; a predicate's
truth is recomputed each read. Three classes: facts stamped at the
event (timestamp, citations), predicates evaluated at read (triggers,
edges), and pure read-time derivations (age, blast radius, churn,
doubt traffic) — the last class recording nothing at all.

## Exchange 2 — 80/20, and the pattern matches

Kendrick: "I like the classes. Not sure if all of them are necessary,
we want to 80/20 this and probably land the automation for this pretty
slowly. The idealized end state for this is some kind of script that
takes params to work in the repo and navigate debt items. I think this
might be pattern matching to stuff that already exists."

It does, in two directions. External: the design is self-admitted
technical debt (Potdar & Shihab's SATD literature) made grammatical
instead of mined; SQALE/SonarQube is the cautionary referent (stored
remediation judgments — exactly the class banned here); Tornhill's
hotspot analysis is prior art that read-time git derivation works; and
the deepest match is git itself — append-only facts, views computed at
read. Internal: the script already exists — `python -m sieve.debt`
gains read modes; AGENTS.md's two status greps are proto-read-modes.
The 80/20 cut: triggers-as-tests deliberately excluded (its own
DEFERRED trigger has not fired — building it would be building from
DEFERRED.md); creating-milestone recording deferred; blast radius and
friction as later columns.

## Exchange 3 — the two improvements, and the churn challenge

Kendrick: "we should leverage git as much as possible to derive the
debt auto, all the information there should probably be integrated for
when it's usable signal. also, work in the file itself that *doesn't*
touch the explicit debt line is signal for potential concurrent work
thats valuable and agent-interpretable, at the risk of overpromoting
high churn files. but high churn files are high churn because they're
load bearing and signals something else: over coupling. add that as a
possible challenge for the debt system PAR. ... First improving: we
need to scope the standardization of the debt tags so that it is
universally picked up no matter the file format. Second improving: we
need to determine what needs to be deposited on the actual line and
what can be explicitly derived from the git for free."

The churn conflation landed as a PAR-0002 Challenges entry. The first
improvement's shape: the file universe becomes the git index (tracked
files — universality definitional, exclusions inherited from
`.gitignore` rather than hand-listed), one reserved token with
per-surface canonical forms — rule v1 unchanged for Python, a column-0
`Owed:` line for every other text surface, one per file, keyed
`(path, <file>)`. Heading-anchored keys for docs lost: heading text is
mutable content, so `(path, heading)` churns exactly like line numbers.
The second improvement's dividing rule: the line carries only what git
cannot know — the semantics; git carries everything temporal, because
the committed entry-keyed ledger makes git history a per-debt event
log (birth, restatements, discharge, adjacency — all free).

## Exchange 4 — what stays off the line

Kendrick, on edges: "even if what is owed is accurate, the maintained
edge might not even exist, letting stuff rot. The second big concern
here is that defining that edge means touching many files in order for
it to be accurate. There's an intermediate pivot table-shaped solution
probably, but this is adding more plumbing for.. marginal gain. In
practice it probably isn't worth it over a statement of what needs to
land in a form that is as general as possible, and maybe a conditional
decision that allows the debt to be released if some upstream decision
makes it irrelevant. But that's exactly the kind of thing that an agent
near the max of it's context will shuffle around as free busy work."

Settled against storage, three ways. A dependency edge is a judgment
about relevance — the banned class; only provenance-shaped edges
survive (citations already mandatory in reasons), extracted at read
time. The pivot table died as a hand-maintained mirror of references
already living in reason strings — drift by construction. Stored
release conditions died as predictions: the release path already
exists — a commit removing the marker, citing the decision that
dissolved the debt — so nothing is written in advance to be wrong.
Kendrick had also proposed the change-count landing "as a number in
auto-debt"; refused into a read-mode view instead, because the ledger
must stay a pure function of the tree at HEAD or the mismatch test
loses its meaning (clone-dependent regen, self-referential increment,
polluted compared-content). The busywork worry became a named design
force: every optional marker field is a shuffle surface for a
context-saturated agent, so minimal grammar is an agent-alignment
feature — and the statement-churn count doubles as the busywork
detector, underivable-by-editing because it is derived.

## Exchange 5 — end outcomes, numbering, planning surface

Kendrick: "end outcomes of the debt PAR is that debt-auto becomes the
defacto, with very rare debt.md. you can raise one challenge to the
debt par: if debt.md is always empty and debt-auto has surface for
literally everything, then debt.md has a nebulous role period. ... a
plan can read out as a planning session where debts are numbered
somehow as order to resolve. that's a pretty cheap planning session
that can be tuned as we go. ... but the other important outcome here is
that the debt PAR becomes the true planning surface."

The nebulous-role challenge landed in PAR-0002. The numbering question
split identity from order: identity lives with the debt, order lives
with the plan — a planning session is the read mode's derived default
order, reordered by judgment, landing as a short dated decision citing
IDs; insertion is a one-file edit and markers are never renumbered.
Ordering is a decision, legitimately hand-authored; it is the *list*
that must never be hand-derived again — `PLAN-DISTILL.md`'s leaked
citation-derived work list is the in-repo evidence. Consequence for
the plan apparatus (flagged, not landed): plans keep gates, ordering,
definition of done; they permanently lose the work-list function.

## Exchange 6 — moves, and the failure of derived identity

Kendrick: "the unique codes makes sense and needs to land with some
kind of git discipline; eventually files in the repo are going to move
around and the git unique codes need to properly. If that's likely to
be a failuremode outright there has to be some kind of derived guards."
Then, seeing the guard apparatus: "if theres a ton of failure modes
for it then is there a more accurate way to do it."

Path-keyed identity has four failure faces under moves: move reads as
discharge-plus-new; lineage resets, corrupting the age columns;
references dangle; plan citations orphan. The derived-guard package
(byte-identical-reason joins, follow-chains, a moves-travel-alone
commit discipline) was proposed and then killed on the repo's own
doctrine: its accuracy depended on commit hygiene the machinery cannot
enforce — a convention rather than a test, the state PAR-0002 forbids.
Identity must be statically decidable: a stored ID. The costs
originally cited against IDs shrank under inspection — allocation needs
no registry (the tree is the registry), and a required opaque token is
not the busywork surface optional prose fields are.

## Exchange 7 — minting, and what breaks (nothing)

Kendrick: "I genuinely don't think theres a ton of downsides to a
unique non-numbered reference just living next to it. ... we can mint
the unique id based on some kind of commit it landed with maybe, or the
one just before? ... but if we're abandoning all the git stuff to begin
with doesn't a bunch of other stuff break too? whats the solution?"

Nothing breaks: git was doing two jobs, and only derived *identity*
was abandoned — every temporal derivation survives, keyed more simply
by a grep-stable token. Commit-based minting died twice over: a commit
cannot contain its own hash (content determines the hash), and the
parent-commit variant lies under rebase and merge while the true birth
commit is derivable exactly as first ledger appearance — storing a
worse copy of what git gives perfectly. Interim conclusion: a random
short token, coordination-free across branches. Sequential numbers
lost here: parallel branches both mint the next integer; PAR-NNNN
survives sequential only because record creation is rare and
single-threaded.

## Exchange 8 — timestamp identity

Kendrick: "I actually think the unique number being the date and second
is better. embeds more information, carries more information when
walking the repo for how long a debt has existed without having to
check against debt auto, and because they're never written at the exact
same time, unique by construction. can write a test so that identical
ids are announced loudly for free too, in the rare case they both land
as a total file rewrite or something."

Accepted, with a stated correction to Exchange 7's principle: the ban
is on storing judgments and derivables, and an authoring timestamp is
neither — a fact about the event, and *not* derivable from git (first
ledger appearance is landing time, not writing time; commit dates are
rebase-mutable). The random token lost to three properties: age
readable at sight while walking the tree, chronological sort free
everywhere, and auditability — a stamp must precede its own landing
commit, so a fabricated stamp convicts itself where a fabricated
random token carries no checkable claim. Pins: UTC, second resolution,
one canonical fixed-width sortable spelling, duplicate ID an
enumeration error, IDs never reused after discharge. Fine print kept
honest: the stamp reads when-stated, not when-incurred — the
debt-creating event remains the milestone declaration (PAR-0002).

## Exchange 9 — hand-written stamps, trust-but-verify

Exchange 8 had pinned tool-minting (the hand-written stamp read as the
copy/hallucination surface). Kendrick reversed the workflow cost
mid-build: "for the tool minted thing we probably want that to be
pretty cheap for agents to do. if the standing instructions are like...
write the file, then get the line, then call the sieve.debt new cmd,
then check it landed properly, it gets messy. lets have it be the agent
can write the time and trust it'll do it right until it doesn't, and
verify with the test as stated, and maybe include a test for like,
malformed or omitted times, or nonsense times, or newly minted times
that are outside of a plausible period (might catch on debts that are
updated as things go though)."

Adopted: the agent writes the stamp; placing a marker stays a
one-touch edit. The mint command dies (a stamp-printing helper stays
possible as convenience, never required). Trust is bounded by three
guards: malformed, omitted, or nonsense stamps (invalid calendar,
pre-repo-epoch, future-beyond-slack) are enumeration errors — the
near-miss-is-error pattern; the duplicate-ID test as stated, now also
covering hand-written round-number collisions; and the
plausibility-window audit against landing time applied only to
first-appearing IDs — Kendrick's own caveat in the quote, since a
restated marker keeps its original stamp and must not trip a
freshness check.

## The drafts-dismissal supersession

The universal surface's stub records mechanically resemble the
drafts-as-worklist proposal PAR-0002's first Challenges entry records
Kendrick dismissing. The supersession runs on the dismissal's own
terms: "the argued necessity for any kind of todo list is argument for
a more exacting debt system" — this session is that system arriving.
What keeps a stub from being a draft is the anti-smuggling rule mapped
from placeholders: a placeholder never invents a signature, so an owed
stub never contains rationale prose — any argument typed into it would
acquire authority by existing. The stub carries the marker, its
citations, and nothing else.

## Close

Wrapped 2026-08-03 at Kendrick's call, context-bound mid-build. The
argument above is complete; the build landed through the v2 machinery
commit (rule v2 code, both surfaces, stamps swept, ledger v2, suite
green). The unlanded remainder is stated where it belongs, not here:
the dissolution of DEBT.md's entries into stubs is a DEBT.md entry;
the read layer is a DEFERRED.md entry with its trigger. Task 4's
yield was record text only (the verbatim-citation convention in
PAR-0002's "The line, and the history"); tasks 5 and 6 are the
deferred read layer and its first planning decision.
