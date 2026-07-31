# Invariants, derived from the charter alone

Working note. Derived only from `docs/CHARTER.md` — not checked against the code, and
deliberately so. What the code does may show one of these is already false; that is a
finding about the code, not a reason to weaken the invariant here.

## The test being applied

The charter states its own criterion at §63, defending measurement's status: *"It is
the universal tool that every single part of SIEVE touches, and earns its status as an
invariant."* Two conditions — **universality** (every part touches it) and **existential
load** (violating it removes SIEVE's reason to exist). I add a third the charter implies
but does not state: **checkability**. A property no test can fail on is a value, not an
invariant, and putting it in the constitution teaches agents that constitutional rules
are decorative.

Applied honestly, the charter's stated three do not survive as stated. Not because they
are wrong — the substance is right — but because §55–65 mixes invariants with
requirements, and one of the three swallows the other two.

## The problem with the charter's grouping

§55 declares the DAG an invariant, then lists five things under it: (a) execution,
(b) save/load, (c) component definition, (d) tuning, (e) outputs. These are not the same
kind of claim. (d) is *"fundamentally mostly the GUI"* and invokes the
load→measure→tune→load loop — so invariant 1's fourth sub-item contains both invariant 2
and invariant 3 entire. A decomposition where one member contains the others is not a
decomposition.

(a) fails the discriminating test: *"the pipeline executes and produces outputs"* is the
product. No change can be evaluated against it, because only total breakage violates it,
and that is already caught by having any test at all.

What survives from §55, restated so it discriminates, is below.

---

## I — Closure

**Property.** Anything admitted to the DAG satisfies the component contract by
construction, and the composition of two valid components is valid.

This is §59 taken literally: *"if it reaches the actual DAG, it meets the requirements by
construction."* The word doing the work is *construction* — not "is validated on the way
in" but "cannot be built wrong." The enforcement point is registration and the type
signature, not a runtime check inside the executor.

**Universality.** Every component, every composition, every future component type.

**Existential load.** Without it, each component is bespoke (§16) and the executor
accumulates per-component special cases — which is the present fragility, restated.

**Checkable by.** Registration rejects non-conforming components; no execution path
reaches a component that did not pass registration. The second half is the part that
actually rots, and needs its own test.

**Does not cover.** What a component *does*. Closure is about admissibility, not
correctness or quality. An agent adding a component satisfies this by conforming to the
contract; it does not owe anything further to this invariant.

### I.a — Round-trip fidelity (corollary, but name it)

A saved pipeline reloads to an identical pipeline. §58: *"exactly as useful as the rate
of the redeployment."*

Formally this falls out of Closure — if the contract requires a serializable parameter
schema, round-trip follows. I would still name it separately, because it is guarded by a
different mechanism (a property test over the save/load pair) and a contract can satisfy
registration while quietly failing round-trip on some parameter type. Corollaries that
need their own test deserve their own ID.

---

## II — Attribution

**Property.** Every unit of work has a known cost, attributable to that unit, and
projectable onto hardware other than the machine that measured it.

Three clauses, all load-bearing, and the third is the one that is easy to lose. §63's
claim is not "SIEVE is fast" and not "SIEVE is measured" — it is that SIEVE can tell a
user *whether a detection project is feasible on the machine they have*. A benchmark
that only reports numbers for the dev box (§17) satisfies measurement and fails the
product claim entirely.

Attribution — per-unit, not per-pipeline — is what §28 demands: *"no feedback on where
to improve the code and why."* An aggregate wall-clock number tells you a regression
happened, not where, and so does not discharge this.

**Universality.** Every component; every change to every component.

**Existential load.** Stated outright at §63: without it *"there are other tools to do
what it does."*

**Checkable by.** Registration requires a declared cost characteristic; the bench gate
fails on per-unit regression, not just total; a projection test asserts that estimates
for a target machine profile are produced and are bounded, not that they are accurate.

**Does not cover.** Being fast. This invariant is satisfied by a slow component with an
honest cost model, and violated by a fast one with none. Worth stating explicitly in the
constitution — otherwise it reads as a performance mandate and agents will
prematurely optimize inside it.

---

## III — Responsiveness

**Property.** No unit of work blocks the interactive loop.

The charter files this under measurement — §63's *"When SIEVE freezes parts of its GUI
due to some resource hog... the user experience degrades proportional to SIEVE's
inability to respond to that constraint."* But measuring cost and responding to it are
different mechanisms with different failure modes, and §17 names the absence of dynamic
load balancing as a top-level fragility that then appears nowhere in §55–65. It is a
separate invariant that got absorbed because it shares a cause.

It passes both of the charter's tests independently: every long-running thing touches it,
and §34's user complaint — *"they initiate a crop and then their workspace is laggy"* —
is a product-level failure, not a performance detail.

**Checkable by.** A test that no registered component executes on the UI thread; a
latency budget on the interactive path.

**Scope decision required.** There is a weak form (work is off the interactive thread,
cancellable, and reports progress) and a strong form (execution adapts to observed load —
the dynamic load balancing of §17). The weak form is an invariant the rewrite can hold
from day one. The strong form is a feature with real cost. I would adopt the weak form as
the invariant and treat adaptation as work governed by it, but this is yours to decide
and the constitution cannot be written until it is decided.

---

## IV — Visibility

**Property.** No capability is *silently* unexposed. Every capability the pipeline can
reach is either reachable by the user or visibly marked incomplete.

The charter is sharper here than a first reading suggests. §65 does not demand
GUI-first — it says *"This should not be defined from the outset, but must be detectable
until the loop is closed."* The invariant is not "nothing unexposed"; it is that the gap
between what the pipeline can do and what the user can reach is **enumerable and loud**.
That is implementable, and the stronger reading is not.

**Universality.** Every capability, and every parameter of every component. §43 extends
it: the GUI is itself a contract with the user, so a capability exposed *illegibly* is a
partial violation. That part is not mechanically checkable and should be admitted as
reviewer judgment rather than dressed up with a test.

**Existential load.** §65: *"might as well not exist."* §35 is the live instance — the
author can drive it, a naive user cannot find the entry point.

**Checkable by.** A test enumerating registered capabilities and parameters against those
reachable from the GUI, failing with the unexposed list. That test is also the project's
to-do list, which is the charter's intent.

**Does not cover.** Whether the exposure is *good*. Legibility is reviewer judgment.

---

## V — Single home

**Property.** Every capability has exactly one home, and that home is discoverable from
its package's export surface.

This is §47 — *"when we can, we put everything in its proper home"* — and it is the
charter's actual defense against reinvention. §41's self-announcing toolbags is the
mechanism; the `__init__.py` export surface is where the announcement happens.

I am promoting this to invariant status even though the charter files it under "shape of
the solutions" rather than under §53's invariants, because it passes all three tests:
universal (every capability), existentially loaded (its violation *is* the bespoke-filter
fragility of §16, which is the stated reason for the rewrite), and checkable (an import
test for orphans and duplicate implementations).

**Note the asymmetry it needs.** §41 and §47 welcome new homes freely; §16 and §49 treat
bespoke implementations as the core disease. These pull opposite ways and the constitution
must resolve it. The workable resolution: adding a *thing* inside an existing type is free
and unreviewed; adding a *new type* requires naming the existing type that cannot hold it.
Cheap to extend, slightly expensive to fragment.

**Structural note.** I–IV are properties of the running system, guarded by tests. V is a
property of the repository, guarded by lints and review. The constitution should not blur
these — they fail differently, are enforced by different machinery, and an agent should
know which kind it is violating.

---

## Candidate, pending a scope decision

### No privileged boundary type

**Property.** Sources and sinks are ordinary components; no data type is special-cased at
the pipeline boundary.

§61 is the charter at its least resolved and, I think, its most consequential: *"the shape
of SIEVE right now, which requires a video as an input, is actually a limitation... a well
defined final product may not be limited this way."* The author flags it as vague. The
non-vague version is that inputs and outputs are the same kind of thing — a source is a
component with no input, a sink is one with no output — and once that holds, video stops
being privileged and background subtraction as a pipeline stage stops being a special
case.

If adopted this is a real invariant with teeth, checkable at the type level. If not
adopted, it is a design goal and video-specific handling stays legal. The two produce
materially different component contracts, so it cannot be deferred past the contract
being written. This is the same scope question as the video/generalization item already
open.

---

## Explicitly not invariants

**"The pipeline executes."** The product, not a property. Nothing discriminates against
it.

**"Tuning the pipeline" (§57d).** A requirement. Its invariant content is Visibility plus
Responsiveness; nothing is left over once those two are stated.

**The mirror thesis (§69).** *"The codebase and SIEVE itself organize as a mirror of each
other."* This is the summary and the reason the invariants are the ones they are — but it
is uncheckable, and promoting an uncheckable claim to constitutional status is the exact
mechanism by which the constitution becomes decorative. It belongs at the top of the
constitution as its preamble and stated intent, with no ID and no Check field.

---

## What is still blocked

Two of these cannot be finalized without decisions already outstanding:

- **III** needs the weak/strong responsiveness call (is adaptation in this rewrite).
- **Candidate** needs the video-generalization call.

**I** additionally depends on what the component contract actually says, which is the
document these invariants are meant to govern — so expect one revision after the contract
is drafted, and expect that revision to be Closure's Check field getting more specific,
not the property changing.
