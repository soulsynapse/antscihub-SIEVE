# PAR-0002 — Debt is derived from the tree

Status: Accepted
Date: 2026-08-01

## Outcomes

What this system looks like working as intended (stated 2026-08-02,
while marker rule v1 covered only the Python surface; primary:
`SESSION-2026-08-02-debt-advance.md`): `DEBT-AUTO.md` is the de facto
debt surface — everything owed, in any tracked format, enumerates into
it, and it is the only file ever read for present debt, because even
`DEBT.md`'s entries are marker lines that enumerate (2026-08-03).
`DEBT.md` itself is very rare: its steady state is empty, and a
nonempty entry is standing pressure to extend the marker grammar,
never a parallel list. And the debt system is the true planning
surface — work is chosen by ordering ledger entries, derived columns
as the default order and judgment recorded as a dated planning
decision citing entries, so a work list is never hand-derived again.

## Context

**Provenance.** This distills `docs/archive/PLAN.md`: the anti-bureaucracy
invariant stated in its preamble, Phase 2 gate decisions 4, 5, and 6
together with the Phase 2 body that builds on them, and Phase 3's
classification rule. Every decision here was settled 2026-08-01; marker
form rule v1 was narrowed the same day by the Phase 2 code review. The
tier-1 citations it retires are `README.md`'s "the debt machinery, PLAN.md
Phase 2" and "marker form rule v1 (PLAN.md, Phase 2, decision 4)", and
`AGENTS.md`'s pointer at what `PLAN.md` holds. That `AGENTS.md` sentence
also names the layout settlement; the layout is component decomposition
rather than debt machinery, is distilled separately, and this record does
not carry it.

Accepted 2026-08-02 after the fidelity review: every quoted passage
machine-verified verbatim against the source, and the four
implicit-reasoning flags (`SESSION-2026-08-02-record-class.md`, Exchange
10) upheld as written. Review record:
`SESSION-2026-08-02-par-0002-acceptance.md`.

Amended to marker rule v2 the same day: the universal surface, timestamp
identity, and the line-versus-git division, argued in
`SESSION-2026-08-02-debt-advance.md` — v1's whole form carries forward
inside v2, and the ledger's rule-version pin keeps the two
distinguishable in history.

**The problem.** This is a rewrite whose skeleton was placed before its
code, so most of the tree is components that do not exist yet. A repo in
that state has to answer, continuously and truthfully, what it owes — and
the usual ways of answering share one failure. A TODO convention, a status
field, a roadmap section, an issue list: each is hand-maintained state
describing a tree that moves independently of it, so the record and the
reality drift, and the drift is invisible from both sides. Here the answer
is load-bearing rather than informational, because an agent orienting in
this repo decides what to build from what it believes is owed.

The constraint that determines the shape of the answer is stated in the
source as a review criterion over the whole conformance plan:

> Every hand-maintained record in this plan is either a decision or an
> intention; everything derivable from the tree is derived. Anything
> expressible as a marker goes in the tree; the hand-authored present-debt
> file is a last resort. The moment any step requires a human to maintain a
> record the tree can derive — a status field to update, a report to
> refresh, an exemption to adjudicate — that is bureaucracy arriving, and
> it announces itself as exactly that shape.

The invariant also limits itself, and the limit is part of the decision
rather than a hedge on it:

> Checked at the Phase 4 conformance pass like everything else, by judgment
> rather than mechanically — deliberately, because a mechanical
> bureaucracy-detector would itself be bureaucracy. This invariant is a
> review criterion and claims to be nothing more.

Everything below follows from applying that invariant to debt in
particular. If the tree can be made to carry the debt, then nobody
maintains a record of it, and the drift problem does not arise because
there is nothing left to drift.

## Decision

### A placeholder is its debt entry

A component the named milestone reaches but that has not been built gets a
real module at its real import path whose body raises `sieve.debt.Owed`.
That module is not a stub standing in for a debt entry recorded elsewhere;
it *is* the entry. Presence in the tree is the authorization — there are no
status fields, no `authorized` flags, no metadata anywhere saying whether a
placeholder is sanctioned.

This is the move the whole system rests on. Because the debt lives in the
tree, the ledger of debts is a function of the tree, and a function of the
tree is computed rather than maintained.

The exception is `sieve.debt.Owed`, and the naming was deliberate: "the
plan's own vocabulary, grep-distinctive, and deliberately not an `-Error`
name because a marker is not a fault and should not pattern-match visually
to real exceptions." A placeholder firing is the system working.

A placeholder carries "only signatures that are quotations from the settled
record — `lower`, `view`, `render`/`sweep`, the five shape signatures —
never inventing one; where only behavior is settled (the store, GUI
internals, the pipeline loader), the docstring points at the governing doc
section instead of presenting an API surface." The prohibition matters more
than it looks: an invented signature is a design decision smuggled into the
tree as scaffolding, where it acquires authority by being typed out and
gets built against before anyone notices it was never decided.

### What counts as debt

> a placeholder is type-1 present debt iff the named next milestone reaches
> through it. Every other component gets a type-2 not-yet-due entry with a
> trigger and **no file in the tree**. The debt-creating event is the
> milestone declaration, not the file placement; placement makes
> already-existing debt enumerable.

The final clause is the load-bearing one. Debt is created by committing to
a milestone that needs a component, not by writing a file — so placing a
placeholder discharges nothing and removing one hides rather than settles.
It also fixes the boundary between the two hand-authored files: everything
the milestone does not reach is an intention with a trigger, and it gets no
file, because a file for an unreached component would be debt the repo does
not actually owe.

The rule generalizes past components (2026-08-02): the debt-creating
event is a governing declaration — the named milestone for code, the
distillation mandate (PAR-0001) for rationales — and placement makes
the already-existing debt enumerable, whatever the surface. A settled
system owed its rationale gets a stub record at its own number carrying
only its status line, its marker, and the citations that govern until
acceptance — never rationale prose. The prohibition is the same one
placeholders carry: an invented signature is a design decision smuggled
in as scaffolding, and prose typed into a stub would acquire authority
by existing. This supersedes, on its own terms, the drafts-as-worklist
dismissal recorded in Challenges — what was dismissed was a new
mechanism beside the debt system; what lands here is the more exacting
debt system the dismissal itself asked for.

### Three files, three authorships

`DEBT.md` and `DEFERRED.md` are hand-authored and live at the repo root:
"they sort adjacent in a root listing, and an agent lists the root first."
`DEBT.md` holds present debt with no better file to carry its marker — a
last resort by the invariant, not a general-purpose list. The last resort
reaches exactly as far as placement cannot (2026-08-02): a real gap that
belongs to no ownable file is hand-stated here, because every
alternative — a work list, a roadmap, a record filed as its own todo — is
hand-maintained state describing a tree that moves independently of it,
the drift this record exists to kill. Felt necessity for any such list is
therefore an argument for a more exacting debt system, never for a
parallel mechanism (primary: `SESSION-2026-08-02-distill-worklist.md`).
And the last resort is a location rule, not a format exception
(2026-08-03): an entry here is itself a column-0 `Owed:` marker line
under the text surface, so it enumerates like everything else and
`DEBT-AUTO.md` stays the only file ever read for present debt. The
surface's one-marker-per-file grain means a second simultaneous entry is
the grammar-extension pressure the Outcomes name, arriving structurally
(primary: `SESSION-2026-08-03-debt-md-marker-form.md`).
`DEFERRED.md` holds not-yet-due intentions, each with the trigger that
makes it due.

The automatic ledger is its own file, `DEBT-AUTO.md` (named
`DEBT-AUTO.txt` until format-version 3, 2026-08-02), marked `-text` in
`.gitattributes`: "Whole-file byte compare, no delimited-region integrity
question, no mixed hand/machine authority in one file." The alternative
considered was a generated region inside a hand-authored file, and it fails
on all three counts at once. The `-text` pin is not cosmetic — without it,
`core.autocrlf` rewrites the bytes the mismatch check compares and reds the
check on a clean Windows clone.

None of the three is called "the ledger" unqualified. They differ in who
writes them and what a change to one means.

### Marker form rule v2

The form is statically decidable, and that is the requirement it exists to
satisfy: a marker convention the enumerator cannot see is a convention
rather than a test, which is the state the design forbids. Rule v2
(2026-08-02) carries all of v1 forward and adds two things: identity, and
the universal surface. Statically-decidable is also why identity is
*stored* rather than derived: the alternative — rename detection over
reasons plus a moves-travel-alone commit discipline — made identity
accurate only while everyone behaved, a convention the machinery cannot
see (primary: `SESSION-2026-08-02-debt-advance.md`, Exchange 6).

**Identity.** Every marker's reason opens with its statement stamp: the
UTC time the debt was stated, second resolution, one canonical
fixed-width spelling — `YYYYMMDDTHHMMSSZ` — followed by `: `. The stamp
is the entry's identity: it survives relocation and rewording, so a
moved marker is `moved` in the entry diff rather than a discharge plus
a new debt, and per-entry git history is one grep-stable token. It is
also the minimum priority signal carried on the line — age readable at
sight, chronological sort free everywhere. Stamps are hand-written at
statement time and trusted until a test says otherwise (Exchange 9 —
tool-minting made placing a marker a ceremony): a malformed, omitted,
or nonsense stamp (invalid calendar, before the repo epoch 2026-08-01,
future beyond slack) is an enumeration error; a duplicate stamp
anywhere under the surface is an enumeration error, never a merge; and
stamps of newly landing entries are audited against first ledger
appearance where git history exists — a stamp cannot postdate its own
landing, so a fabricated one convicts itself. A discharged stamp is
never reused. Two honest edges are named rather than hidden: the stamp
reads when-*stated*, not when-incurred — the debt-creating event
remains the declaration — and markers whose shared statement event
gives them one wall-clock second (a skeleton commit, an enumeration
restated as several entries) disambiguate by incrementing seconds in
entry-sort order, a recorded artifact of uniqueness, not a claim about
sub-second history.

The canonical import is `from sieve.debt import Owed` at module top level,
no alias. The canonical statement is `raise Owed("<stamp>: <reason>")`
where the argument is "exactly one static string literal" —
adjacent-literal concatenation folds at parse and is fine; f-strings are
not literals and are out of form. The literal requirement is what makes
the reason comparable bytes at enumeration time rather than a value that
only exists at runtime.

There are exactly two canonical positions, corresponding to the two things
a placeholder can be: (a) the sole statement of a function or method body
after its optional docstring — the signature-quoting form; (b) the final
statement of a module whose only executable top-level statements are the
docstring, the canonical import, and the raise — the behavior-only form,
which raises on import. "A module is never both: a module-level raise would
make quoted signatures unreachable."

Which of the two a placeholder takes is not a style choice. It follows
from whether anything must import a *name* out of the module. Vocabulary
that is reached for — an op constructor a tool emits, a view layer, a
field type — takes form (a), because form (b) raises before the name can
be bound, so every importer dies at import rather than at use: a tool
naming an unbuilt op would never be scanned into the derived registry,
never appear in the picker, and never reach the backend error the debt
system exists to produce. Behavior that is only called into — an
evaluator, a store, the GUI — takes form (b). The tell is whether a
`from <module> import <name>` against the placeholder appears anywhere
the milestone reaches. This is a placement rule, not a third form; both
positions are v1's and the enumerator already keys them apart by
qualname.

**The universal surface.** The file universe is the git index — tracked
files plus untracked-not-ignored, so a marker is visible to regen before
its first commit — which makes universality definitional rather than
maintained: a new file or format is covered the moment git would take
it, and the exclusion list is `.gitignore`, maintained anyway, rather
than a hand-listed walk. Python files are the AST surface, rule v1's
two positions unchanged. Every other file that decodes as UTF-8 is the
text surface, with exactly one form: a column-0 line
`Owed: <stamp>: <reason to end of line>`, at most one per file, keyed
`(path, <file>)` — mirroring the module form, because file paths are
the only stable anchor unstructured text has (heading-anchored keys
lost: heading text is mutable content and churns like line numbers).
A column-0 line opening `Owed:` that fails the form is an enumeration
error; the word elsewhere is prose. Reasons are read under universal
newlines and stored LF-clean, so checkout line-ending style cannot make
two clones enumerate different bytes. Three named boundaries, not
leniencies: files that do not decode as UTF-8 are outside the text
surface; the automatic ledger and the sentinel root are machinery, not
surface; and `docs/archive/` is excluded outright, because a frozen
file can never be edited, so a frozen enumeration error would be
permanent — the frozen tier states no live debt by definition. The
dynamic instrument remains Python-only, and the asymmetry is stated:
text markers cannot fire, so they are enumerator-only.

Entries are keyed by "(repo-relative POSIX path, qualified name — dotted
qualname for callables, `<module>` for module-level)", never by line
number, so edits above a marker cannot churn its entry — and identified
by their stamp, which is what the entry diff joins on across
relocations. The reason text is the compared content, so "a reworded
reason renders as *changed*, which is real signal (the debt's statement
moved, the debt didn't)." A duplicate key is an enumeration error and
never a silent merge, because "one marker per scope is the grain of
'this scope is owed'"; a duplicate stamp is the same error one level
up, because one stamp is the grain of one debt's history.

Anything that references the name and fails the form — non-literal reason,
non-canonical position, aliased binding — is "an **enumeration error, never
a skip**." So is an unreadable or unparseable file under an enumerated
root, with parseability defined by the pinned interpreter, "because a
skipped file makes debt vanish while both the mismatch test and the
sentinel stay blind to it." Every leniency in an enumerator is a way for
debt to disappear quietly.

The reason string's internal shape — what is owed, and a pointer to the
governing section — is left as convention: "a grammar here would be the
anti-bureaucracy invariant tripping on itself."

The narrowings recorded from the Phase 2 code review are part of v1. Any
statically visible reference to the name `Owed`, canonically bound or not,
is held to the rule — "the name is vocabulary, reserved repo-wide under the
enumerated roots." Qualnames flatten `<locals>`, and shadow collisions
surface as loud duplicate-key errors. Canonical positions are reached
through `def`/`class` nesting only, so a marker under `if` or `try` is out
of form. Reasons are LF-only; any other line boundary is an enumeration
error. Class-body markers remain out of form — if they are ever needed
that is an additive v3, which is why the rule version is pinned inside
the ledger.

### The instruments, and why there are two of them

The enumerator is the static instrument: a library function walking the
git index by default, AST-matching the Python surface and line-matching
the text surface, returning canonical entries. Because explicit roots
can be passed in place of the index walk, its own tests run against
fixture trees rather than assuming the live repo; the exclusions are
one definition, consumed by both the tests and the regen command.

The conftest adapter is the dynamic instrument. A test-tree marker raises
the same exception as everything else — "one syntax, one enumerator key" —
and the adapter converts it to a pytest skip carrying the debt as its
reason, so the suite stays green and the debt shows up in the skip summary.
The adapter also checks membership against a fresh per-session enumeration:
a caught marker present in it skips, one absent from it fails, named as a
marker the enumerator cannot see. The enumeration is fresh rather than read
from the checked-in ledger so that "staleness is the mismatch test's alarm,
form-nonconformance is the adapter's; one cause, one alarm."

Two instruments rather than one because they fail differently and check
each other: "the sentinel guards against the enumerator dying, the
membership check guards against markers raised in forms the enumerator
can't see."

The sentinel is one known marker per surface in a test-fixture directory
that the enumerator must always find, failing the suite if it finds zero
there — a Python marker and a text-form marker, so a dead scanner on
either surface is distinguishable from that surface being debt-free.
"Without it, a dead enumerator regenerates an empty ledger and passes
vacuously — 'no debt' and 'monitor broken' must be distinguishable." It is
excluded from the default enumeration so it never appears as live debt.

The ledger format is "a published interface consumed by git history" and
inherits the file-format discipline of `DESIGN-SESSION.md` Exchange 1
wholesale: additive-only evolution, a removed name never reused, and the
enumeration rule's version recorded in the ledger "so rule churn is
distinguishable from debt movement." Entries are sorted by path then
qualified name, UTF-8, LF.

Format-version 3 (2026-08-02) re-serialized the ledger as a markdown
table and renamed it `DEBT-AUTO.md`: the only file ever read for
present debt should render where it is read, so each entry became one
row — path and qualname as code spans, which is also what keeps
`<module>` and `<file>` visible in rendering — with the v2 key's fields
unchanged as columns and reason cells backslash-escaped so parse stays
serialize's exact inverse. This is a versioned break, not additive
evolution; the version pin is what makes it legible, the retired name
and serialization are never reused, and the stamp-landing reader
parses both key spellings and both file names, so history consumers
lose nothing across the break.

### The line, and the history (2026-08-02)

The dividing rule: the marker line carries only what git cannot know —
the stamp (writing time, which git holds only as rebase-mutable landing
time) and the semantics: what is owed, and the governing citation.
Everything temporal is derived, because the committed, entry-keyed
ledger makes git history a per-debt event log: birth is the first
ledger commit containing a stamp, every restatement is a `changed`
entry, discharge is the commit whose diff removes it — which also links
each debt to the exact work that paid it — and all of it is computed on
call, never stored. Nothing history-derived is ever written into the
ledger: the ledger is a pure function of the tree at HEAD, or the
mismatch test loses its meaning (clone-dependent regen, self-referential
counters, polluted compared-content). The suite's checks are
correspondingly static and tree-only; audits that need history — the
stamp-landing check — run where history exists and say so where it
does not.

What stays off the line, deliberately: dependency edges (a judgment
about relevance — the only edges are provenance-shaped, extracted at
read time from citations already required in reasons, which name their
targets verbatim — `PAR-NNNN`, a stamp, a `path :: qualname` — so
extraction is mechanical); release conditions (predictions — the
release path is a commit removing the marker and citing the decision
that dissolved the debt, so nothing is written in advance to be wrong);
and every optional annotation, because each optional field is a shuffle
surface for a context-saturated agent — minimal grammar is an
agent-alignment feature. The statement-churn count doubles as the
busywork detector, and cannot be gamed by editing, because it is
derived.

### The planning surface (2026-08-02)

Work is chosen by ordering ledger entries. The read layer emits the
ledger in a derived default order — age, last-touched, restatement
count — and judgment reorders it; the ordering lands as a short dated
planning decision citing stamps. Identity lives with the debt, order
lives with the plan: markers are never renumbered, insertion is a
one-file edit, and a cited stamp that is no longer enumerated means
exactly one thing — discharged. Ordering is a decision and legitimately
hand-authored; it is the *list* that is never hand-derived again — the
citation-derived work list that leaked two settled systems
(`docs/archive/PLAN-DISTILL.md`) is the in-repo evidence for why.

### Enforcement

The mismatch check is a test in the suite: enumerate, diff against the
checked-in ledger, fail on mismatch. Regeneration is a separate one-command
write mode, and the test never mutates the repo — a self-healing test would
launder every real change into a silent one.

The failure output is the entry-level diff, added / removed / changed, "so
'stale ledger' and 'unintended debt change' are distinguishable at the
point of failure rather than laundered by a reflexive regen."

There is no hook and no CI dependency. "A stale ledger turns the suite red
until regenerated, so the wrong thing is hard rather than discouraged." CI,
if it is ever added, inherits enforcement by running pytest. The residual
gap is named rather than hidden: nothing physically blocks committing on a
red suite, which matches the design's own bar — Exchange 6 asks for hard,
not impossible.

### The machinery class is closed

The `Owed` exception module, the enumerator and mismatch test, the regen
command, the conftest adapter, and the sentinel fixture are real code and
never placeholders, "because it is what gives every placeholder its
meaning." Membership is that enumerated list, "not anyone's judgment that
their code 'is machinery'"; extending it is a placement decision that goes
through the normal loop. A self-declared exemption is the "exemption to
adjudicate" the invariant names as bureaucracy arriving.

## Consequences

- The question "what does this repo owe right now?" is answered by reading
  `DEBT-AUTO.md`, and the answer is correct by construction rather than by
  anyone's diligence. Nothing has to be remembered at commit time except
  running the regen, and forgetting that reds the suite.
- Debt movement is legible in git history at entry granularity, which is
  what makes the ledger a published interface rather than a report.
- A reworded marker reason is a ledger change. Later distillations that
  repoint marker reasons from `DESIGN-SESSION.md` exchanges to `PAR-NNNN`
  will therefore render as `changed` entries and travel with a regenerated
  ledger — the anticipated case, not a defect. The v1-to-v2 stamp sweep
  was the same case at scale, and existing markers' stamps were derived
  once from their placement commits and are pinned bytes thereafter.
- Known accepted gap: `--doctest-modules` imports module-form placeholders
  outside the adapter's collection path and reds the suite loudly.
- Marker form rule v3 is anticipated and additive (class-body markers are
  the known candidate). It supersedes this record, which carries forward
  everything it keeps; the rule-version pin in the ledger is what keeps
  versions distinguishable in history.
- `DEBT.md`'s steady state is empty (see Outcomes): its two entries
  dissolved into the surface — fourteen stub records (PAR-0005..0018)
  and PAR-0003's own marker — landing 2026-08-03. A future nonempty
  entry is stated in marker form and is standing pressure to extend
  the marker grammar; the file's remaining role is the open Challenges
  question below.
- The instruments constrain each other, so neither can be relaxed alone:
  loosening the enumerator's form checking silently widens what the
  adapter's membership check will fail on.

## Challenges

- **2026-08-02 — "The distillation work list can't be derived and the
  debt files weren't carrying it — land every system as a `Proposed`
  stub so `grep -l "^Status: Proposed" docs/par/` derives the list."**
  Raised by the agent after the citation-derived work list proved
  incomplete: two settled systems had no tier-1 citation to enter it
  by. Dismissed by Kendrick — "drafts are a new mechanism btw, and
  aren't necessary, stated debt should be picked up, and the argued
  necessity for any kind of todo list is argument for a more exacting
  debt system." The gap went to `DEBT.md` as an ordinary hand-stated
  entry, the last resort doing precisely its job, and the Decision
  above now states the rule the dismissal articulated. First entry in
  this section, arriving contemporaneously rather than reconstructed —
  the surface working as the no-reconstructed-challenges gate
  anticipated (`docs/archive/PLAN-DISTILL.md`, Phase 2). Fuller record:
  `SESSION-2026-08-02-distill-worklist.md`. Superseded on its own terms
  2026-08-02: the dismissal asked for "a more exacting debt system,"
  and marker rule v2 is it — stub records now carry the owed rationales
  as markers, distinguished from the dismissed drafts by the
  no-rationale-prose rule (see "What counts as debt"; primary:
  `SESSION-2026-08-02-debt-advance.md`, closing section).

- **2026-08-02 — "Work in the file itself that doesn't touch the
  explicit debt line is signal for potential concurrent work that's
  valuable and agent-interpretable, at the risk of overpromoting high
  churn files. But high churn files are high churn because they're load
  bearing and signals something else: over coupling."** Raised by
  Kendrick against a prospective mechanism, before it exists: deriving
  debt priority from git activity adjacent to a marker. The measurement
  is real — commits near a gap are interest being paid on it — but the
  same number scores a defect the debt system does not track: a file
  with too many reasons to change ranks high whether or not its debt is
  the thing in the way. Standing caution, not a dismissal: any read
  mode that ranks by adjacent churn either separates the two readings
  or inherits the conflation. Fuller record:
  `SESSION-2026-08-02-debt-advance.md`, Exchange 3.

- **2026-08-02 — "If DEBT.md is always empty and DEBT-AUTO has surface
  for literally everything, then DEBT.md has a nebulous role, period."**
  Raised by Kendrick at the marker-rule v2 proposal, whose universal
  surface (git-index walk, file-form markers for every tracked text
  format) aims DEBT.md at permanent emptiness. The doctrine above gives
  an empty last resort a meaning — a nonempty DEBT.md is standing
  pressure to extend the grammar — but that meaning needs the file to
  be creatable, not present. Whether an always-empty escape valve earns
  its place in the root listing, or retires until a grammar failure
  recreates it, stands open; resolves on evidence once v2 lands and the
  file's steady state is observed. Fuller record:
  `SESSION-2026-08-02-debt-advance.md`, Exchange 5.
