# Principles

## Key Tools

- Key everything that determines a value, and nothing else.
- One declaration; every presentation is generated from it.
- Edits are the log; everything else is a view.
- One call shape; a declaration cannot outrun it.


## TOOL 1 SUPPORT

**Key everything that determines a value, and nothing else.**

*Content addressing over a Merkle DAG — Git, Nix, Bazel. Identity is a digest of the
transitive closure of inputs, so equality is decidable without comparing bytes. The name
obliges two things the corpus states separately: hermeticity, since an input that is not
declared is an input that is not keyed, which is Bazel's sandbox and this document's admission
test; and early cutoff, since a rebuild stops the moment a digest matches, which is what the
"and nothing else" half buys and what a surplus term destroys.*

Two halves, and both have to hold. A missing term makes different results collide under one
name. A surplus term — anything describing *how* the bytes were obtained rather than *what*
they are — discards the reuse the mechanism exists to get.

**The half that was missing, and what it cost**

- v2 defined `cacheable = deterministic and not stateful` — `core/filter_base.py:250`
- Keying anything else raised — `pipeline/cache_key.py:61`
- Unkeyable nodes were skipped — `pipeline/dag.py:311`
- And so was every node downstream of a skipped one — `pipeline/dag.py:293`
- Four of seven filters carried state, three of them mid-chain — `filters/background_ema.py:58`, `block_signal.py:72`, `motion_history.py:105`, `temporal_baseline.py:76`
- So the cache was inert past the first stateful node, which is most of any real pipeline
- The hazard was diagnosed exactly, and answered by forbidding the entire class — `backend/dispatch.py:90-95`
- The key's actual terms are upstream keys, filter id, version, params, backend — `pipeline/cache_key.py:68-75`
- Start offset, span, and history actually supplied appear nowhere in that list
- Lead-in shortfall was computed, reported to the user, and never keyed — `pipeline/plan.py:89-94`, `cli/run_cmd.py:134`
- So frame N with full history and frame N computed cold share a key and differ in bytes
- State lived in a closure created at bind time, with no offset to key against — `backend/dispatch.py:61`
- Which is why checkpointing was unrepresentable rather than merely unbuilt
- Determinism was inferred from a numpy version string, not from BLAS build, thread count, or SIMD path — `backend/identity.py:17-20`

**The half that was surplus, and what that cost**

- A crop artifact backing a replicate replaced the source key with that file's own identity — `pipeline/resolve_source.py:70`
- While the ROI was dropped for pre-cropped sources — `pipeline/dag.py:286`
- So the same frames key differently depending on whether an optimization has already run
- Crops are written losslessly, so the pixels do agree — `storage/crop_writer.py:37`
- The cost is a discarded cache rather than a wrong answer, which is exactly the surplus-term failure
- Source identity was an absolute path plus size and mtime — `pipeline/cache_key.py:34`
- While the spec keyed off it stored relative paths and relocated cleanly — `core/pipeline_model.py:76`, `:448`
- So v2's pipelines were portable and v2's artifacts were not, decided once by the identity function

**The assumption underneath both halves**

- Frame N of source S is a fixed array only if the decoder guarantees it
- Seeks fall back to `CAP_PROP_POS_FRAMES` past a 40-frame grab-forward window — `decode/reader.py:86`, `:13`
- Decoder identity captures the OpenCV version and a policy integer, not the seek path — `decode/identity.py:12`
- The instrument to test it already exists — frame *n* is a solid field of intensity `n * 5` — `tests/conftest.py`
- Unverified as of `9ed3b40`: the hazard is confirmed, the defect is not

**What it generates once it holds**

- Admission to the graph *is* deterministic keyability, checked at registration rather than by review
- Nothing derived is authoritative, so any cache, proxy or intermediate is deletable at recomputation cost
- Invalidation is a key diff across log positions, so it never becomes a subsystem
- Provenance is the log and undo is truncating it — one mechanism, not three
- Tests survive refactoring because they assert on keyed artifacts, which keying already holds stable
- Golden fixtures are keyed like anything else and regenerate from their key
- Measurements are keyed artifacts too, so refitting a cost shape *is* invalidation
- The correct response to a hazard is to key it, never to forbid the capability that raised it

**Why it is stated this way**

- The discriminating property is not that the pipeline executes; it is that it reproduces
- "The pipeline executes and produces outputs" cannot be violated by anything short of total breakage
- Keying's negation is a real system people build on purpose: a cache as the system of record
- Its bearer is *derived value*, which exists under any source kind, any backend, any interface
- Adopting it costs one field now, and every artifact ever written later


## TOOL 2 SUPPORT

**One declaration; every presentation is generated from it.**

*DRY as Hunt & Thomas actually stated it — "every piece of knowledge must have a single,
unambiguous, authoritative representation within a system" — which is about knowledge, not
about code, and is why two similar helpers are harmless while two validators for one property
are not. The derived half is model-driven generation, and the obligation the name carries is
that the model must be expressive enough to generate the hard cases; a generator that covers
the easy ninety percent produces a hand-written exception for the rest, which is the thing it
was adopted to prevent.*

Anything a human maintains in parallel with a declaration will drift. The failure is not the
drift — that is inevitable and cheap to spot. The failure is a second copy that looks
authoritative, and a check written against the copy rather than the source.

**The duplicate, and the test that certified it**

- The engine checked edge types through `admits` and propagated element kind — `pipeline/dag.py:201`, `:215`
- The interface checked the same property independently, with its own kind lattice — `gui/chain_model.py:66`
- Raising messages like "expects block series, receiving image" from a second source of truth
- `catalog()` calls `discover()` and then returns a hand-written tuple anyway — `gui/wizard_model.py:84`
- Each entry re-typing title, stage, input kind, output kind, blurb, hidden params, repeatable
- With hand-written guidance for the two stages that had no spec to read from — `gui/wizard_model.py:53`
- A test then asserted those hand-written kinds against the interface's own catalog — `tests/unit/test_chain_model.py:173-174`
- Which makes drift *pass*, and is worse than leaving the property untested
- The test's rationale says the kinds are not derivable from `FilterSpec` — `tests/unit/test_chain_model.py:167-170`
- That comment went stale at commit `48635fc` and is now false — `core/filter_base.py:199-211`
- Element meaning is refused at registration with no default, and every filter complies — `filters/block_signal.py:65`, `normalize.py:43`, `rescale.py:27`
- So a stale rationale kept a duplicate alive after the thing justifying it had been built
- No import check, type check, or coverage number catches that

**A vocabulary that existed in only one surface**

- `Stage` decides what a user may add where, and has no engine counterpart — `gui/chain_model.py:36`
- Nor does `ChainKind.EVENTS`, because detection was never in the graph — `gui/chain_model.py:33`
- The interface built edges with `itertools.pairwise` — a path, never a branch — `gui/chain_model.py:87`
- While the engine already supported branching, named ports, merges and fan-out
- So capability the engine had could not be authored, and might as well not have existed

**The generated version was already in the same tree**

- The CLI generates its entire parameter presentation from the params schema — `cli/inspect_cmd.py:111`
- And reads prose guidance from a sidecar resolved off the spec — `cli/inspect_cmd.py:135`, `filters/__init__.py:23`
- One surface generated everything it showed; the other hand-maintained a catalog of the same facts
- The generator this principle asks for has a working precedent in the repository it replaces

**What it generates once it holds**

- A declared parameter gets a control for free, with no interface edit
- A hand-written panel then means exactly two things: an incomplete declaration, or a semantic type with no registered widget
- The second is fixed by registering a widget, never by writing a panel
- The module guide is a walk over package surfaces, never a maintained file
- The debt register is the same walk returning nothing, so it cannot grow unbounded or drift
- Column names derive from the declared element rather than being typed by hand — `detect/tables.py:76`
- Cost and progress surfaces read the declarations the engine reads, so the two cannot disagree
- Connectivity, placement, guidance, and the reason-it-cannot-go-here message all come from one place

**Why it is stated this way**

- Its bearer is *declaration*, which exists wherever anything is configurable
- Its negation is a real system built often: two validators for one property, with nothing forcing agreement
- Per instance the cost is one hand-written entry; in aggregate it is every operator times every surface
- Which is why it is a principle rather than a convention — the aggregate is the unit
- Generation is also what makes offering every choice affordable rather than a promise nobody can keep


## TOOL 3 SUPPORT

**Edits are the log; everything else is a view.**

*Event sourcing with read models — Fowler; Kleppmann ch. 11, which ARCHITECTURE already
borrows the vocabulary of without naming the pattern. The name carries four obligations the
corpus states in scattered places or not at all, listed at the end.*

Undo, cache invalidation, provenance and view refresh are one question — what changed between
two states. v2 answered it four times, and each answer had a different failure mode.

**Four mechanisms, one question**

- Whole-project snapshots written per step, capped at fifty — `gui/history.py:13`
- Ten hand-written `QUndoCommand` subclasses, each with its own redo/undo pair — `gui/commands.py`
- Several carrying `id()`/`mergeWith()` coalescing on top of that
- A gesture object so that one drag becomes one undo step — `gui/document.py:65`, `:424`
- With a `_would_change` guard to suppress no-ops — `gui/document.py:343`
- And twelve distinct change signals, each consumer deciding for itself what to recompute — `gui/document.py:71`
- Snapshots answer "what changed" only for the newest pair
- Hand-written inverses make correctness a per-feature obligation that fails silently when wrong
- Broadcast signalling costs change-kinds times view-types, which is much of why one tab reached 1,629 lines
- All three costs grow exactly where v3 intends to grow

**What the interface kept because the engine declined to own it**

- 817 `self._` references across 154 distinct owned attributes, in one tab — `gui/filter_tab.py`
- Including `_filled`, `_settled`, `_series_final`, `_partial_published` — `gui/filter_tab.py:134-138`
- So a completeness boundary, which is a property of the computation, lives in a widget
- A source frame rate baked into interface defaults — `gui/filter_tab.py:119`
- Histogram surfaces built beside the view with their own bin count — `gui/density_plot.py:28`, `:31`, `:54`
- A quantity derived in a view cannot be keyed, cached or reused, so a second view computes it again
- Both costs scale with view count, and v3 adds views

**The two exceptions that are real, and are named rather than tolerated**

- Machine-local settings change which frames are *requested*, never what a frame *is* — `gui/preferences.py`
- View-local state — zoom, scroll, hover — changes nothing computed
- Anything else held only in a widget cannot be saved, undone, or reproduced, and is therefore not a feature

**What it generates once it holds**

- Undo is truncation plus replay, so no inverse is ever written
- Invalidation is a key diff between two log positions
- Provenance is the log itself
- A view declares the keys it depends on, and the diff says whether it must recompute
- That cost does not grow with view count
- Save and load is serialization of the log, so a tuned pipeline is redeployable by construction
- An edit that invalidates the graph is still a legal entry; the engine runs the valid subgraph and reports what is unreached

**What the name obliges**

- Replay determinism is constitutive, not a nice-to-have — without it the log is not a source of truth
- Snapshots are a performance mechanism the pattern requires, and are the *same* mechanism as operator checkpointing
- Event schema evolution is the pattern's known hard problem, which is the migration obligation arriving from a second direction
- A projection with side effects is the classic failure — anything a view does that is not recomputable belongs in the log
- The pattern's known cost is weight, and the corpus has no statement on log retention or compaction at 100,000-file scale

**Why it is stated this way**

- Its bearer is *edit*, which exists wherever anything is configurable over time
- Its negation is a real system and the common one: current state as the record, with history bolted on beside it
- The four mechanisms above were each individually reasonable and collectively unmaintainable
- It is the only one of the three source-of-truth claims that is about *time* rather than identity or representation


## TOOL 4 SUPPORT

**One call shape; a declaration cannot outrun it.**

*The narrow waist — IP over everything, everything over IP; REST's uniform interface
constraint. One invariant call shape, with variation carried in the message rather than in the
method set. GoF's Bridge is the diagnosis for what happens without it, and Context Object is
the mechanism: capability axes become fields of one signature.*

The invocation protocol is the real contract regardless of what the declarations say. If the
call shape cannot express something, declaring it is a lie that stays hidden until something
important needs it.

**Three protocols, four cells, one missing**

- `Kernel(frame, params)` — `backend/dispatch.py:30`
- `MergingKernel(frames_by_port, params)` — `backend/dispatch.py:34`
- `StatefulKernel(frame, params, state)` — `backend/dispatch.py:40`
- Policed by three decorators, each enforcing port arity — `backend/dispatch.py:146`, `:169`, `:193`
- The fourth cell does not exist, and the code says so in its own error message — `backend/dispatch.py:195-196`
- "no stateful merging protocol exists yet — the filter that needs one should bring its signature"
- So an operator could not both carry state and take more than one input
- Two axes give four cells with one already missing; lookahead and rate change would give sixteen

**Declarations the protocol could not honour**

- `Mode` is declared — `core/filter_base.py:29`
- `output_rate() -> Fraction` is declared — `core/filter_base.py:90`
- `rate_changing` is declared, with its own consistency checks against the params model — `core/filter_base.py:159`, `:220-229`
- `input_warmup_frames` already converts warmup across rate changes — `core/filter_base.py:280`
- The executor refuses every node that is not `Mode.STREAMING` — `pipeline/executor.py:108-112`
- "one frame in, one frame out — a windowed filter needs a span"
- And every node that is `rate_changing` — `pipeline/executor.py:113-117`
- "no way to emit nothing for an input frame"
- So there was machinery validating declarations the engine would refuse to run
- And nothing surfaced that at declaration time, only at bind time

**Where the capability went instead**

- The detector consumes the whole time series, outside the graph — `detect/detector.py:35`
- A Morlet CWT over the time axis — `core/wavelet.py:76`
- A windowed mean over cumulative sums, then a gate, then interval extraction — `core/detection.py:30`
- With `centered`, the window reads *future* frames — `core/detection.py:23`
- `hi = t + (window - window // 2)`, which no per-frame protocol can express
- So the product's centrepiece was built beside the pipeline rather than in it
- Which is why it is unkeyed, unschedulable, and carries its own worker, thread and CLI command
- And why `ChainKind.EVENTS` has no engine counterpart — `gui/chain_model.py:33`

**What the shortfall costs downstream**

- State captured in a closure at bind time has no offset to key against — `backend/dispatch.py:61`
- Which is why checkpointing was unrepresentable rather than merely unbuilt
- And why every form of random access into a stateful stream — scrubbing, resuming, replaying — was out of reach
- Retrofitting is impossible: the operators were written against a signature with nowhere to put it

**What the name obliges**

- A waist works only if it is wide enough, and a too-narrow waist forces capability outside it
- Which is exactly what happened, so the waist's width is a first decision rather than a later one
- Widening later rewrites every implementer, which is the same asymmetry as any key or contract change
- Schema evolution says adding a field is compatible and adding a signature is not — Kleppmann ch. 4
- The corpus already applies that argument to outputs and to operator versions, and not to the call itself
- Admission must reject any operator the engine cannot actually run, or declaration and capability drift again

**The tension worth naming rather than hiding**

- Interface Segregation pulls the other way: many small client-specific interfaces, not one wide one
- The resolution is that ISP is about *clients* not depending on methods they do not use
- This is about one *role* having one shape, which is the implementer's side and a different axis
- Anyone citing ISP against this claim is answering a question it does not ask

**Why it is stated this way**

- Its bearer is *the call*, which exists in any implementation that has operators at all
- Its negation is a real and common system: one protocol per combination of capabilities
- FINDINGS nominates this as the single most likely way a third implementation repeats the second
- The cost is one field now against every operator rewritten later
- And it is what makes every other declaration trustworthy, since a declaration the protocol cannot honour is a lie
