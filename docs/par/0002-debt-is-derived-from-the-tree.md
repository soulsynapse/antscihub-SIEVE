# PAR-0002 — Debt is derived from the tree

Status: Accepted
Date: 2026-08-01

## Outcomes

What this system looks like working as intended (stated 2026-08-02,
while marker rule v1 covered only the Python surface; primary:
`SESSION-2026-08-02-debt-advance.md`): `DEBT-AUTO.txt` is the de facto
debt surface — everything owed, in any tracked format, enumerates into
it, and `DEBT.md` is very rare: its steady state is empty, and a
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

### Three files, three authorships

`DEBT.md` and `DEFERRED.md` are hand-authored and live at the repo root:
"they sort adjacent in a root listing, and an agent lists the root first."
`DEBT.md` holds present debt no in-tree marker can carry — a last resort by
the invariant, not a general-purpose list. The last resort reaches exactly
as far as derivation cannot (2026-08-02): a real gap the tree can neither
carry as a marker nor compute is hand-stated here, because every
alternative — a work list, a roadmap, a record filed as its own todo — is
hand-maintained state describing a tree that moves independently of it,
the drift this record exists to kill. Felt necessity for any such list is
therefore an argument for a more exacting debt system, never for a
parallel mechanism (primary: `SESSION-2026-08-02-distill-worklist.md`).
`DEFERRED.md` holds not-yet-due intentions, each with the trigger that
makes it due.

The automatic ledger is its own file, `DEBT-AUTO.txt`, marked `-text` in
`.gitattributes`: "Whole-file byte compare, no delimited-region integrity
question, no mixed hand/machine authority in one file." The alternative
considered was a generated region inside a hand-authored file, and it fails
on all three counts at once. The `-text` pin is not cosmetic — without it,
`core.autocrlf` rewrites the bytes the mismatch check compares and reds the
check on a clean Windows clone.

None of the three is called "the ledger" unqualified. They differ in who
writes them and what a change to one means.

### Marker form rule v1

The form is statically decidable, and that is the requirement it exists to
satisfy: a marker convention the enumerator cannot see is a convention
rather than a test, which is the state the design forbids.

The canonical import is `from sieve.debt import Owed` at module top level,
no alias. The canonical statement is `raise Owed("<reason>")` where the
argument is "exactly one static string literal" — adjacent-literal
concatenation folds at parse and is fine; f-strings are not literals and
are out of form. The literal requirement is what makes the reason
comparable bytes at enumeration time rather than a value that only exists
at runtime.

There are exactly two canonical positions, corresponding to the two things
a placeholder can be: (a) the sole statement of a function or method body
after its optional docstring — the signature-quoting form; (b) the final
statement of a module whose only executable top-level statements are the
docstring, the canonical import, and the raise — the behavior-only form,
which raises on import. "A module is never both: a module-level raise would
make quoted signatures unreachable."

Entries are keyed by "(repo-relative POSIX path, qualified name — dotted
qualname for callables, `<module>` for module-level)", never by line
number, so edits above a marker cannot churn its entry. The reason text is
the compared content, so "a reworded reason renders as *changed*, which is
real signal (the debt's statement moved, the debt didn't)." A duplicate key
is an enumeration error and never a silent merge, because "one marker per
scope is the grain of 'this scope is owed.'"

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
error. Class-body markers are not in v1 — if they are ever needed that is
an additive v2, which is why the rule version is pinned inside the ledger.

### The instruments, and why there are two of them

The enumerator is the static instrument: a library function taking a root
path, walking `.py` files, AST-matching rule v1, returning canonical
entries. Because the root path is a parameter, its own tests run against
fixture trees rather than assuming the live repo; the default roots and
exclusions are one definition, consumed by both the tests and the regen
command.

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

The sentinel is one known marker in a test-fixture directory that the
enumerator must always find, failing the suite if it finds zero there.
"Without it, a dead enumerator regenerates an empty ledger and passes
vacuously — 'no debt' and 'monitor broken' must be distinguishable." It is
excluded from the default enumeration roots so it never appears as live
debt.

The ledger format is "a published interface consumed by git history" and
inherits the file-format discipline of `DESIGN-SESSION.md` Exchange 1
wholesale: additive-only evolution, a removed name never reused, and the
enumeration rule's version recorded in the ledger "so rule churn is
distinguishable from debt movement." Entries are sorted by path then
qualified name, UTF-8, LF.

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
  `DEBT-AUTO.txt`, and the answer is correct by construction rather than by
  anyone's diligence. Nothing has to be remembered at commit time except
  running the regen, and forgetting that reds the suite.
- Debt movement is legible in git history at entry granularity, which is
  what makes the ledger a published interface rather than a report.
- A reworded marker reason is a ledger change. Later distillations that
  repoint marker reasons from `DESIGN-SESSION.md` exchanges to `PAR-NNNN`
  will therefore render as `changed` entries and travel with a regenerated
  ledger — the anticipated case, not a defect.
- Known accepted gap: `--doctest-modules` imports module-form placeholders
  outside the adapter's collection path and reds the suite loudly.
- Marker form rule v2 is anticipated and additive (class-body markers are
  the known candidate). It supersedes this record, which carries forward
  everything it keeps; the rule-version pin in the ledger is what keeps the
  two distinguishable in history.
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
  `SESSION-2026-08-02-distill-worklist.md`.

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
