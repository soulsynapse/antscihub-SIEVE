# Session record — 2026-08-02 — the runbook gap

Status: Frozen
Date: 2026-08-02

Curated primary for PAR-0003. Opened with the problem named and the
answer nebulous by its author's own statement; the design argument
closed the same date at Exchange 6, with PAR-0003 rewritten to the
settled design and the design debt discharged. Frozen at that close —
a deliberate wrap, not a reflex of the last decision landing. The
acceptance judgment, when convened, files its own primary (precedent:
`SESSION-2026-08-02-par-0002-acceptance.md`). Doctrine: PAR-0001.

## Exchange 1 — naming the problem: the missing how-to layer

Kendrick, verbatim:

> "one actual challenge for the PAR system that would be good to address
> right now: architecture.md holds the settled synthesis, PAR holds the
> why, but nothing adds in the derived-and-tested runbook(s) of the
> system PAR speaks to. Tightening up what ARCHITECTURE.md explicitly
> points to could be handy, but I think this lands as concretely outside
> of what PAR is. There are a bunch of ways to meet the rationale, some
> deliberately stated, but how execution in the repo should respect the
> rationale is left to the reader. I think the next, extremely clear
> step, is to have a new PAR detailing the system to codify how to pass
> the information about how agents and people should improve, use, or
> otherwise leverage the benefit the system exists to provide. As
> rationale, this is improving on PAR *specifically* to close the
> diataxis loop: Agents and people can pick up tutorials from convention
> within the repo, PAR holds the explanation and reference for working
> in the repo directly. The last item is the how-to guides. For clarity,
> the answer to this is nebulous; I'm only naming the problem, so this
> is debt to be resolved, with a draft PAR pointing at why it needs to
> exist, which is this session."

The agent's assessment, compressed. The diataxis mapping is right, and
the strongest evidence for the gap is that the layer already exists de
facto as orphans — `README.md`'s mismatch runbook and `AGENTS.md`'s
Procedures are how-to guides living where they landed, which under the
granularity rule is what "no named system" looks like; naming the system
is recognition, not invention. The central design tension is
"derived-and-tested" against the anti-bureaucracy invariant: a runbook
is hand-maintained state about a tree that moves — PAR-0002's drift
failure — so the design must find how much of a runbook can be derived
or verified without the verifier itself becoming bureaucracy.

Candidate directions held open, deliberately undecided here:

- Runbook steps that are literally executable — commands the suite or a
  smoke script actually runs, so drift reds something.
- Runbooks rendered from tests rather than written beside them — the
  test tree as the source of truth, the guide as a derived view.
- Hand-authored prose whose *pointers* are verified, the way marker
  reasons point at governing sections — cheapest, weakest.

One boundary caution, also open: if the layer lands well it will tempt
absorbing the tutorial convention; task-oriented ("I need to do X now")
versus learning-oriented must stay a drawn line or the diataxis
distinction collapses in the implementation.

Executed this sitting: PAR-0003 drafted `Proposed`, recording only what
is decided — the system exists and is anchored; it is outside PAR;
its purpose is closing the diataxis loop — and naming the rest open.
Design debt filed in `DEBT.md`, since `Proposed` alone carries hardening
debt but not design debt.

## Exchange 2 — the name and the heuristic (design session, first sitting)

Kendrick, verbatim, opening the design session:

> "First: renaming runbook -> how-to. This is adopting the diataxis
> terminology directly, and pattern matches deliberately; better for
> agentic work. Thoughts?"

The agent's assessment, compressed. For: the record already defined the
layer by its diataxis role, with "how-to guides" as the referent and
"runbooks" as the gloss — the rename stops using the gloss as the name;
"how-to" is the accurate superset (the stated purpose is how-to breadth,
"runbook" names the layer after its narrowest member); and "runbook"
primes the SRE incident-response genre, misrouting an agent asking
"where do I learn to do X." Against, the position that lost: "runbook"
carries the stronger *executable* prior — SRE culture treats runbook
automation as the goal state — while stock diataxis how-to guides are
hand-authored prose with no verification implied, so the rename trades
away the one prior pointing at the derived-and-tested constraint.
Resolved: the discipline is carried by the record and the machinery,
not the noun; the name's job is routing consumption.

Kendrick, verbatim, settling it:

> "how-to is the form and I agree with adopting the stance that
> anything that can be a script should be a script as a governing
> heuristic."

Two decisions land. **The name is how-to**; "runbook" is retired
wholesale — no subgenre survival — since a two-tier vocabulary (a
how-to layer containing runbooks) reinstates the unqualified-name
ambiguity the rename kills. Frozen records and this file's name keep
the word; retirement bars reuse, not history. **The governing heuristic
for the derivation-and-test discipline: anything that can be a script
is a script** — which adopts Exchange 1's first candidate direction
(literally executable steps, so drift reds something) as the default,
demotes the other two to the residue for what genuinely cannot
execute, and answers the traded-away prior above: the executable
discipline the old name gestured at is now doctrine, so the name is
free to do routing.

Surfaced in passing, deferred by Kendrick ("can surface it later if
necessary"): `AGENTS.md`'s never-reuse-a-retired-name rule cites no
governing record — a possibly unfiled gap, parked here.

Still open after this sitting: the form (per-system guides or a tier
of their own), the home, the residual discipline for the prose
remainder, and Exchange 1's boundary caution against absorbing the
tutorial convention.

## Exchange 3 — home and form: the hand-written guide, not the script

Kendrick settled the home in a sentence — "how-to is a top level
folder, that way someone looking at the repo can see how it's
organized" — and the agent proposed a form: scripts only, `how-to/*.py`,
task-named, logic-free, docstring residue, import-and-pointer
verification as the floor, no `.md` residents. The position lost
whole. Kendrick, verbatim:

> "Nope, and the reason is the constraints and purpose: how-to has to
> be human-legible, agent-legible, and trusted. The eventual goal is to
> have some kind of marker in the yaml of the howto where you can spawn
> a sonnet session and tell it what to do and check extremely tightly
> scoped to the content of the how-to without having to hand-craft the
> context specifically. Give it commands to run, how to run it, spawn
> the sonnet session and it just does it. This trivializes much of the
> repo work.. when it works. the how-to folder holds a folder for
> scripts for meta tooling, then any folders necessary to categorize
> the different how-to guides. That's the end goal, not the default
> though: the default is the hand written guide and it is self
> referrential: a how-to exists as a 4 fold distillation: session
> archive made it to the PAR, the PAR made it to the ARCHITECTURE.md,
> and the ARCHITECTURE.md pointed to the how-to. The existence of the
> how-to is the confirmed validity of the implementation of one of the
> PAR outcomes. So something in a PAR with an outcome that it is
> explicitly enables is debt to be paid to ARCHITECTURE.md and the
> associated how-to file. It comes due when the PAR is mostly settled,
> but just like PAR, the how-to is continuously updated, and the sign
> that it's settled is that it's quiet. Within the how-to itself, a
> step can *optionally* be turned into a script, and that can do a ton
> for the validity of the how-to, given that one part can be automated.
> But a how-to is not a script by default."

The agent's assessment, compressed. The scoped-agent runner reframes
"derived-and-tested" better than derivation did: the how-to is a
program whose interpreter is an agent — not derived from the tree, but
testable by execution, drift redding as a failed run rather than
accumulating silently; scripts are steps compiled down for determinism
where determinism is available. That makes the runner the layer's
verification story, not a convenience — `DEFERRED.md` material with
that stated as what's at stake. One pressure-test survived and was
agreed (Exchange 4): existence proves the chain was walked once, not
that it stays valid, and "settled when quiet" is ambiguous for a
how-to in a way it is not for a PAR — a PAR goes quiet when doubts
stop arriving; a how-to can go quiet from neglect, and
quiet-under-use versus quiet-from-neglect look identical in the file.
Runs are the disambiguating signal, a second reason the runner is
load-bearing. Smaller notes: YAML frontmatter is a new form in a
plain-`Status:`-line repo, justified because the runner contract needs
structured fields, and scoped to this layer; the scripts folder must
be visibly not-a-category; category folders emerge when a second
resident forces them, never pre-drawn.

## Exchange 4 — three rulings: the debt's home, the bar, the fallback chain

Kendrick, verbatim:

> "for reference, the debt for the howto lives in the architecture
> file, not the PAR. that's the separation of responsibility fyi. and
> also the collision is not a collision, stating something 'should' be
> something is defined by how useful it would be to automate it, not
> something that must be built automatically. until it crosses that
> bar, why make the script? but when various repo tasks become so
> standard that theres speed to be gained by following the script,
> then yeah, it should be. agree on your point on the pressure test.
> but notice the fallback here: how-to is good, you don't need
> architecture. architecture is good, you don't need par. par is good,
> you don't need session. that's by design."

Three rulings. **The how-to debt is `ARCHITECTURE.md`'s to state, not
the PAR's** — separation of responsibility: the PAR holds why, and
what its outcomes are owed downstream is the synthesis surface's
business. **Exchange 2's heuristic is defined, not contradicted**:
"can be a script" reads as "has crossed the utility bar" — a repo task
standard enough that following a script gains speed — a human-judged
tipping point like friction confirmation and template owing, not a
capability trigger. The agent had read the heuristic as
capability-triggered and named a collision with "optionally"; the
ruling dissolves it by definition rather than reversal. **The fallback
chain is the design**: how-to good → architecture unneeded;
architecture good → PAR unneeded; PAR good → session unneeded — the
walking path extended to a task-oriented tier 0, read deeper only
until convinced, which is also what bounds the staleness cost of the
agreed pressure-test: a bad how-to degrades to a walk down one tier,
never to being stranded.

Raised by the agent at this exchange, open pending ruling — the
marker mechanics under PAR-0002's grain: the text surface keys
`(path, <file>)`, at most one marker per file, so `ARCHITECTURE.md`
literally carrying the how-to debt class means a second simultaneous
owed how-to is the grammar-extension pressure PAR-0002 names — and
simultaneity will be the common case with fourteen stub records
coming. Two candidate mechanics: extend the marker grammar to a
multi-marker text form (stamps are already unique, so `(path, stamp)`
keys exist); or state each owed how-to as a stub file in `how-to/`
under placeholder doctrine — the placeholder is the debt entry — with
`ARCHITECTURE.md`'s pointer landing in the same commit, keeping the
responsibility architecture-side and the grain untouched.

## Exchange 5 — the grain disputed, and its provenance traced

Kendrick, verbatim, on the one-marker-per-file grain:

> "whoa, one marker per file? that's nutty, that was never the intent,
> I think you swept that up from your own inference FYI."

And, separately, on the form:

> "and yeah we don't have to have yaml frontmatter, follow repo
> convention"

The second ruling is simple and lands: how-to files use the repo's
plain column-0 line convention, no YAML frontmatter; the runner
contract's structured fields, when they arrive, are plain lines like
`Status:` and `Owed:` are. Exchange 3's note treating frontmatter as
justified is superseded.

The grain, traced. It is not this conversation's inference: PAR-0002
states the text surface as "exactly one form: a column-0 line ... at
most one per file, keyed `(path, <file>)`," `debt.py` enforces it —
every column-0 `Owed:` line becomes an entry keyed `(path, <file>)`,
so a second line in one file is a duplicate key and an
`EnumerationError`, suite red — and PAR-0002's `DEBT.md` passage
builds doctrine on it ("the surface's one-marker-per-file grain means
a second simultaneous entry is the grammar-extension pressure the
Outcomes name, arriving structurally"). But the provenance supports
the suspicion one level up: the grain entered as a *consequence* of
the keying choice — file paths as the only stable anchor unstructured
text has, heading-anchored keys rejected for churn — and the primary
(`SESSION-2026-08-03-debt-md-marker-form.md`) records it as a limit
"named rather than hidden," spun as doctrine agreeing with itself,
with no verbatim ruling choosing one-per-file as intent. An inferred
structural consequence was doctrinalized without the human's words
anchoring it. That the trace is possible is the record system working;
that it was needed is a caution the system should keep: curated
primaries can launder agent inference into doctrine wherever a passage
carries no quote.

Candidate resolution, pending ruling (ruled Exchange 6): marker rule
v3 — the text surface admits multiple markers per file, keyed
`(path, stamp)`.
Stamps are already each entry's identity, globally unique by enforced
rule, and designed to survive rewording and relocation, so the
stable-anchor argument that produced the grain is satisfied without
it. Costs, per PAR-0002's own coherence-rewrite doctrine: PAR-0002
rewritten whole and reviewed as a diff, `debt.py` and its tests, the
ledger's pinned rule version, the "states one debt" wording in
`README.md` and `AGENTS.md`, and `DEBT.md`'s second-entry tripwire
restated (a nonempty `DEBT.md` is already the pressure signal; the
structural tripwire was the grain's contribution and retires with
it). Sequencing: the extension gates the first *exercise* of the
how-to debt class in `ARCHITECTURE.md`, not the close of this design
session.

## Exchange 6 — v3 ruled; the conventions; the index simplified

Kendrick, verbatim:

> "v3 is fine as long as it all works. I want to quickly knock out
> some back and forth on convention for how-to so you have all the
> context. first, how-to's main folder has a script folder in it, and
> it has other folders. any how-to has to live in one of them, and
> they're organized by domain.. sieve work, repo work, split on the
> major seams defined in PAR. the how-to main folder has a generated
> file that walks the folders by the how-to's nesting, not the folder
> nesting. each how to has some kind of automatically represented
> position in a hierarchy, random for now, as debt for later if
> wanted, ideally in a nested list that makes sense but again not
> important for the initial par. how-to's are referenced in the
> architecture when they exist, and there must be a test for that.
> format of how-tos are tbd, but they're written defensively to
> resist stagnation and to be broadly accurate, and when found to be
> inaccurate, cheaply updated on the spot to avert the error. again,
> written to not need fixing."

And, after the agent asked how "random" position should render:

> "when i say random, since they're going into folders where they
> belong, just walk the folders and alphabetical is fine"

Settled here. **Marker rule v3 is ruled in, conditionally** — "fine
as long as it all works"; it stays gating work, not doctrine, until
it lands green. **The conventions**: `how-to/` holds a scripts folder
(meta-tooling, visibly not a domain) and domain folders split on the
major seams the PARs define — sieve work, repo work; every how-to
lives in exactly one domain folder, so the folder set is closed under
the seams. **The index**: one generated file in `how-to/`, the read
surface, walking the domain folders alphabetically — the second
message supersedes the first's stated-position idea, so the index is
a pure function of the tree with no hand-stated fields; a position
hierarchy is deferred debt if ever wanted. The full ledger pattern
applies: never hand-edited, regenerated in the commit that changes
what it reflects, mismatch-tested so staleness reds. **The reference
test**: every how-to is referenced from `ARCHITECTURE.md`; the
agent's grammar refinement stands as the coherent reading — every
reference either resolves to an existing how-to or is stated as an
`Owed:` marker, since under Exchange 4's placement an unresolved
reference *is* the debt class's legal state; dangling either
direction without a marker reds. **The form doctrine**: individual
how-to format TBD, but written defensively — broadly accurate at an
altitude that resists stagnation — and repaired on contact when
found inaccurate: the mismatch discipline applied to prose, with the
fallback chain bounding what defensive vagueness costs.

Proposed by the agent, unconfirmed, held as a candidate only: a
folder-seam conformance check (a how-to's domain folder derivable
from its cited PAR's seam). Flagged for acceptance judgment, not
decided here: PAR-0004's second challenge names this design session
as its resolution point — whether the template convention folds into
the how-to layer.
