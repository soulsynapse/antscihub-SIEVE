# VISION v3

## History
v1 of SIEVE was very good, but completely inflexible. It worked for what it was built for; it was well praised, and did what it needed to well. It lives in antscihub-optical-flow-detector.

v2 of SIEVE was the rewrite because v1 was pretty hardcoded for a certain type of pipeline. I needed to see what would be needed for a modular architecture, and v2 did it pretty well. It lives in the antscihub-SIEVE-v2 folder.

v2.5 of SIEVE was me planning and planning and planning in circles. It lives in antscihub-SIEVE currently, just because I haven't bothered to rename it.

## v3 difference






### Primary components

Derived from v2 — its `docs/ARCHITECTURE.md`, its `.importlinter`, `src/sieve/`, and the 44 items in `docs/todo/`. Not a list of v2's packages: v2 ran long enough to show which of its boundaries held, which needed a bespoke contract written to prop them up, and which were declared before anything needed them. Each entry carries the observation that justifies it.

Each entry states what it owns and what it must never own, because **the never-list is the outgoing forbidden edge set**. That is what makes this a component list rather than a package list.

Ten primaries, bottom of the stack to top. A primary is a band in the layer contract. An interior is a boundary inside a band that the layer contract cannot express, and it gets its own contract.

**Quantity.** Dimensioned values and the frame: media time as a rational against the container rate, wall time, work units, frame counts and indices, spans, ROI, channel spec. Owns unit arithmetic and refuses implicit conversion. Never owns a default, a filter's meaning, or an I/O call.

*From v2:* the quantity types landed 2026-08-04 (`core/types.py`) and the rest of R6 did not. Ceilings are still denominated in the wrong dimension (`docs/todo/ceilings-in-the-dimension-they-bound.md`) and no number carries provenance (`a-number-says-how-it-was-founded.md`). Both are retrofits in v2 because the type arrived after its consumers. Here a number carries its dimension *and* how it was founded from the first commit, or neither ever arrives.

**Contract.** The vocabulary a step declares itself in — accepts, emits, cost, warmup bound, determinism, statefulness, version — plus the registry mapping id to declaration. Owns what can be said about a step. Never owns an implementation, and imports no codec and no toolkit.

*From v2:* this is the split worth copying verbatim. A filter is two things on two tiers: its spec is data in `core/`, its kernels are code in `filters/`, so a saved DAG loads and validates structurally with no filters installed and no codec present. `FilterSpec` is constructed in the registry, never in the filter module. Keep both.

The one thing v2's contract could not say is the thing that cost it most: `ArraySpec` cannot distinguish a block-signal series from an image, so the GUI grew its own `kind_in`/`kind_out` and with it a second spelling of edge legality. Expressiveness here is not a nicety; it is what makes the second model unnecessary.

**Document.** The saved artifact — an ordered DAG of nodes, holding intent and never progress. Owns the schema, its migration, and the identity line: a field either changes what a result *is*, and is hashed, or only where it lives and how fast it arrives, and is never hashed. Nothing straddles. Never owns machine state, a preference, or a widget's notion of anything.

*From v2:* schema v5 with `extra="forbid"`, and `checkpoints`/`outputs`/`crops` on `Project` and deliberately off `Node`, which is the identity line made structural rather than reviewed. Carry that. Carry also v2's highest-priority unfinished item as a starting condition rather than a destination: everything touching footage is a filter, so crop, span, temporal step and detection are nodes in the graph, not side channels beside it (`docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md`). Identity is not exemption — "no crop" is a full-frame ROI, never `None`.

**Ops.** Array math as a declared kind: arrays in, arrays out, no state, no spec, no registration. Never owns a filter id or a params model.

*From v2:* the kind is right and the population drifted. `settled_frames` exists twice — `core/ops/wavelet.py` and `core/ops/detection.py` — and `detect/detector.py` imports both under the aliases `settled_after_coi` and `settled_after_window`. An op is named by what it computes, never by which filter reaches for it, and `ops/detection.py` is the counter-example: a module named after a consumer.

**Machine.** The machine read once, and the ledger of shares over it. Owns available cores and memory, the worker split, the memory reserve, and the declaration that a given consumer takes a bounded slab. Never owns a judgement about which consumer matters.

*From v2:* the placement rule this validates is worth stating as a rule — a thing shared by dependency but not by agreement sits in its own band below every consumer, not in the pure-logic band. Carry v2's honesty mechanism too: a declared share with no sensor is listed as `WITHOUT_SENSOR`, and the list is shrink-only. v2's rule 5 was rewritten from a two-body to an N-consumer rule only after a fourth consumer slipped past a test that summed declared constants; write it N-consumer from the start.

**Decode.** The only path to a frame. The sharpest boundary v2 drew, and it should be copied to the letter including its reason: it is narrower and more load-bearing than "the only package that imports cv2," because it is what keeps decoder identity a single string and therefore keeps cache keys meaning something.

- *Reader* — one seek strategy, one frame at a time, one probe of the container rate. (A `double` cannot carry 30000/1001, which is why Quantity's rational exists.)
- *Prefetch* — N readers, one per thread. v2 measured 1.61× peaking at four workers and *degrading* beyond, allocator- and page-fault-bound rather than core-bound. The finding transfers; the constant gets re-measured, not re-guessed.
- *Lowered* — crop and scale pushed into the decoder, expressed as inert value objects so planning and keying can name the lowered contract without importing process machinery.

Never owns a cache key, a node, or a project.

**Store.** Bytes at rest and frames in flight, under one identity. The largest departure from v2, where these were two components that never met: `storage/` at 161 lines knows a format and an array and never a key, while `pipeline/cache.py` is a `FrameStore` protocol whose only real implementation is an unbounded dict — named `UNBOUNDED` in the share ledger and deferred in its own docstring.

- *Identity* — the key. What is hashed is the Document's business; computing and comparing the key is this component's.
- *Retention* — eviction against a declared budget. v2 already built the instrument for choosing this honestly: an access-event recorder replaying against ring, LRU, and playhead-distance simulators. Choose the policy by that measurement rather than by argument.
- *Writer* — reads its own output back before registering it, and deletes rather than records what it cannot verify.

*From v2:* the general store was deferred waiting on "a workload that can say what the chunking is for," the workload never came, and so the rule "filesystem is truth at rest" spent two weeks in the table governing nothing and had to be demoted. The lesson v2 drew is the one to carry: a rule that governs no code path is not a rule. This component exists when its first writer does, and its band is declared before then.

**Execution.**

- *Graph* — legality, ordering, keys, plan. The single spelling of edge legality; if a front end needs a second one, that is a defect in Contract's expressiveness, reported there rather than worked around here.
- *Filters* — one module and one markdown per filter, discovery automatic, importing is registering. Kernels live here and a kernel may reach a codec, because a kernel calling into `cv2` touches no container, no seek, and no decoder identity. What keeps it honest is the declared version that enters the cache key.
- *Executor* — the one loop that computes a frame. Every front end calls it; a caching front end over it is not a second one. Never grows a front-end concept in its signature; if it must, the fix is an adapter, and if no adapter can express the need, the rule is what gets redesigned.

*From v2:* rule 1's actual check — run one project through two front ends and diff the output — was called "the most valuable unwritten check in this repo" and never landed. Here it lands with the *second* front end, in the same commit, or the second front end does not land.

**Budget.** The ceiling table, the metric bus, and the visibility of a miss. Drawn above Execution, but the tier is a prohibition rather than a dependency: it imports nothing from the tree, and everything below pushes into it. What the placement forbids is Execution importing Budget, which is why the measured layer takes an injected measure callable.

*From v2:* the tier has a real price — the measured layer names its budget keys as string constants, reintroducing one layer down exactly the unchecked-key typo the key registry exists to prevent. v2 pays it and closes the hole from the other end, with a test that fails on a budget nothing publishes *and* on a published key that is no budget. Pay it the same way. Carry the two shrink-only honesty lists: budgets without a producer, and budgets in declared debt.

**Interaction.** Named now, because in v2 this was 44% of the tree, 16k lines under one contract unit, and the site of every boundary failure. Four interiors:

- *Intent* — the edit surface: commands, undo, snapshots, the project boundary. Toolkit-free and testable headless. v2 has an open item that is exactly the residue of not having drawn this (`docs/todo/qt-free-logic-under-gui.md`).
- *Transport* — request to decoded frame to paced delivery. It is handed a request — a frame, a consumer, an intent — and never reaches back for the project, which is what lets a second consumer drive it without either learning about the other. This is the one interior boundary v2 drew explicitly, and it held.
- *View* — renders values and emits intents; computes nothing. In v2 this needed its own contract, because the layer contract governs direction and therefore cannot say it: the view sits above the math, so importing a wavelet into a widget is legal under every layer rule while being precisely the second implementation rule 1 forbids.
- *Shell* — window, tabs, and command assembly. Owns wiring and nothing else. v2's evidence for naming it apart: `gui/filter_tab.py` reached 2321 lines and eleven responsibilities, importing from five layers.

Two front ends sit over these — terminal and desktop — and what makes them two front ends rather than two implementations is that a saved project runs identically under either because there is nothing else it could do.

Preferences sit here, in one settings object, with no channel to an answer. The boundary is enforced by the test rather than by the rule: scrambling every preference leaves every result and every cache key unchanged.

#### What is deliberately not a component

The never-lists above are edges. This is the absence of nodes — declare the boundary, never the machinery.

**Detection is not a component.** In v2 it is spelled in four layers — two ops modules, a `detect/` package, a filter that is a compatibility façade re-exporting the package's functions as thin wrappers, and a fifth derivation inside a widget — and four open items name the smear. Here detection's math is Ops, its composition is a Filter, its parameters are Document fields, and its export is a Writer. There is no fifth home.

**Device policy is a reserved band with no type surface.** v2 built a complete backend type system, a preference order of GPU then CPU, and a runtime-availability check that tests for a module rather than probing a device — with zero GPU kernels in existence, and backend identity entering every cache key for no benefit. Reserve the band so the contract governs it on arrival. Write no enum until a kernel needs one.

**Process isolation is a reserved band with its two edges settled now.** v2 declared a workers band before it existed, which was right, but left it a sibling of the orchestration band — so the contract forbids the one edge the design requires and says nothing about the one it forbids. Settle both in the declaration, not in the commit that fills it.

**A sink is not declared until something writes through it.** v2 has the type, and the CLI refuses any project that uses it.

#### How the never-lists get checked

A static import graph over the AST, with layer bands parsed live from the contract file so the two cannot drift, marking every edge as conforming, grandfathered, or going the wrong way up. Cheap and honest, and v2 already built it (`graph-system/extract.py`). Note what it is: a reachability graph, not a trace of a run.

Direct-import checking is not sufficient for these never-lists. v2's contract that the view computes nothing allows indirect imports, and the view consequently reaches the forbidden detection package transitively — through the filter façade — and passes. At least the computes-nothing class of never-list has to be checked over transitive reach.

One thing to settle rather than inherit: every contract v2 enforces carries a shrink-only exception list, and v2's own note is that *the exception list is the work list* — an entry whose import disappears fails the contract, so deleting the code and deleting the exception are one edit, and adding an entry is a reviewed widening. That mechanism is why v2's boundaries moved instead of staying aspirational. A boundary with no such mechanism can only be declared after the code is already clean, which in practice means declared late, or widened quietly.