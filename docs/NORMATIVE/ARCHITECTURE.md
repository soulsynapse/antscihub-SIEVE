# ARCHITECTURE

SIEVE is a data-intensive application. A filter chain over video emits many
multiples of the source in derived data — one intermediate per node per frame
per replicate — and the design problem is how that derived data is keyed,
materialized, invalidated, and thrown away, not how any one filter computes.

The vocabulary is Kleppmann, *Designing Data-Intensive Applications*, named so
that design discussions start from a shared word rather than reinvent one. It
covers the interactions — state, windows, joins, backpressure, keying, skew —
and does not cover cost estimation or performance modeling. Where §2 and §7 need
a cost model with calibrated, parameter-dependent constants, the reference is
query optimization (Selinger-style estimation; Volcano/Cascades for structure);
where §7 needs an estimate for a machine we are not running on, it is analytical
performance modeling. Named here so a cost discussion does not go looking in the
wrong book.

Two more names. §5 is event sourcing with read models (Fowler; Kleppmann ch. 11),
whose vocabulary this document already borrows without having named the pattern,
and naming it is what puts projection rebuild and event schema evolution within
reach of someone who would otherwise derive them. §2.7 is the uniform interface
constraint in REST's sense — one invariant call shape, with variation carried in
the message rather than in the method set — implemented as a context object.

This document is normative: each section states a rule, the mechanism that
enforces it, and the failure mode it forbids. It covers runtime data only. How
the codebase is organized — toolbags, contracts, package surfaces — is a
separate argument and is not answered here.

One dividing line runs through all of it. What appears in an operator's contract
or in a key must be right from the beginning, because changing either rewrites
every operator and invalidates every artifact. What is an engine implementation
choice can be replaced whenever, which is the whole point of §2.

## 1. Keying admits things to the DAG

The system of record is the source assets and the pipeline spec. Everything
else — filter output, preview frame, crop artifact, detection table — is
derived: recomputable, disposable, and keyed by the derivation that produced it.

1. A key is the transitive closure of what the output depends on: operator
   identity and version, its resolved parameters, the geometry it was asked
   for, and the keys of its inputs. Two runs with the same key must agree to the
   operator's declared determinism class (§1.5), or it is not admissible. And
   nothing else: a key names what an artifact *is*, never how it was obtained.
   The route of derivation is provenance (§5.1), and a term describing the route —
   which optimization ran first, where the bytes were staged, what path the source
   sat at — discards the reuse keying exists to buy. The two halves fail in
   opposite directions and both fail silently. A missing term makes different
   results collide under one name; a surplus term makes identical results miss
   each other, so a cheaper route to the same bytes invalidates everything it was
   meant to help.
2. Membership in the DAG *is* deterministic keyability. This is the admission
   test for pipe sections, and it is checked at registration, not by review.
   An operator that reads wall-clock time, machine state, or an RNG it does not
   declare and seed fails the test.
3. Nothing derived is authoritative. Any cache, proxy, or materialized
   intermediate can be deleted at any point and the only consequence is
   recomputation cost.
4. The source assets being video today is a property of the operators we have,
   not of the system of record. Nothing outside an operator's own input
   declaration may assume a decodable video exists.
5. Determinism is declared and the class is part of the key. The classes are an
   open registry closed by policy at two: a class is a declared name with a
   declared equivalence predicate, and a third is refused without an explicit
   decision rather than being unrepresentable. *Bitwise* operators reproduce
   byte-identically and may be freely recomputed, compared, and discarded.
   *Tolerant* operators — threaded reductions, GPU kernels with float atomics,
   any library whose summation order varies by build — reproduce only within a
   declared numeric tolerance, so their artifacts are materialized once per key
   and reused rather than recomputed and compared. An operator that declares no
   class is bitwise, and failing to reproduce is then a failure rather than a
   discovery. The registry is open because the first operator fitting neither
   class would otherwise be forced into tolerant with a meaningless bound, which
   is this section's own named failure arriving through the taxonomy instead of
   through the tolerance.
6. An artifact is whatever a key names, and for an operator carrying state
   across frames that is a frame range together with the state it began from —
   not a frame. The starting offset is part of the key. Without this, output
   that depends on where a run happened to start keys as though it does not, and
   nothing can detect the difference. *Frame range* is the noun of today. The
   durable claim is that an artifact is the span plus the state it began from,
   and it is stated over frames and offsets because the addressing axis is a
   totally ordered index; when that stops being true the rule is restated over
   whatever the span is, since a source addressed by something other than a total
   order still has an entry state and stops having a starting offset
   (STRATEGY §6.5).
7. The determinism class propagates infectiously: an artifact computed from a
   tolerant input is tolerant, and cannot claim byte-identity its inputs do not
   have. Tolerant artifacts are therefore pinned — still deletable, since §1.3
   admits no exceptions, but the deletion is recorded as invalidating the
   byte-identity claim of everything downstream rather than only as a
   recomputation cost. This is what lets a wipe-and-recompute check and a
   preview-divergence check compare bytes at all; under boundary-stopping
   propagation both compare nothing.
8. A declared tolerance is a bound derived from a stated numerical argument that
   names the source of non-determinism — threaded reduction, float atomics,
   library build — and is tested against that argument's prediction rather than
   against the author's number. A bound chosen to make its own test pass is not a
   check, and a source is verifiable by inspection where a number is not. This is
   the same complaint as inferring determinism from a version string: a version is
   not a guarantee.
9. Measurements are derived artifacts and carry keys like anything else. A fitted
   cost shape is keyed by what it was fitted from, including the machine profile
   (§7.4), so refitting is invalidation rather than an update in place, and a
   measurement taken under one allocation cannot silently answer a question about
   another machine. Without this there are two derived-data disciplines and every
   argument about invalidating a fit is had twice.
10. Source identity is content-derived, or at minimum path-independent. The
    closure in §1.1 terminates at sources, so whatever names a source is what
    every derived key ultimately rests on, and a name encoding where the asset
    currently sits makes the artifacts non-portable while leaving the spec
    perfectly portable — the spec resolves on the second machine, every artifact
    keyed under the first machine's paths misses, and the recomputation looks
    like a cold cache rather than like a defect. That is §1.1's surplus term
    arriving at the base case, where there is no upstream key to inherit the
    fault from. Path-independence is the floor and is what buys reuse across
    machines and across a reorganized library; deriving the identity from content
    additionally makes the asset changing under a stable name detectable, since a
    re-encoded file at the same name is a different source and must key as one.
    The weaker form is admitted rather than the stronger one required because the
    difference is a read over every asset at admission, and at a hundred thousand
    files that cost is real.
11. Frame-exactness is a measured and keyed property of a source, never an
    assumption about a decoder and not a gate. Whether a seek lands on the frame
    it asked for is a question about a particular library, build, and container,
    and it is answerable only by measurement — read a range sequentially, read
    the same indices after seeking, compare — never by reading a version string,
    which is §1.8's complaint arriving at the source layer. What the measurement
    produces is a term in the source's key, so two runs reaching a frame by
    different paths do not collide under one name. It is not a gate because
    refusing an inexact decoder refuses the footage users have, and §1.1's rule
    is to key the hazard rather than forbid the capability it endangers. The
    reason it is worth measuring at all is that this particular hazard is
    invisible to every downstream check: two runs that seek the same way agree,
    so an inexact seek makes every key silently wrong and no comparison
    downstream can find it.
12. The unit above a single source is a **collection**: a declared set of
    members, each member a source together with the parameter overlay that
    applies to it. Replicates are what motivate it, and they are also why a member
    is not simply a source — two members can name the same asset and differ in a
    threshold, so what distinguishes them is the overlay and not the file. The
    working scale is what makes it a declared thing rather than a way of speaking
    about several runs: a hundred members over a hundred thousand files has to be
    addressable, keyable, and estimable, and none of those is available for a set
    that exists only in the user's head. Membership is a key term, which follows
    from §1.1 rather than being added here — an artifact derived across a
    collection has the member artifacts as its inputs, so a collection that gained
    or lost a member is a different input set and yields a different key, and a
    reduction over ninety-nine members cannot be mistaken for one over a hundred.
    Per-member artifacts key exactly as they did before: a member's overlay
    resolves to that member's parameters (§1.1) and nothing about the collection
    enters them, which is what lets a member's work be reused when the same member
    appears in a second collection.

    The sample a user tunes on is a subset of the members and not a separate kind
    of thing. Tuning selects a few members, the full run selects all of them, and
    the spec is the same spec across both (§5.2) — which is the whole of the
    operation STRATEGY §1.5 describes as the user's loop, and the reason it needed
    a unit before it could be named.

Forbids: artifacts that cannot be reproduced, and therefore cannot be
invalidated with confidence or thrown away without fear — and equally, an escape
hatch bolted on the first time a threaded kernel fails to reproduce bitwise.

## 2. Operators declare; the engine decides

An operator declares a pure transform, its I/O shape, and its cost model. The
engine decides fusion, materialization, parallelism, placement, and
scheduling. All of it travels through one invocation signature (§2.7), which is
the constraint the rest of this section is written inside.

1. Declared I/O shape covers input arity and dtype, output arity and dtype,
   geometry transform (does it change frame extent), and temporal extent on both
   sides — history and lookahead (§3.1). Parameters are declared with a
   semantic type — region of interest, curve, threshold-over-histogram, bounded
   scalar — not merely a primitive shape. §6 generates controls from these, and
   nothing can recover "this is a crop rectangle" from `tuple[int, int, int,
   int]`.
2. An operator never chooses its own thread, process, buffer size, or cache
   location, and never reads a machine-capability probe. Asking for those is
   the engine's job and the engine is allowed to answer differently per
   machine.
3. Cost is declared as a *shape*, not a constant: which declared inputs the
   work scales with, and how. Constants are fitted by the benchmark harness on
   the machine it runs on. A filter author writes "linear in output megapixels,
   linear in window length"; nobody hand-writes milliseconds. A shape may take
   measured properties of the data as terms — blob count, scene activity — when
   the work is content-dependent. That makes estimation two-pass, sampling the
   source before estimating, which is strictly better than an honest interval so
   wide it answers nothing (§7.6). The shape is then evaluated once per task,
   against the parameters that task resolved to, and never once against a
   representative task and multiplied by how many there are. Replicates are what
   makes this concrete rather than pedantic: they are parallel tasks over one
   source carrying their own parameter overlays, so a per-replicate window length
   or crop changes that task's cost and no other's, and a scaled single estimate
   is wrong by whatever the overlays do — invisibly, because it is wrong in the
   direction of confidence. §7.3 is the same heterogeneity showing up in the wait
   rather than in the estimate.
4. A new filter is benchmarked through the engine. There is no per-filter,
   per-machine stress ritual, and a filter that can only be validated by
   running the GUI and watching for lag is not finished.
5. Parameters are what the user tunes. Properties of the source — frame rate,
   extent, duration — and the resolved geometry produced by upstream nodes are
   execution context, supplied by the engine and never declared as parameters. A
   parameter that duplicates a source property can disagree with it, and the
   disagreement is silent, because the declared parameters remain perfectly
   consistent with each other while every quantity derived from them is wrong.
   The split is drawn where it is because the tuner is a human choosing values by
   hand, and that is what expires it: a swept or searched parameter is still the
   user's choice and still not SIEVE's opinion (STRATEGY §1.2), but "what the user
   tunes" stops being what separates the two, and the rule is then restated over
   who supplies a value rather than over who chooses it (STRATEGY §6.5).
6. Operators may take more than one input, and the interesting ones do — a node
   joining a full-resolution stream to a reduced one is a join across differing
   rates and geometries (Ch. 11). Reconciling them is the engine's job, and both
   are part of the key. Multi-input keying is cheap to allow now and expensive
   at the moment the first two-input node needs it.
7. Every capability axis is a *field* of one invocation signature, never a second
   signature. Arity, statefulness, rate change, window extent, declared tolerance:
   an operator implements one call shape and varies within it. Counting is the
   argument — two axes give four combinations, and a set of per-combination
   protocols will be missing one of them, found by whoever first needs it rather
   than by whoever wrote them; four axes give sixteen. Admission therefore rejects
   any operator the engine cannot actually run, which is a stronger test than
   rejecting one that declares incorrectly. A declaration the protocol cannot
   honour is a lie that stays hidden until something important needs it, and what
   needs it gets built beside the pipeline rather than in it — unkeyed,
   unschedulable, carrying its own threading, and invisible to every rule in this
   document. Widening the signature later rewrites every implementer: adding a
   field is compatible and adding a signature is not, which is §8's
   schema-evolution argument applied to the call rather than to the output.
   What makes this affordable is that the variation is carried in the message and
   not in the method set. A capability axis is a field an operator may ignore,
   never a method it must implement, so a pointwise operator receiving a call
   whose state and lookahead are empty implements nothing it cannot support and
   stubs nothing out. That distinction is the whole answer to the Interface
   Segregation objection this rule will attract, and the objection is worth
   taking seriously rather than deflecting: a wide interface really does cost
   something when it forces an implementer to supply what it has no meaning for,
   and the working use of that principle is more often about implementers than
   about the clients its original statement names. The cost simply does not arise
   here, because an ignored field is free and a stubbed method is a lie. Splitting
   the signature to avoid a cost that is not being paid is how the missing cell
   gets built.
8. There is one entry point into the engine and every surface uses it. A request
   states what is wanted, at what priority, by when if it has a deadline, and
   whether it should be shed or waited on under pressure (§3.3). The engine
   arbitrates across all outstanding requests because it is the only thing that
   can see them all. A surface passes requests; it never assembles stages. What
   this prevents is not duplicated code but arbitration that cannot happen — N
   surfaces each holding a private queue and a private coalescer compete for one
   machine with nothing deciding between them, and each surface that re-derives
   the orchestration gets it subtly different. Adding a surface, whether a batch
   mode or an off-box submit, is then a new caller rather than a fourth variant
   of the same assembly. This is §2.2 from the other side: an operator does not
   choose its own execution, and neither does a surface.

   The general rule this is one instance of: **one owner per contended resource,
   one entry point per capability.** A contended resource is anything whose users
   have to be arbitrated against one another rather than served independently —
   cores, memory, the disk, the decode path — and the diagnostic count is the
   number of components that believe they own one. Two owners of a resource never
   conflict visibly. Each is correct in isolation, each stays inside the budget it
   believes it has, and the machine is oversubscribed by their sum, so the symptom
   is a machine slower than any owner's model predicts with no owner that is
   wrong. §9.4 is this rule over artifact writing and §2.2 is what leaves the
   resources ownable at all: an operator picking its own thread has made itself a
   second owner of the cores, and it did not have to be a bad decision to do the
   damage.
9. An operator version declares its relationship to the version before it —
   whether it supersedes that version, and how parameters convert. Keys carry the
   operator version (§1.1), so versions churn precisely because keying works, and
   a saved pipeline naming a version nobody kept cannot be opened. Without a
   declared conversion there are exactly two options and both are bad: retain
   every version's code and parameter class forever, or break saved work on every
   change. Migration is what lets retired code actually be deleted, which is the
   only thing that makes a version number worth carrying rather than merely
   worth incrementing.

   An optimization is therefore a new version and not an edit: identical declared
   semantics, a different cost shape. Each piece of the machinery does one part of
   making that safe — keying keeps the two versions' artifacts distinguishable
   instead of silently mixed, the declared determinism class (§1.5) makes "the
   same answer" a precise claim rather than an intention, the cost shape makes the
   improvement a measured difference rather than an assertion, and the declared
   conversion is what eventually lets the slow version be deleted. Editing a
   version in place to make it faster is the same act with all four removed:
   artifacts computed before and after the edit collide under one key, and the
   claim that nothing but the speed changed becomes untestable at exactly the
   moment it most needs testing.
10. An operator may declare that its input is a collection (§1.12) rather than a
    stream. This is the kind that puts cross-member work inside the graph instead
    of in a script someone runs afterwards, and it is the arity axis of §2.7 taken
    to its end: §2.6's multi-input operator declares a fixed number of inputs at
    differing rates, while a reduction declares the collection axis and has its
    member count resolved at execution. It is a field of the same signature and
    never a second one, so an operator that reduces across members is an operator
    and is scheduled, keyed, and placed like one. What forces the rule is that the
    alternative is not the absence of cross-source aggregation — the working cases
    need it — but cross-source aggregation assembled beside the pipeline, which is
    §2.7's named failure arriving through the one axis nobody declared.

This is the one place the architecture adds a requirement the product did not
ask for: declaring a cost shape is real work per filter. It is accepted because
without it the engine cannot place work, and SIEVE cannot answer "how long on
*your* machine" — the question that justifies the tool.

Forbids: bespoke filters, each tuned to the author's machine, with no runbook
and no comparable numbers.

## 3. Windows are declared; pressure policies are named per path

Filters that carry state across frames are stateful windowed operators.

1. Windows are declared on both sides. History and lookahead are separate fields,
   each a bound plus a function of resolved parameters: the bound is what admits
   the operator, the resolved value sizes the actual lead-in or read-ahead, and a
   resolved value exceeding its own bound is a registration error. The engine
   supplies both. An operator never reaches past what it declared in either
   direction. Lookahead is declared because it exists: a centered window reads
   frames after the one it is emitting for, and an operator that needs one and
   cannot say so is built outside the graph instead — unkeyed, unschedulable, and
   carrying its own execution. That is not a hypothetical shape, it is where the
   detection work went last time, and a one-sided declaration is what put it
   there.

   A warmup shortfall is legal at a source boundary and is a key term. The
   lead-in actually supplied is part of the key, so a frame computed with a full
   window and the same frame computed cold do not collide under one name. This is
   §1.1 applied to its own case: the hazard is keyed, not forbidden. Refusing
   instead would make every windowed operator unusable across the first *w*
   frames of every source, so a user who crops the start would get a refusal
   rather than a result and a disclosure. What remains forbidden is the sentinel —
   a value standing in for history that was not there, which reads downstream as a
   real result and is indistinguishable from one. Keying the shortfall is what
   makes the sentinel unnecessary rather than merely prohibited. The rule is
   symmetric now that the declaration is: a lookahead shortfall at the end of a
   source is the same disclosure at the other boundary, keyed the same way, and
   an operator whose window is two-sided has two ends at which a source can run
   out.
2. Retuning is reprocessing, not mutation. A parameter change replays the
   affected window; it never patches state in place.
3. Every producer/consumer edge names its policy: backpressure, bounded
   buffering, or load shedding. Chosen per path, never left to chance, and
   never "whatever the queue does when it fills."
4. Interactive paths shed; export paths backpressure. Dropping a preview frame
   is correct behavior and must be reported as such (§5.4). Dropping a frame
   from a run is a failure. Two path classes is an inventory of what the current
   paths are, not a claim that there are two: a long-running background
   derivation the user watches but does not interact with has no assignment under
   either, and the first one of those expires this rule as stated (STRATEGY §6.5).
   What does not expire is §3.3 — every edge names a policy, so an edge whose
   class is unclear is one that has not been assigned a policy rather than one
   entitled to go without.
5. State is checkpointable: serializable at a frame offset and restorable from
   one. Random access into a stateful stream — scrubbing across a long window —
   is restore the nearest snapshot and replay forward (Ch. 11). Never recompute
   from the beginning, and never fabricate a starting state. How often to
   snapshot is an engine tuning decision; *being* snapshottable is an operator
   contract, and it cannot be added later to operators written without it.

Forbids: a crop or a parameter change that makes the workspace slower than not
doing it, because some unnamed edge grew without bound.

## 4. One implementation, two trigger policies

Preview and run are the same operator graph under different completeness
policies. Preview triggers early on partial input and may be superseded; run
triggers once on complete input. Two policies is an inventory of what the work
needs and not a closed set, so a third completeness policy expires the count and
nothing else (STRATEGY §6.5). What survives it is §4.1 and §4.2: the policy is
engine configuration rather than a branch inside an operator, and divergence
between any two policies over the same graph is a bug of the highest class.

1. Trigger policy is engine configuration, not a branch inside an operator. An
   operator that asks "am I in preview?" is misfactored.
2. Any divergence between what preview shows and what a run produces is a bug
   of the highest class, because it silently breaks the user's contract (§6).
3. Sampling, downsampling, and proxy resolution are legitimate preview
   differences precisely because they are *keyed* differences (§1) — the
   preview is a different key, not different logic.
4. Completeness is a property of the artifact, not of the view showing it. An
   operator's declared window (§3.1) determines the point up to which its output
   can no longer change, and that settled boundary is computed from the
   declaration and carried on the artifact. A consumer therefore reads how far
   the result is final rather than inferring it, and no view has to work it out
   for itself — which is what stops the boundary from ending up as a private
   attribute of whichever widget first needed it, alongside the other state §5.5
   forbids living there.

Forbids: the Lambda failure mode — the same logic maintained twice, drifting.
Also forbidden is event-time machinery, which is a distinct thing and stays
refused: no watermarks, no late arrivals, no accumulation modes. §4.4's
boundary is derived from a declared window over an ordered source, so it needs
none of them — a source that arrived out of order would, and that is the
condition under which this refusal expires rather than a permanent property of
the domain.

## 5. Edits are a log; everything else is a view over it

Parameter edits form an ordered, replayable log. The preview, the caches, the
provenance record, and the GUI are materialized views maintained over it.

1. Undo, cache invalidation, and provenance are one mechanism, not three. Undo
   is truncating the log; invalidation is diffing keys across log positions;
   provenance is the log itself.
2. The log is the pipeline spec. Saving and loading a pipeline is serializing
   the log, so a tuned pipeline is redeployable by construction.
3. Every edit must be representable as data and replay must be deterministic —
   the same requirement as §1.
4. Views may lag, and must say so. A stale view announces staleness rather
   than blocking the UI to stay current. "Working" and "stale" are display
   states, not exceptions. A view also reports the settled boundary of what it
   shows (§4.4), which is a different question from freshness: freshness is
   whether the view has caught up with the log, settledness is whether the
   artifact itself can still change.

   Whether a view must also report the *identity* of what it shows — which feed
   filled this viewport, pipeline output or raw proxy decode — is deliberately
   unsettled. The naive fix puts a key on the most-copied object in the system
   and may cost more than the capability is worth, so it is not adopted by
   default. STRATEGY §9 holds it with its trigger: the first surface that
   displays two feeds into one viewport. Until then the obligation is that the
   artifact carries its key, not that every frame does.
5. No state that determines a result lives outside the log. Two categories sit
   outside it legitimately and are named rather than tolerated: view-local state
   (zoom, scroll, hover), which changes nothing computed, and machine-local
   preferences, which change what is *requested* but never what an artifact *is*.
   Anything else held only in a widget cannot be saved, undone, or reproduced,
   and is therefore not a feature.
6. Every derived quantity is an engine-owned keyed artifact that views read —
   settled boundaries, histograms, aggregates, counts, anything computed *from*
   results rather than displayed *from* them. This is §5.5 stated over quantities
   instead of over state, and it is a separate rule because a quantity computed
   inside a view does not resemble state living outside the log: nothing is
   stored, the computation is pure, and it derives only from what the view was
   already given. What it cannot be is keyed — so it cannot be cached,
   invalidated by a key diff, reused by a second view, or compared against the
   same quantity computed anywhere else. The second consumer that needs it
   computes it again, and now one number has two definitions and nothing that
   would notice them diverging. The dividing line is not whether the computation
   is expensive; it is whether the result is a fact about the data, which the
   engine owns, or a fact about the display, which it does not.

Forbids: a god-object tab that is the sole owner of the current pipeline state.

## 6. The user surface is a contract, and it is generated

SIEVE's usefulness equals the user's knowledge of it. The obligation this places
is disclosure rather than parity: no capability is *silently* unreachable, and
the gap between what the engine can do and what a user can reach is enumerable
and loud. A capability with no surface carries a debt naming the surface that
would pay it, so the gap is a query rather than a thing someone has to notice.

The surface is any generated authoring surface, not the graphical one
specifically. Scoping the obligation to a GUI makes it unsatisfiable for the
entire period during which the system that would satisfy it is being built,
which is how a rule becomes decorative; and a command-line surface generated
from the same declarations discharges the disclosure half in full. What it does
not discharge is legibility — a capability reachable only from a flag is
disclosed and is not thereby *findable*, which is a real and separate weakness
and is treated as one rather than folded in here.

1. Parameter controls are generated from the operator's declared I/O shape and
   parameter declarations (§2.1). They are not hand-written per filter.
2. Therefore an operator that declares a parameter gets a control for free. A
   hand-written bespoke panel means one of exactly two things: the operator's
   declaration is incomplete, or the semantic type it declares has no registered
   widget. The second is fixed by registering a widget, never by writing a
   panel.
3. Cost and progress surfaces read the same declarations the engine reads
   (§2.3, §7), so what the user is told about performance cannot drift from
   what the engine believes.
4. Widget classes are a bag, keyed by semantic type (§2.1). Direct manipulation
   — dragging a crop on the frame, editing a curve, picking a threshold off a
   histogram — is a widget class for a declared type, not an exception to
   generation. A rich control is a new member of that bag; it is never an
   operator-specific panel, because that is how one panel becomes the only place
   some state lives.
5. Authoring is graph-shaped from the start, and affordance rules are defined
   over a graph rather than over a sequence. The engine admits branching,
   fan-out, merges, and multi-input nodes (§2.6), so a surface modelling a
   pipeline as a list expresses a proper subset of what the engine runs — this
   section's second failure direction, and the one that goes unnoticed because
   everything the surface does offer works correctly. Nor is a sequence a simpler
   special case to be widened later: what may be placed here, what may connect to
   what, and why a connection was refused are all answered against adjacency in a
   list, and none of those answers survives the change of relation. Building the
   path first and generalizing afterwards is what happened last time, and the
   record of its cost is that the engine's branching was never reachable from the
   surface at all.
6. Generation covers more than parameter controls. Connectivity kind, where a
   node may be placed, the guidance shown for it, and the message explaining why
   it cannot go where it was dropped all derive from declared I/O and declared
   metadata (§2.1), because each is a statement about what the engine will accept
   and the declarations are where that is written down. Any of them authored by
   hand is a second account of admission maintained beside the first, and it
   drifts in the direction that costs most: a surface refusing what the engine
   would have run is indistinguishable, to the user, from a capability that does
   not exist. That asymmetry is why generation extends past the widget rather
   than stopping at it — a wrong control is visibly wrong the first time someone
   uses it, and a wrong refusal is never seen by the person it refuses.

Forbids: capability that exists in the pipeline and is silently unreachable in
the product, and the reverse — a control whose behavior the engine does not know
about. Both directions are failures and the second is the one that gets missed:
a surface able to express something the engine cannot run is as broken as one
unable to express something it can.

## 7. Performance is stated against a load parameter

"Frame" is not a fixed unit once cropping and downsampling exist. The load
parameter is megapixels per second through *n* stages.

That parameter is contingent and its expiry is already visible in §8.4: an
operator redefining its element — emitting a per-region value where its input was
per-pixel — does work that megapixels do not measure, and the load parameter for
it is stated over its declared element instead. What is durable is that
performance is stated against a declared load parameter at all, per path
(STRATEGY §6.5); megapixels per second through *n* stages is the parameter for
the operators that exist.

What this section requires is honesty about cost, not low cost. It is satisfied
by a slow operator with a truthful cost model and violated by a fast one with
none. Stating that plainly is what stops the whole section reading as a
performance mandate, which would have agents optimizing inside it before anything
has been measured — and an unmeasured optimization is a guess that has been made
expensive to remove.

1. Two distinct questions get two distinct statistics, never one number:
   *responsiveness* is percentile latency on interactive paths; *feasibility*
   is a throughput estimate with an uncertainty interval, which is what "how
   long will this take on my laptop" actually asks for.
2. Percentile targets are stated against the named load parameter, per path.
   Latency is reported as percentiles, never as a mean. Throughput is a rate with
   an interval — a rate is a mean, and it is the right statistic for the question
   §7.1 calls feasibility.
3. Fan-out waits take the maximum, not the mean. Replicates are parallel tasks
   over one source — the general case is the members of a collection (§1.12) —
   wall-clock is set by the largest, and per-task progress looks healthy right up
   until it doesn't. Straggler skew is the normal case, not an anomaly.
4. Every measurement is attributed to a machine profile, and the profile is a
   portable descriptor rather than a label on local results. A number without the
   machine it was taken on is not a number; a machine identifier only the machine
   that wrote it can interpret is not a profile. What the descriptor states is the
   terms a cost shape can be evaluated against — core counts by class, memory and
   its ceiling, the ceiling being an allocation and not necessarily the hardware —
   so the constants §2.3 has fitted on one machine are evaluable at another's
   profile, and the estimator accepts a profile it did not measure and returns an
   estimate for that machine. This is not a refinement of the measurement rule; it
   is the differentiator. Fitting locally and reporting locally answers a question
   nobody asked, because the question is whether a project is feasible on the
   machine the user has or the cluster they can apply for, and neither is the
   machine the fit was taken on. It is also the rule most easily reverted without
   anyone noticing: under a label-only profile every local number still looks
   correct, every local check still passes, and the one capability that justifies
   doing the measurement work at all is quietly unimplementable.
5. Memory is a declared and measured dimension, not a footnote to time. Peak
   working set relative to input size belongs in the cost declaration, because
   exceeding it is what freezes an interface or ends a run on a smaller machine,
   and a time-only model reports health while that happens. The ceiling being
   exceeded is the one the run is allocated, which on a scheduler-managed machine
   is not the machine's — stated that way because the mechanisms that impose an
   allocation are today's and the ceiling being an allocation is not.
6. An interval must be narrow enough to discriminate, not merely wide enough to
   be correct. Coverage on its own is satisfiable by widening — "somewhere
   between two seconds and two hundred" contains the truth and answers nothing —
   so the check on an estimate has two clauses: a re-run falls inside the stated
   interval, *and* the interval separates the ends of the range the user is
   choosing between. Without the second clause the check rewards the least
   informative estimator, and the discipline decays toward one, because widening
   is always the cheapest way to stop failing. How narrow is narrow enough is set
   by the decision the interval serves and not by a constant: an interval that
   cannot separate a cheap parameter setting from an expensive one on a single
   machine cannot support tuning, and one that cannot separate a laptop from a
   cluster cannot support the feasibility question at all. §2.3's two-pass
   estimation exists to satisfy this rule on content-dependent work, where the
   only alternative is an interval wide enough to cover every input the operator
   might see.
7. A collection's cost is the sum over its members of each member's own estimate;
   its wall-clock is the fan-out maximum (§7.3). Those are two numbers answering
   two questions — total work, and time until the last member finishes — and
   neither is one member's estimate multiplied by the count (§2.3). Extrapolating
   across member count is therefore not a new dimension in any operator's cost
   shape: it is a sum, and the thing that still has to extrapolate is the
   per-member estimate across the machine profile (§7.4), which it already did.

Forbids: performance claims that only hold on the author's machine, and
progress bars that lie by averaging.

## 8. Outputs carry a declared schema

Outputs are written with an explicit, versioned schema so another pipeline —
or another tool — can read them without reading our source.

1. The schema is declared, versioned, and written with the data. Readers
   validate; they do not infer.
2. An output whose consumer is unspecified is not designed. The shape of
   outputs sets the ceiling on extensibility, because downstream pipeline
   sections ingest them.
3. The requirement is schema and interop. Column orientation is an
   implementation detail with little to offer narrow fact tables; if a columnar
   container is chosen, it is chosen for its schema, not its compression. The
   dismissal is conditioned on the tables being narrow and expires with that —
   wide tables read a column at a time change the trade-off, and the requirement
   above them does not.
4. A schema says what one value *is*, not only how wide it is: what it counts
   and per what unit. An operator that redefines its element — emitting a
   per-region value where its input was per-pixel — declares that; one that
   inherits its input's meaning declares that instead. There is no safe default,
   because the symptom of guessing wrong is a correct-looking number read under
   the wrong noun by whatever consumes it next. This is not in Kleppmann; it is
   closer to dimensional analysis.
5. How an element addresses back into its source is declared, not assumed. The
   declaration states how to map an element index to a source region and back,
   and how to test whether a point falls inside one. Rectangles and uniform grids
   are the common case of that facility, never the assumption underneath it. Bake
   them in and the source crop, the logic matching an artifact against a request,
   and every surface mapping a click to an element each encode the same
   assumption independently — so the first irregular region or irregular element
   breaks three things at once, and none of the three can be fixed on its own.
   The declaration originates with the operator that produces the elements
   (§2.1); it travels with the schema because the readers are what need it. The
   same declaration carries a member axis wherever a collection is involved
   (§1.12): an element in an artifact derived across members addresses back to a
   member as well as to a region inside it, and that is one declaration rather
   than a spatial descriptor with a source label set beside it. A reader able to
   say which pixel a value came from but not which member it came from can do
   nothing with the value.

Forbids: outputs that are only interpretable by the version of SIEVE that
wrote them, and an element whose provenance in the source is inferred from its
index.

## 9. Verification happens where the consumer reads

The end-to-end argument: correctness is checked at the point of consumption,
not promised at the point of writing.

1. An artifact is verified by reading it back through the same path a consumer
   would use. An encoder's success code is not evidence.
2. Tests assert on keyed artifacts and observable outputs, not on internals.
   This is what makes them survive refactoring — the thing they check is the
   thing §1 already guarantees is stable.
3. Golden fixtures are keyed like anything else (§1); a fixture that cannot be
   regenerated from its key is a liability. They are therefore synthetic and
   generated, never downloaded and never committed media — a fixture that has to
   be fetched is a fixture that gets skipped, and a test that skips is
   indistinguishable from one that passes, so the suite stays green while the
   thing it was written to check has not run since it was written. Synthesis buys
   the second thing a downloaded asset cannot: a fixture constructed to answer the
   question being asked. A source whose frame *n* is a known function of *n* lets
   a test assert which frame a seek landed on, which is the instrument §1.11
   requires and which no amount of real footage supplies.
4. One facility owns writing an artifact, and everything that writes one goes
   through it: staging to a temporary location, reading back through the consumer
   path, comparing what was read against what was intended, handling
   cancellation, and committing atomically. The rule is worth stating because the
   alternative is not that the work gets skipped — it is that the work gets
   reinvented per writer, at differing strength and with differing error quality,
   which is exactly what happened last time and happened twice independently.
   Nobody notices, because a writer that half-implements this is indistinguishable
   from one that implements it fully until the disk fills or a run is cancelled.

Forbids: a test suite that has to be rewritten every time the internals move,
and artifacts trusted because the writer said so.

## 10. Scope

Out of scope, permanently: replication, consensus, distributed transactions
(Ch. 5–9). A design discussion reaching for these has gone wrong.

Nothing in §§1–9 may assume the executing machine is the machine holding the
interface. That is the durable half of this section, and it is a constraint on
the other nine rather than a boundary drawn around them: comparing a laptop
against a cluster is the question §7.4 exists to answer, and an architecture
that forbids running elsewhere cannot estimate running elsewhere.

The boundary this section used to draw — **one machine per run** — is withdrawn,
and what it was for is stated in its place: planning for distribution must not
shape the design before distribution exists. Written as a boundary it was read as
a constraint and could not survive being one, because a collection of a hundred
members (§1.12) is the ordinary case and is precisely what one machine per run
forbids. Either it forbade the normal case or *run* meant something narrow enough
to forbid nothing, and neither is what it was for. Partitioning and straggler
handling across nodes stay unbuilt until work is submitted off-box; what §1.12
buys is that they are unbuilt rather than precluded, since a collection of
independent members partitions at the member and needs no concept that does not
already exist.
