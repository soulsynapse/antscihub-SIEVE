# Tool contract plan

Scope: the Tool base's first real code, together with the two closed
vocabularies its signatures name. `docs/archive/PLAN.md`'s Phase 3 layout settlement
already made this a single unit — "the five-shape algebra is one design unit
… all five IR classes landing in the change that first needs `Resample`" —
and the change that first needs `Resample` is the one that gives `lower()` a
return type. So this cycle lands `src/sieve/kernel.py`, `src/sieve/views.py`,
and `src/sieve/tools/base.py`, and removes exactly four markers from the
automatic ledger.

Crop is out of scope and keeps its marker; it gets its own cycle, per
`docs/archive/PLAN.md` "After this plan." The executor, the store, the pipeline file
and the GUI keep theirs.

This plan is a map, not a build authorization. Per the working loop each item
inside a phase still gets proposed and confirmed individually before it is
built. Approving this plan settles the *sequence* and the *definition of
done*, nothing else.

Each phase carries its own gate: the decisions that block it, made at that
phase and not before. A phase does not start until its gate is cleared.

## Why the Tool contract and not the pipeline file

`docs/archive/PLAN.md` left the fork open ("likely the pipeline file format or the
Tool base"). It resolves against the pipeline file for one reason: Exchange 1
defines the format's load path as read-dict → migrate → *then validate*, and
defines its conformance test as "one parametrized test over the step
registry." Both halves name a Tool. Building the format first means either
shipping a contract whose validating test cannot be written — the
convention-not-test state Exchange 6 forbids — or stubbing the very contract
this cycle exists to settle. The dependency runs one way: a Step is a Tool
plus filled params, and the file serializes that.

The same objection lands partly on this cycle and is answered in Phase 4: a
Tool base with no tools has an empty parametrized sweep. The difference is
that the base's semantics are complete without any tool existing, whereas the
file format's are not.

---

## Phase 1 — Record amendments

No code. Lands as its own commit, per the chunking rule; regen stays a no-op
because no marker is touched.

**Gate: three findings to confirm or reject.** They are amendments to records,
so they precede everything built on those records.

1. **GUI-in-process trigger — settled 2026-08-01: narrow it to the Tool
   base.** `DEFERRED.md` read "due when: the first real contract code (the
   pipeline file format or the Tool base)." Only the second disjunct bites.
   Exchange 1's conditional is that *if the GUI is a separate process, the
   step declaration is also a wire format* — a claim about where a tool's
   `Params` schema is canonical, not about the file on disk. The pipeline
   file carries parameter values and its migration registry is `dict → dict`
   under either canonicalization. The trigger is narrowed to the Tool base,
   where the canonical form of the `Params` declaration first becomes
   executable.
2. **Eligibility and multiple inputs — settled 2026-08-01: split the gaps.**
   The old `DEFERRED.md` entry called the record "three partial answers, no
   settlement." That was inaccurate: Exchange 7 explicitly settles the
   eligibility rule as "does an applicable method exist for these argument
   types," with the dispatch table as the eligibility check. What remains
   unsettled is how a Tool participates in that rule: Exchange 5's rebuilt
   `lower(self, p)` exposes neither consumed input types nor the requested
   generic function. That bridge remains due at the Tool base's first real
   code. The old entry also combined this with a distinct question — how a
   second input enters the shape signatures — whose earlier trigger is the
   five-shape vocabulary's first real code. The entry is split so each gap
   names what is missing and becomes due where it first bites.
3. **Frozen-plan discovery — settled 2026-08-01: record now, decide at the
   trigger.** Moving frozen plans into `docs/frozen/` would encode lifecycle
   status as a manually maintained location and break load-bearing pointers
   from code docstrings, `README.md`, and `DEFERRED.md`; an index naming the
   live plan would duplicate status already declared by the plans themselves.
   Neither candidate is clean under the anti-bureaucracy invariant, and the
   current flat named layout is still readable. `DEFERRED.md` now records the
   question and both objections. It becomes due when this plan freezes as the
   second frozen planning document, when the current layout first needs
   reassessment.

Exit: the three records say what they mean; suite green; regen a no-op.

---

## Phase 2 — The closed vocabularies

`src/sieve/kernel.py` and `src/sieve/views.py` become real. Both are
declaration-only modules: the five op shapes as an IR, the seven view layers
as a vocabulary. Neither holds an implementation of anything — no resampler,
no renderer.

**Gate (four decisions):**

1. **What a shape instance *is*.** Exchange 5's example is
   `Resample(scale=(1, 1/p.factor, 1/p.factor))` — the op is the shape,
   parameterized. So `Resample` is a constructor over coordinate maps, not a
   base class for a library of resamplers. Confirm that reading, and confirm
   that "the kernel is the set of primitive operations" in `ARCHITECTURE.md`
   describes a wider thing than `kernel.py` holds.
2. **Where non-trivial primitives live**, given (1). A `Resample` needs no
   implementation module because the coordinate map *is* the op; a `Fold`
   tracker plainly does. Nothing in the record places that module. Likely
   outcome: a `DEFERRED.md` entry triggered by the first `Fold`- or
   `Window`-shaped op, not a decision here.
3. **How a second input enters the shape signatures** — recorded as unpinned
   in `kernel.py`'s docstring and in `DEFERRED.md`. It becomes due here and
   not at crop, because the layout settlement lands all five shapes together
   and `Fold`'s signature is being written for real. Background subtraction
   consumes frame + plate; Exchange 4 treats it as `Fold`.
4. **`lower()` returns an op *graph*, not an op.** `ARCHITECTURE.md` says
   "params to an op graph"; Exchange 5's example returns a bare `Resample`.
   Whether a single op is a one-node graph or graphs are a separate type has
   to be settled before the shapes are written, because it determines whether
   composition lives in the vocabulary or above it.

Ordering note: vocabularies before the contract, by blast radius. The op
representation feeds the recipe hash the store addresses by, so changing it
later orphans every stored value. That is cost, not corruption — no
git-history semantics here, unlike the pipeline file and the automatic ledger
— but it is the largest blast radius in this cycle.

Exit: both modules import cleanly, the closed vocabularies are complete at v1
with their additive-revision discipline stated in code, the ledger is
regenerated to eight entries, and the suite is green.

---

## Phase 3 — The Tool contract

`src/sieve/tools/base.py` becomes real: the `Params` requirement, `lower()`,
`view()`, and whatever a tool declares about its inputs.

**Gate (four decisions):**

1. **How a tool declares what it consumes** — the entry Phase 1 reworded.
   This is the cycle's hardest decision and the one the record cannot
   arbitrate. It must produce the bridge from op-level dispatch to tool-level
   eligibility, or an explicit declaration on the Tool, or a reasoned
   deferral with a trigger.
2. **`Params` canonicalization: Pydantic as source of truth, or JSON Schema
   canonical with Pydantic as one consumer.** Requires settling whether the
   GUI is in-process with the executor (Exchange 1's open fork). Due here per
   the Phase 1 amendment.
3. **Tool identity.** Exchange 2 makes the Tool "what gets versioned and
   migrated," and Exchange 1 keys migrations `(step_type, from_version)`.
   `schema_version` sits on `Params`; the other half of that key is
   undefined. Whether identity is settled here or deferred to the pipeline
   cycle with a trigger is the decision — but it cannot be left unnamed,
   because a retired identity may never be reused.
4. **What enforces tool purity.** No runtime handle, no I/O, no state outside
   `Params` is the strongest lever in the design, and a plain base class
   enforces none of it. The doctrine is that the wrong thing is made hard
   rather than discouraged, and that enforcement lives in tests rather than
   convention. Which mechanism carries it — structural typing, a base class
   that withholds the wires, a conformance test, or some combination — is
   this phase's equivalent of the classification-by-shape call.

Exit: `Tool` is a real contract; `tools/base.py` has no marker; the ledger is
regenerated to seven entries; the suite is green.

---

## Phase 4 — The contract, tested

**Gate (one decision): what the conformance suite covers now.**
`tests/test_conformance.py` is currently one whole-module marker. Exchange 1's
suite is parametrized over the step registry, and this cycle ships no tools,
so that sweep is empty. The decision is whether the conformance marker splits
— the parts that can run now becoming real, the rest staying owed — or stays
whole until crop lands. If it splits, marker form rule v1 has no class-body
position, so the split has to land as module-level or function-level markers,
or as the additive v2 the rule version anticipates.

Build item, and the reason this phase is not optional: **the contract is
validated against two worked examples before it is called done.** Exchange 6's
catalog rule is that you design an abstraction with two examples in hand,
because the jump from n=1 to n=2 is the difference between deriving a shape
and guessing one. The record already supplies both — crop (Exchange 2) and
downsample (Exchange 5, `ARCHITECTURE.md`) — so the examples cost nothing to
obtain and neither ships as a tool. They live in the test tree, exercising the
contract, the way `tests/_sentinel/` lives there exercising the enumerator.

Exit: the two worked examples type-check and round-trip against the real
contract; whatever the gate decided about the conformance marker is reflected
in the ledger; the suite is green.

---

## Phase 5 — Exit

Final pass against the definition of done. Anything failing it is either fixed
or entered as present debt — a repo that accurately states what it owes is
conformed; one that silently misses a criterion is not.

**Definition of done** (approving this plan confirms this scope reading):

- [ ] `kernel.py`, `views.py`, and `tools/base.py` hold real code and carry no
      marker; `DEBT-AUTO.md` is regenerated in the same commit as each
      removal.
- [ ] Both closed vocabularies are complete at v1, with the additive-revision
      discipline stated where the code is, not only in a doc.
- [ ] Every gate decision above is recorded in this document at the phase
      that made it, in the form `docs/archive/PLAN.md` used — the decision, the
      reasoning, the date.
- [ ] Every question that came due and was *not* settled has a `DEFERRED.md`
      entry with a trigger, or a `DEBT.md` entry if it is presently owed.
- [ ] The Tool contract is validated against two worked examples from the
      record.
- [ ] The anti-bureaucracy invariant holds: no hand-maintained record
      duplicates anything derivable from the tree.
- [ ] Suite green, regen a no-op, working tree clean.

---

## After this plan

Crop's cycle, under its own name. It is where the port-binding UI question
(`DEFERRED.md`, "due when: after crop lands") gets close enough to see, and
where the Params fields `tools/crop.py` calls undesigned surface get designed.

This plan freezes under its name when exhausted, per the doctrine
`docs/archive/PLAN.md` recorded about itself: a successor cycle takes a new name, and
a live contract recorded here migrates out only when it first needs to evolve,
additively, with the v1 record staying put.

## Known risks

- **Four of the five shapes land with no caller.** Crop reaches `Resample`
  only. The layout settlement made this call knowingly — one closed contract
  whose vocabulary arrives together — but it is exactly the n=1 generalization
  failure Exchange 6 describes, at n=0 for four of the five. Mitigation: the
  shapes are signatures, not implementations, so the surface area guessed
  wrong is as small as the design allows; and Phase 4's two worked examples
  put n=2 under the part of the contract that does have callers. This does not
  cover `Fold`, `Window`, `PixelMap`, or `Opaque`, and pretending otherwise
  would be the risk going unnamed.
- **Phase 3's gate is four decisions deep and they interact.** Canonicalization
  depends on GUI topology; identity depends on canonicalization; purity
  enforcement depends on whether `Params` is a Pydantic model or a schema. The
  one-decision-at-a-time loop is the mitigation, but the ordering within the
  gate is itself a call, and if it fragments this phase is the plan's
  serialization point the way Phase 3 was for `docs/archive/PLAN.md`.
- **The empty registry.** Phase 4's answer is worked examples in the test tree.
  If that is judged to be the throwaway-second-caller pattern Exchange 6 warns
  about, the alternative is folding crop into this cycle — which contradicts
  `docs/archive/PLAN.md`'s scope statement and should be decided as an amendment, not
  drifted into.
