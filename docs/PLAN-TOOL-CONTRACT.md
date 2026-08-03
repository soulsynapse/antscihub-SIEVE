# Tool contract plan

Scope: the Tool base's first real code, together with the vocabularies its
signatures name. `docs/archive/PLAN.md`'s Phase 3 layout settlement made this
a single unit — "the five-shape algebra is one design unit … all five IR
classes landing in the change that first needs `Resample`" — on the ground
that the op vocabulary is one closed contract arriving whole. PAR-0005
supersedes that ground (2026-08-03): the vocabulary is what has been proved
and no more, and a further form is admitted one at a time, with the rewrite
it licenses, never in advance. The unit survives on a narrower footing —
`kernel.py` carries one marker, and the change that first needs `Resample`
is the one that gives `lower()` a return type. So this cycle lands
`src/sieve/kernel.py`, `src/sieve/views.py`, and `src/sieve/tools/base.py`,
discharging their markers: `20260802T023505Z`, `20260802T023511Z`,
`20260802T023508Z`, and `20260802T023509Z`.

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
declaration-only modules: the proved forms as an IR — the affine coordinate
map, the sequential bit, and `Opaque` (PAR-0005) — and the seven view layers
as a closed vocabulary. Neither holds an implementation of anything — no
resampler, no renderer.

**Gate (two decisions; narrowed 2026-08-03 from four by PAR-0005 and
PAR-0007):**

1. **What a shape instance *is*, and which names `kernel.py` exposes.**
   PAR-0005 settles the first half: an op is a value — a closed constructor
   with typed fields, never a callable — so Exchange 5's
   `Resample(scale=(1, 1/p.factor, 1/p.factor))` is the op parameterized,
   not a base class for a library of resamplers. What is left is a
   confirmation and a surface. Confirm that "the kernel is the set of
   primitive operations" in `ARCHITECTURE.md` describes a wider thing than
   `kernel.py` holds; then settle the exposed names, which is this phase's
   alone: PAR-0002's position split sends vocabulary reached for by name to
   the function-body form, so the names decide whether `kernel.py` stops
   raising at import — and PAR-0007's Outcomes are unobservable until it
   does.
2. **`lower()` returns an op *graph*, not an op.** `ARCHITECTURE.md` says
   "params to an op graph"; Exchange 5's example returns a bare `Resample`.
   Whether a single op is a one-node graph or graphs are a separate type has
   to be settled before the shapes are written, because it determines whether
   composition lives in the vocabulary or above it. PAR-0007 settles it —
   `lower` returns a graph with named outputs, a single op being the one-node
   case — but is `Proposed` and governs nothing, so the decision is taken
   here or at that record's acceptance, never twice.

Two gate items came off this phase on 2026-08-03 rather than being answered,
and are recorded so they are not rediscovered as gaps:

- **Where non-trivial primitives live** is a `DEFERRED.md` entry, deferred on
  PAR-0007's own one-way-door filter: no module path is in a recipe hash, so
  being wrong later costs a file move and some imports, never a store
  migration. PAR-0007 settles only the negative — not the tool module,
  because the operation is different debt. Loose preference when due:
  `kernel/` as a package.
- **How a second input enters the shape signatures** was due here because the
  layout settlement landed all five shapes together and `Fold`'s signature
  was being written for real. PAR-0005 retired that table, so `Fold` is no
  longer landing; the `DEFERRED.md` entry's trigger moved to *the first
  stateful op is written*, where the form is admitted under PAR-0005's
  admission rule and its signature is settled by the op that needs it.

Ordering note: vocabularies before the contract, by blast radius. The op
representation feeds the recipe hash the store addresses by, so changing it
later orphans every stored value. That is cost, not corruption — no
git-history semantics here, unlike the pipeline file and the automatic ledger
— but it is the largest blast radius in this cycle.

Exit: both modules import cleanly; `views.py`'s vocabulary is closed and
complete at v1 with its additive-revision discipline stated in code, while
`kernel.py` holds the forms that have been proved with PAR-0005's admission
rule stated beside them — "complete" is the wrong bar for a vocabulary that
is open by admission; `20260802T023505Z` and `20260802T023511Z` no longer
enumerate and the ledger is regenerated in the same commit as each removal;
the suite is green.

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

Exit: `Tool` is a real contract; `20260802T023508Z` and `20260802T023509Z` no
longer enumerate and the ledger is regenerated in the same commit as their
removal; the suite is green.

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

- ~~**Four of the five shapes land with no caller.**~~ **Retired 2026-08-03
  by PAR-0005.** The risk was that four shapes would be guessed at n=0 —
  exactly the n=1 generalization failure Exchange 6 describes — mitigated
  only by their being signatures rather than implementations. The admission
  rule dissolves it rather than mitigating it: `PixelMap`, `Window`, and
  `Fold` are no longer landing, and each is admitted when a rewrite it would
  license is both wanted and provable, with its signature settled by the op
  that needs it (`DEFERRED.md`, "Further forms enter the kernel"). `Opaque`
  lands with no caller and is not the same risk: it exposes no structure and
  authorizes nothing, so there is no surface to guess wrong. Kept rather than
  deleted because a risk dissolved by a later decision is worth the same
  record as one that fired.
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
