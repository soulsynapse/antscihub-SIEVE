---
status: current
reviewed: 6596d13
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
derived is here: six rules, the decisions that closed its open questions, four
ordering constraints, and how a rule leaves this file.
Where a remembered enumeration and a rule disagree, the rule wins.

The same precedence governs what was written before this date. A `docs/todo/`
item or a `docs/SETTLED.md` row older than 2026-07-29 that disagrees with a
rule below is an instruction from the architecture being reworked: the rule
wins, and the item is rescoped when it is *taken*, not preemptively. A settled
row stands until the completed entry that re-decides it overturns it by name
(`overturns:` in that entry's frontmatter) — until that entry lands, the row is
still how the code works, and an item that is not part of this rework must
still obey it. There is deliberately no work list here: it is the exception
lists plus `docs/todo/`, and `docs/.state.md` renders the frontier and the item
DAG from frontmatter. A step table re-added to this file would be the
derivation rot this paragraph replaced.

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

**Gate:** `gui-computes-nothing` in `.importlinter`, landed 2026-07-29 — the
GUI may not import computation; seven exceptions, shrink-only.

**R2. What can be declared can be run — or is refused by name.** Every spec
the contract can express either executes through the one path or is refused
by name in `_bind`. A declarable field with no runnable kernel and no error
message is a defect worse than an absent field. Kernel signatures extend when
the filter that needs one arrives — `MergingKernel` proved the extension
additive — and detection *is* the arrived case for windowed and
table-emitting execution; do not wait for a filter the current protocol makes
impossible to write. (Rule 6 turned inward: the contract must not look more
runnable than it is.)

**Gate:** OPEN — the declarable-shape walk (item `declarable-but-not-runnable`),
which also closes the unnamed `emits` refusal in the same commit rather than
declaring it as a gap.

**R3. The spec declares facts; everything derivable is derived.** Never
declare — or fuse into one flag — what is a function of things already
declared: warmup follows from a filter's own parameters, a chain stage from
spec properties, cache *policy* from the declared facts plus verification.
Declare only the genuine residue (τ, the settling epsilon), and declare it as
a field a test can read, never as a docstring sentence. A declared copy of
derivable state will drift, and that drift is this document's origin story.
(Rule 3 generalized: nothing enumerates what the graph already knows.)

**Gate:** OPEN — the two-start-point property test over `discover()`
(item `warmup-is-derived-not-declared`), with a shrink-only unverified set.

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

**Gate:** half landed — `gui-computes-nothing` is the placement half for
computation. The duplicated-literal half is OPEN (item
`a-filter-id-spelled-twice`), aimed at registered filter ids and declared
column names, deliberately not at every string: a generic two-layer literal
detector would seed an exception list the size of the codebase, which is
enumeration rot re-encoded in Python.

**R5. Every value is exactly one of: parameter, product, view state.** A
parameter changes what a result *is* and is hashed. A product is what a
filter emitted, addressed by its key — and the moment anything downstream
depends on a drawn value, it is a product and its producer is a filter. View
state is where the user is looking: never saved, never hashed, never an input
to a result. Nothing straddles, and no value gets a second representation
anywhere. (Rule 7's identity line reaching every value — including the ones
that decide what is claimed as an event.)

**Gate:** OPEN — first the spec-channel partition (item
`the-spec-has-three-channels`: every `FilterSpec` field in exactly one of
identity / execution / presentation, and a presentation edit provably moves no
cache key), then pyright once the buckets exist as types. The partition is
also the honest gate for "core carries no GUI policy": `primary_params` is a
field, not an import, and no import contract can see it.

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

**Gate:** OPEN — pyright, once the four types land (item
`four-numbers-four-types`), which must precede anything fitted or measured.

## Enforcement

The rules bind through CI or they do not bind.

- **R1, R4 (landed 2026-07-29):** `gui-computes-nothing` in `.importlinter` —
  `gui` imports no computation (`core.wavelet`, `core.detection`,
  `sieve.detect`) — with the seven current violations as an exception set that
  only shrinks: `unmatched_ignore_imports_alerting = error` fails a stale
  entry, so deleting the code and deleting its exception are one edit, and
  *adding* an entry is a reviewed widening of the rework itself. **The
  exception list is the work list**; no prose table of what moves where.
  "Core carries no GUI policy" is a field, not an import, and its honest gate
  is the spec-channel partition under R5's Gate line.
- **R2:** a test that walks the declarable spec fields and asserts each
  either executes or is refused by name.
- **R3:** a property test over `discover()` — run each filter from two start
  points, require agreement within its declared epsilon past its derived
  warmup.
- **R4:** the existing AST instrument, re-aimed narrowly — registered filter
  ids spelled outside their own module, declared column names spelled in two
  layers — never at every string (see R4's Gate line for why).
- **R5, R6:** pyright, once the buckets and the four quantity types exist.

The GUI needs no rule of its own: with every transform a filter (R1), every
value bucketed (R5), and no second spellings (R4), what remains for `gui/` is
rendering values and emitting intents — painting, layout, undo, Qt threading,
view state. Everything else it currently holds is on the exception list.

## Decided — the open questions, closed (Kendrick, 2026-07-29)

- **Channel, not intervals.** The detection filter emits a per-frame channel;
  intervals are derived downstream, and the deriving step is the natural
  table emitter. The uniform frame-shaped contract holds, the fold composes,
  and the kernel signature widens to `Mode.WINDOWED` plus a declared channel.
  R1's falsifier is answered; the kernel-protocol work is unblocked.
- **Presentation is a declared channel on the spec, visibly non-hashed.**
  Captions, signal labels, `primary_params`, and `FilterSpec.cost` — one
  answer for all four. The filter author declares them beside the parameters
  they describe; any front end reads them; "visibly non-hashed" is a test
  result (a presentation edit moves no cache key), not a claim.
- **Incremental ratchet on main.** CI green and the app runnable at every
  commit. The execution side lands per item against the old schema; the
  saved-graph changes land in one migration commit with staged demolition
  around it. No rework branch: the doc and CI machinery only help while they
  are live, and this repo is its second rewrite precisely because the first
  one's constraints were prose.

## Ordering constraints

Four are load-bearing: R6's types land before anything is fitted or
measured, or the fits are redone; the saved-graph changes land as one schema
migration, not four; the channel-versus-intervals answer lands before the
kernel signature it decides (now answered — see above); and **the GUI/CLI
parity check lands before the migration commit, not after it**. The
migration's failure mode is a plausible frame — a synthesized crop node in the
wrong coordinate space, a span node off by the lead-in — and the parity diff
is the only instrument that can see it. Landed afterwards, it can only
confirm that both front ends agree about the same wrong thing.

## How a rule leaves this file

A rule graduates when its **Gate:** line names something that exists and the
shrink-only list behind it is empty. Graduating means the rule's sentence
folds into the `docs/ARCHITECTURE.md` rule it strengthens — the parenthetical
at the end of each rule above says which — through that rule's own falsifier
process, and leaves this file. Nothing automates the move; the gate only makes
readiness visible. When the last rule has graduated, this file flips
`status: current` → `record`, is dated, and is never edited again. That is the
intended end state: this document is scaffolding, and scaffolding that
outlives the building is the failure it was written about.
