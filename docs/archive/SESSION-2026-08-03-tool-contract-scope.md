# Session — the tool contract's scope

Status: Frozen
Date: 2026-08-03

The sitting that scoped PAR-0007 before drafting it whole. Kendrick and
Claude (Opus 5). A first draft existed early and was cut down rather than
extended; what follows keeps the positions that lost, because three of
them lost to arguments worth having on record.

Kendrick is quoted verbatim. Exchanges are numbered for citation.

---

## Exchange 1 — The surface had grown, and what the rationale is for

The finding that opened the sitting. Exchange 5's rebuilt tool is
`Params` + `lower` + `view`. Since then PAR-0005's Consequences route two
further declarative surfaces to PAR-0007 — the equivalence spec
(comparator, tolerance, target statistic) and a convention that a tool
declares the guarantees it voids — and `DEFERRED.md` holds a third, how a
tool declares what it consumes. Five members where the design's headline
was one file and no compiler tax.

Claude's first answer was a **graded contract**: exactly one mandatory
member, and any other admitted only if it carries an always-correct
default, mirroring `Opaque` in the algebra and the naive evaluator in the
executor. Kendrick redirected:

> "I think this PAR is one of the clearest ones that must exist, and the
> one we have to be careful about scoping. However, the most important
> part of the contract is what it *doesn't* own, since it is able to own
> so much. That barrier, and how it's enforced, is this entire PAR."

Accepted, and it displaces the graded contract as the spine. Everything
the draft argued separately — purity, the missing preference argument,
ops as values — is one boundary seen from different sides.

## Exchange 2 — The adversarial pass, and what it killed

A skeptic review was run against the first draft. Its findings, and their
dispositions:

- **The admission rule is a convention with no test**, in a repo whose
  doctrine is "make it a test, not a convention" (Exchange 6's catalog
  rule got one; this did not). *Held* — and it contributed to the rule
  being cut in Exchange 4.
- **`view`'s "always-correct default" is asserted.** Rendering an
  arbitrary array by type is *possible*, not *correct* — a normalization
  has to come from somewhere, and Exchange 4's honesty constraint already
  ruled that a misleading display is a defect in an instrument selling
  interpretability. Since `view` was the only member the admission rule
  actually bound, the rule bound nothing. *Held.*
- **Optionality is the wrong medicine for the stated patient.** Prompt
  6's worry was *"an agent would write spaghetti code every time."* A
  human under pressure omits; an agent handed a base class with five
  members implements five, including an equivalence spec it has no
  measured basis to state — the declares-itself-correct pattern arriving
  through a member admitted for the contributor's benefit. *Held*, and it
  implies that optional members must not be discoverable from the base
  class, which the draft never said.
- **`PLAN-DEBT-ORDER.md`'s next-session block hand-maintains derivable
  status** — that PAR-0006 and PAR-0007 are Proposed is a `grep` away.
  Against the anti-bureaucracy invariant, in the same working tree that
  cites it. *Held, unfixed at close.*
- **What breaks if PAR-0007 is never written?** The one-file invariant
  keeps its plan-gate citation and README keeps Exchange 1's, both
  accurate today. *Answered by Exchange 10*: the rationale is what makes
  the invariant true rather than asserted, and the invariant is a
  detector with no stated cause without it.

## Exchange 3 — The delivery unit, and a wrong turn

> "I don't think there are too many worlds where the tool lands in a
> single file either as a result. Most operations are built out because
> of the tool. The tool can call them but doesn't own them, but a tool
> isn't complete without its operations."

Claude took this as a claim about the delivery unit and proposed
rewording the one-file invariant from files to **edits** — three new
files and zero edits being perfect conformance, one new file plus an edit
to the renderer being a violation. Evidence offered: v1's pipeline needs
a z-score, a wavelet bank, change energy, a threshold, a block reduction
and a detector, and only a couple are expressible in ops that would
already exist.

**This position lost in Exchange 10** and is kept because the error is
instructive: it conflated *the feature landing* with *the feature
running*.

## Exchange 4 — The scoping filter

Kendrick, on the rationale being written with no tools in existence:

> "I do also agree that no tools means this is adjudicating an empty room
> here. So before the rest of it exists, the form it needs to exist in
> *before the tool and the operations exist* is the form that prevents
> mistakes that cause rewrites or letting tools be written with too much
> stuff. The initial form is about preventing mistakes. It'll grow into
> exactly what it owns once the tooling actually lands."

Settled as the admission test for v1: **a claim belongs now only if
getting it wrong later costs a rewrite or a store migration.** You cannot
adjudicate what a tool owns with no tools, but you can enumerate one-way
doors, because those are properties of the contract's shape rather than
of its content.

Cut by the filter, with reasons: the graded-contract admission rule from
Exchange 1 (governance, purely additive, and unenforceable per Exchange
2); `view`'s default (making a member optional later is additive, and the
claim rested on an undrafted PAR-0013); the equivalence spec as an
admitted member (additive). Retained as a one-paragraph refusal rather
than an argument: the voiding declaration.

The distinction the filter draws, stated because it will be attacked:
speculative-and-cheap-to-fix goes out, speculative-and-expensive-to-fix
goes in. The test is not whether a claim is ahead of evidence — all of
them are, at n=0 — but what being wrong later costs.

## Exchange 5 — `lower` challenged, and kept

Kendrick: *"what the hell is lower I've been meaning to ask."*

It is compiler jargon inherited from Exchange 5 of the design session —
LLVM and MLIR lower through passes, Halide lowers an algorithm to a
schedule, a query planner lowers logical to physical — and Exchange 3
borrowed that whole frame, so the verb came with it. It names the one
thing a tool does: params in, description out, one direction, with
nothing reconstructing the tool from the ops.

Argued against on three grounds: the contributors are behavioral
scientists and agents rather than compiler people; `lower(self, p)`
parses in English as "make p lower," the opposite of a description-
returning function; and its partner `view` is plain English, so the pair
is inconsistent in register. The rename window is also one-way — a
retired name may never be reused, so it costs one placeholder edit and
two marker rewordings today and a migration plus a burned name after the
first tool.

Candidates priced. **`emit`** — good verb, one-directional, standard in
codegen; killed by Qt, where `emit` is the signals keyword and the GUI is
two panes. **`plan`** — collides with the planner the design insists does
not exist. **`recipe`** — taken by the intent side; PAR-0006 uses "what
belongs to the recipe" for params. **`graph`** — accurate but overloaded,
since the pipeline is also a DAG. **`ops`** — recommended: a noun, so it
cannot be read as executing; names its product, restoring symmetry with
`view(p, out) -> View`; and puts the barrier in the signature, since a
tool supplies *ops* and a *view*, neither of which it owns.
**`request`** — runner-up, and the design's own word (Exchange 6: "steps
request from the executor," provided requests are declarative); held back
because it reads as RPC to anyone arriving from web work, and a name
connoting a call is a poor guardrail against the one thing a tool must
never do.

Ruled: *"lower is fine, I'll get used to it."*

## Exchange 6 — Tool / Step / Task

Claude had listed the three names as a one-way door, on the ground that a
retired name may never be reused. Kendrick:

> "A step is a name for a thing that lives on the pipeline.. it's mostly
> what the user is going to call it, for better or for worse. An author
> in the repo isn't going to call it a step, they're going to call it a
> tool. Task isn't picked up by anyone except maybe by the executor?"

Conceded: the names were spent in July and are already load-bearing
across the tree, so restating them decides nothing and fails Exchange 4's
filter. What survives is not naming but scope — **the Tool is the only
object with a contract** — because `pipeline.py` will hold Steps as data
and an agent reading `ARCHITECTURE.md` sees three nouns of equal weight.

## Exchange 7 — `consumes`, and the question behind it

> "I feel like a tool/step/task declaring something it can consume kinda
> makes sense, what's the argument against it?"

Claude conceded the framing was wrong. The design rejected declarations
three times — the random-access flag, a lowering's declared output type,
the catalog entry's claim — and in each case the defect was that the
declaration was a *second copy* of a fact existing elsewhere with nothing
checking the copy. A declaration is only dangerous when it can disagree
with something. `consumes` has nothing to disagree with, because
`lower(self, p)` receives no inputs; calling it a flag was a category
error.

The real question is therefore **`lower`'s arity**, which is a one-way
door where `consumes` is not: an argument added after tools exist
rewrites every tool, a declaration added later is additive.

Settled: `lower(self, p, inputs)`, inputs **typed and non-inspectable**.
Typed, so eligibility is a static read off the signature — Exchange 6's
third condition requires ineligible tools shown greyed *with the missing
requirement named*, before params are filled. Non-inspectable, so a tool
cannot pattern-match its upstream and emit differently, which is planner
work inside a tool and the thing an agent writes when asked to make a
tool efficient.

Refined immediately against a v1 counterexample PAR-0006 already cites —
the frequency bank capped at `0.45*fps` inside
`core.wavelet.default_freqs`, a param default computed from a property of
the input, which strict opacity makes unwritable. The cut that survives
both: **a handle exposes properties of the value — shape, fps, dtype —
and never its history.** Inspection of what a value is, never of how it
was made.

A related settlement, carried from the draft and unchallenged: `lower`
returns a graph with named outputs rather than a single op, forced by
Exchange 2's tracker offering trajectories *and* masks as two ports both
always present. A single op is the one-node case.

## Exchange 8 — The swap, and a system with no home

> "Inputs opaque and typed is.. mostly fine, except in the swapping case,
> when you have 2 different methods for one operation, they have to have
> a unified parameter or the swapping isn't free and the user has to
> reset all the parameters every time they try to"

The objection lands on params, not inputs — opacity neither helps nor
hurts a swap. But the need it names is larger than the UX symptom: **the
harness cannot pose its own question without a correspondence between two
methods' param surfaces.** "Is DIS equivalent to Farneback" is undefined
unless you can say at what configuration, so without the mapping an
equivalence measurement compares two arbitrary points and reports a
number about nothing. Exchange 8's behavioral clustering has the same
dependency.

Kendrick then widened it past method swapping:

> "auto swapping between levels is also exposed by this, such as
> interchange between a downsample of 4x and a block size of 4"

That case is neither an implementation choice nor a param mapping: it is
a measured equivalence between *graph shapes*, outside what PAR-0005
permits silently, and only ever offered rather than taken. v1 evidences
both that it is real and that the state of the art is avoidance —
PAR-0006 cites `block_size` deliberately tracking scale rather than
moving with it, separability engineered by hand because interchange had
no home.

The shape it must take: a canonical param space **per operation, never
global**, with each method declaring a map into and out of it. Pairwise
translation is N² and produces the twelve-near-identical-variants failure
Exchange 6 describes; a global vocabulary is Exchange 7's
unchangeable-algebra failure at n=0. A knob that does not map is a
finding — the methods are not swappable at that setting — surfaced rather
than silently dropped.

Filed as **PAR-0019 — Configuration interchange**, stamp
`20260803T065949Z`, inserted into `PLAN-DEBT-ORDER.md` after PAR-0012 and
PAR-0011 because its first question is the seam against them.

## Exchange 9 — Provenance of the one-file rule

Asked where the invariant came from. It originates as prose in Exchange
5's rebuilt contract — "if adding a feature ever requires touching a
second file, the architecture has failed" — became a numbered invariant
only when `ARCHITECTURE.md` was written up after the design session
closed, and was amended once by `PLAN.md`'s Phase 1 gate on 2026-08-01,
narrowing "feature" to "tool" because the original was false for field
types, view layers and migrations. Nothing with rationale authority has
ever governed it. The noun had been examined once; the unit never.

## Exchange 10 — The reword loses, and the recolor

> "Yeah, adding a feature is one file. That doesn't change. You wrote the
> feature; the tool; you can call it; it won't run and the back end will
> error but the feature lands, probably with a boatload of debt, which is
> the entire purpose of the debt system."

Exchange 3's position falls. The tool file *is* the feature; it lands
complete; everything it names that does not exist is owed elsewhere with
its own marker and its own governing rationale. Incomplete-but-landed is
the designed normal state. The current wording already covers the case
the reword was aimed at — "anything the tool needs that doesn't exist is
declared, not reached for" is exactly the ROI field type — and the reword
would have converted a working mechanism into a blocker, making crop
unshippable until field types have a home.

Then the hardened form, and the general claim:

> "The actual hardened form of this is that you can edit one file and *in
> theory* you will have enacted change that is enough for the feature to
> at minimum be scaffolded. It doesn't pre-suppose the dependencies are
> present. I don't think there are any problems other than the invariant
> is just the responsibility separation rule in a different color"

Accepted, and it is the sitting's central result. Touching a second file
happens exactly when another module owns a piece of the feature — the
renderer knowing tool identity, a registry owning registration that
should be derived, the executor holding per-tool knowledge. **The file
count is not a rule; it is the symptom by which a misplaced
responsibility announces itself.** As a delivery-completeness claim the
invariant is false; as a detector it is exact, which is why it survived
being attacked.

Three consequences. PAR-0007 does not restate the one-file rule — it owns
the responsibility boundary, and the file count is how a violation
surfaces. The invariant keeps its wording and gains a rationale it never
had (Exchange 9), which answers Exchange 2's "what breaks if this is
never written." And the rationale gains the test the skeptic pass said it
lacked: if adding a tool requires editing something that already exists,
name what that module owns that belongs to the tool.

**Finding, in-tree and unresolved at close**: `kernel.py` raises `Owed`
at module top level, so a tool doing `from sieve.kernel import Resample`
dies at import rather than at run — it never enters the derived registry
and cannot be listed greyed. "You write the tool, it lands, the backend
errors" is therefore unobservable in the tree today. Kendrick's "in
theory" concedes this is about the placeholder form rather than about the
rule. The split it implies: behavior nobody imports may raise at import;
vocabulary a tool must name has to be importable and raise on use. Filed
against PAR-0002, stamp `20260803T072353Z`.

## Exchange 11 — Where a method's params live

Claude proposed partitioning a tool's `Params` into measurement fields
and a method sub-model, justified by migration cost, with the test being
whether a field would mean anything to a different implementation of the
same operation — a temporal window would, `dis_preset` would not.
Kendrick redirected:

> "If the ops say what they need, and swapping between equivalents is
> owned by the tool, then passing those ops to the GUI representation as
> a pass-through for the tool lets ops be swappable, which means that
> adding a method means adding an op, and.. what, the equivalence
> arbitration has them grouped? or maybe it's just like a one line
> addition to the tool itself?"

Resolved by separating two things both called *method*. Two
implementations producing statistically equivalent output are two
implementations of **one op** — the user never learns which ran, the
recipe does not change, selection is by measured cost. Two methods that
answer differently are **two ops** — different descriptions, different
numbers, the choice authored and hashed. Farneback/DIS/RAFT are the
second kind, which PAR-0006 already ruled.

Both arrive as one file, by Exchange 10's rule: if adding RAFT means
editing the flow tool, the flow tool owns knowledge about RAFT.

The one-line-in-the-tool option was rejected: it is a registration list,
and registration lists are what derived registries exist to delete.
Grouping is the generic function, membership earned by measurement.

On an op stating its own GUI — automatic yes, bespoke no. An op's params
imply widgets through the existing field-type mechanism; an op shipping a
widget or a layout is the erosion path Exchange 5 named, where a bespoke
visualization is a two-hour job against the vocabulary's two-day one and
possible-therefore-preferred is how a closed vocabulary dies.

**Claude's partition proposal loses to a cheaper one.** If ops own their
params there is no partition, because the method's fields were never in
the tool's model; they live on the method, in the method's file. The
tool's params stay flat and carry only what survives a method swap. This
dissolves rather than obeys PAR-0006's "hash over effective params" rule:
with no fields in the wrong model, no inert field survives to be
excluded.

What it genuinely requires, and the reason the question mattered: the
config pane must compose the tool's params **with the selected op's
own**, rather than walking the tool's alone. That is PAR-0013's, and it
comes due at the first tool offering a choice rather than at the first
tool.

---

## Settled

- The spine is the responsibility boundary; the one-file property is its
  symptom, not its content, and PAR-0007 does not restate it (1, 10).
- v1 admission test: a claim belongs now only if being wrong later costs
  a rewrite or a store migration (4).
- `lower(self, p, inputs)`; inputs typed and non-inspectable; handles
  expose properties, never history (7).
- `lower` returns a graph with named outputs, forced by the design
  session's two-port tracker (7).
- No preference argument; the absence is the enforcement (PAR-0006).
- Ops live outside the tool module; the operation is a different file
  because it is different debt (10).
- Method params live on the method; the tool's params hold only what
  survives a swap (11).
- Grouping is the generic function; nothing is appended to a tool when a
  method lands (11).
- An op declares field types, never rendering (11).
- `lower` keeps its name, with the rename window closing at the first
  tool (5).
- The Tool is the only object with a contract (6).
- The voiding declaration is declined and handed back to PAR-0005; the
  equivalence spec stays routed but unadmitted (4).

## Open at close

- PAR-0007's judgment, by attack, with PAR-0006 argued first.

## Closed after the exchanges above

- The placeholder-form split turned out to need no new form. Rule v2
  already has both positions; what was missing was the rule selecting
  between them, which is now PAR-0002's: vocabulary reached for by name
  takes the function-body position, behavior only called into takes the
  module position, and the tell is whether a `from <module> import
  <name>` appears anywhere the milestone reaches. Stamp
  `20260803T072353Z` discharged the same sitting it was stated. Which
  names `kernel.py` exposes stays Phase 2's, since PAR-0005 retired the
  five-shape table and a placeholder may not invent a surface.
- Where non-trivial primitives live stays deferred, and on the sitting's
  own filter rather than on caution: no module path is in a recipe hash,
  so being wrong later costs a file move. Filed to `DEFERRED.md` with
  the trigger and a loosely-held preference for `kernel/` as a package.

- `PLAN-DEBT-ORDER.md`'s next-session block no longer restates derivable
  status; it names the two queries and keeps only the judgment over them
  (raised in Exchange 2).
- "Record" stays the genus and PAR stays Project Architecture Rationale,
  with the distinction stated in `AGENTS.md` rather than swept through
  316 occurrences across eighteen live files — PAR-0001 uses *record* as
  the genus deliberately (rationale records, primary records, stub
  record), so a sweep would have contradicted the rationale that defines
  the tier system.
