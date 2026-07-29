---
status: current
reviewed: 7fb6f89
subjects:
  - src/sieve/core/filter_base.py
  - src/sieve/pipeline/executor.py
  - src/sieve/backend/dispatch.py
  - src/sieve/bench/budgets.py
  - .importlinter
---

# REWORK — the rules

Distilled 2026-07-29. The diagnosis this came from — the residue tables, the
bucket taxonomy, the fifteen-step order — is in git
(`git log -- docs/REWORK.md`, versions before this date). It is kept out of
this file deliberately: every enumeration of *what moves where* is a
derivation, derivations held in prose rot (several of that draft's
file-and-line facts were wrong within a day of writing), and the enforcement
section below makes the machine hold the work list instead. What cannot be
derived is here: six rules, two open questions, three ordering constraints.
Where a remembered enumeration and a rule disagree, the rule wins.

None of this replaces the eight rules in `docs/ARCHITECTURE.md`. Each rule
below strengthens one, and the parenthetical says which.

## The rules

**R1. Everything that touches the footage is a filter.** Any transform of the
footage, or of anything derived from it — crop, span, the temporal step,
detection — is a filter: one module and one markdown, discovered, its
parameters hashed into identity, backend-dispatched, cached, refusing up
front. Identity is not exemption: "no crop" is a full-frame ROI, never
`None`; an absent transform is the identity value of a present parameter, so
no `X | None` propagates through the plan. (Rule 1 widened past the word
*frame*: the one execution path computes everything derived from the footage,
not only frames.)

**R2. What can be declared can be run — or is refused by name.** Every spec
the contract can express either executes through the one path or is refused
by name in `_bind`. A declarable field with no runnable kernel and no error
message is a defect worse than an absent field. Kernel signatures extend when
the filter that needs one arrives — `MergingKernel` proved the extension
additive — and detection *is* the arrived case for windowed and
table-emitting execution; do not wait for a filter the current protocol makes
impossible to write. (Rule 6 turned inward: the contract must not look more
runnable than it is.)

**R3. The spec declares facts; everything derivable is derived.** Never
declare — or fuse into one flag — what is a function of things already
declared: warmup follows from a filter's own parameters, a chain stage from
spec properties, cache *policy* from the declared facts plus verification.
Declare only the genuine residue (τ, the settling epsilon), and declare it as
a field a test can read, never as a docstring sentence. A declared copy of
derivable state will drift, and that drift is this document's origin story.
(Rule 3 generalized: nothing enumerates what the graph already knows.)

**R4. One name, one home — and the home is the layer that owns the deciding
fact.** The test for `core` is agreement, not purity or convenience: would
two independent implementations have to agree on this to interoperate? (The
second implementation is not hypothetical — it is this codebase across a
version boundary and, under rule 8, any reader of what SIEVE wrote at rest.)
Shared by dependency but not by agreement sits *mutual*, below both
consumers, not in core. A name spelled in two layers is one bug with two
cures — promote it into the shared vocabulary or eliminate one spelling — and
a string literal duplicated across a layer boundary is the AST-checkable
smell. Derived quantities live with the fact that decides them: a fold's
combining rule belongs to whatever fixes the execution strategy, or it is
correct only for the sequential case. (Rule 7's discipline applied to names
and placement.)

**R5. Every value is exactly one of: parameter, product, view state.** A
parameter changes what a result *is* and is hashed. A product is what a
filter emitted, addressed by its key — and the moment anything downstream
depends on a drawn value, it is a product and its producer is a filter. View
state is where the user is looking: never saved, never hashed, never an input
to a result. Nothing straddles, and no value gets a second representation
anywhere. (Rule 7's identity line reaching every value — including the ones
that decide what is claimed as an event.)

**R6. A number carries its dimension and its provenance.** Media time (on
rational fps), wall time, work units, and frame counts are four types with no
implicit conversion; work units are anchored to one reference operation, held
relative to it with no per-filter measured coefficients, and never wear a
time-flavored name. A ceiling is denominated in the dimension of what it
bounds — user-perceived latency in wall time, algorithmic cost in work units
— which makes the algorithmic budgets machine-independent and CI-gated, and
moves wall-clock verification to a calibration job that does not gate. Every
displayed quantity says whether it was measured or predicted and against
which machine profile; an uncalibrated machine yields work units that say so
— never someone else's constants, and never a dispersion that shrinks with n
into a point estimate wearing a quantile's name. (Rule 6 applied to
quantities: a number must never look better-founded than it is.)

## Enforcement

The rules bind through CI or they do not bind.

- **R1, R4:** forbidden contracts in `.importlinter` — `gui` imports no
  computation (`core.wavelet`, `sieve.detect`), `core` carries no GUI policy
  — with current violations as an exception set that only shrinks. **The
  exception list is the work list**; no prose table of what moves where.
- **R2:** a test that walks the declarable spec fields and asserts each
  either executes or is refused by name.
- **R3:** a property test over `discover()` — run each filter from two start
  points, require agreement within its declared epsilon past its derived
  warmup.
- **R4:** the existing AST instrument, re-aimed at literals duplicated across
  a layer boundary.
- **R5, R6:** pyright, once the buckets and the four quantity types exist.

The GUI needs no rule of its own: with every transform a filter (R1), every
value bucketed (R5), and no second spellings (R4), what remains for `gui/` is
rendering values and emitting intents — painting, layout, undo, Qt threading,
view state. Everything else it currently holds is on the exception list.

## Undecided — needs an answer, not a step

- **Channel or intervals.** Does the detection filter emit a per-frame
  channel (uniform contract holds, intervals derived downstream) or intervals
  directly (a node whose output is not frame-shaped)? This is R1's falsifier,
  and it decides the kernel signature — answer it before widening the
  protocol.
- **Presentation hints.** Captions, signal labels, and `primary_params` are
  one question, not three: filter-owned, not interop vocabulary, so R4 alone
  does not place them. Either a declared presentation channel on the spec or
  they stay in the GUI — decide once, for all of them together, and check
  `FilterSpec.cost` against the same answer.

## Ordering constraints

Only three are load-bearing: R6's types land before anything is fitted or
measured, or the fits are redone; the saved-graph changes land as one schema
migration, not four; the channel-versus-intervals answer lands before the
kernel signature it decides.
