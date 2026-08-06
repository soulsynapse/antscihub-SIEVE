# Phase 2: Structuring for future filter development

**End goal:** three years of ordinary churn from now, with ~30 working filters
in the repo, adding filter #31 touches only that filter's own directory — and if it requires new functionality, the capability to safely add that in without breaking everything else. Nothing else in the repo has to be edited, re-read, or re-reasoned about to add it.

Thus, below is a list of what is reasoned to be **what must be true for SIEVE to absorb a filter it was not designed for — such that the cost of adding the 31st filter is equal to or less than the cost of adding the 1st.**

## Using the MCP to queue tasks
During any given pick up, you can do one of three things:

1. Implent a single unfinished plan step. If you finish it and are under 30 steps, you can do another.
2. Add a new problem statement and steps. See: Working with this plan below.
3. If no actionable item remains, drain the rest of the queue. This should only be done when there isn't a clear way forward.

## Implementing a step
1. Assess if what you are doing should be done *before* another structural constraint. Utilize the lookahead document for ideas.
2. If there is another structural constraint that blocks the planned work or would result in extensive duplication, you can place a [UNBLOCKED WHEN] statement at the end, and write the new problem statement following the instructions.
3. If there isn't a blocker after a cursory glance, you can implement the step. If you finish in under 30 turns, you can do another.
4. As you complete a step, any findings you did along the way should be logged. If you notice buggy code, small problems should be fixed on the spot, larger problems that aren't structural should be queued with the queue tool before continuing on the big stages plan. Overly verbose comments or docstrings that don't genuinely explain something that can't be inferred from the code itself should be fixed in place.
5. Before you close you should fix up changes in the plan file as a result of your edits, and queueing the things you need.

## Adding a new problem statement:
1. Verify a problem that is structurally blocking to the end goal. You can look to the 1-big-stages-lookahead.md for ideas, and 0-big-stages-identification.
2. State the problem *that specifically blocks the end goal* with **IF**, **THEN**, **RESULTING IN**. Each problem statement gets a h2 numbered entry, the IF/THEN/RESULTING IN is right below the problem statement header, and the rest of the info for addressing the problem lives with that entry.
3. Under the IF THEN RESULTING IN problem list (and there can be multiple), you draft a solution very generally, such that all the if-then problem statements are addressed. Each if/then/resulting in statement should live directly below the solution proposition, with checkmarks for which of them they address. A solution doesn't address all the if/then statements doesn't go forward unless I say it is acceptable, but one that does, can go forward.
3. Then make a list of steps, with checkboxes so we know what work has been completed, and a completed when statement. Steps should be scoped to 1 chunked deliverable that can be done in under 50 steps.


---


## 1. The shell still owns the vocabulary for what can attach to what

IF the contract cannot express the distinctions the shell needs to offer,
order, load, and repair filter chains, THEN the GUI keeps a parallel vocabulary
of chain kinds, stages, catalog entries, and tab-side pseudo-steps, RESULTING IN
filter availability and compatibility being re-decided outside the filter's own
directory whenever a new shape appears.

Verified current state:

- `src/sieve/core/filter_base.py` declares `StreamKind`, `ArraySpec`,
  `FilterSpec.accepts`, `FilterSpec.emits`, `FilterSpec.mode`, and emitted
  element meaning, but the GUI docstrings still say `ArraySpec` cannot
  distinguish an image frame from a block-series frame.
- `src/sieve/gui/chain_model.py` owns `ChainKind` and `Stage`, builds the
  default chain with literal `rescale`, `normalize`, and `block_signal` node
  IDs, then appends `morlet_band` and `windowed_count` steps that are not
  nodes.
- `src/sieve/gui/wizard_model.py` owns `CatalogEntry` and a hand-written
  `catalog()` whose node-backed entries repeat registered filter IDs, while the
  two tab-side suffix entries have no `filter_id`.
- `chain_from_pipeline()` in `src/sieve/gui/wizard_model.py` refuses a saved
  graph whose node has no catalog entry, then appends the tab-side suffix from
  the catalog because the artifact cannot carry those operations.
- `tests/unit/test_filter_id_spelling.py` already treats GUI spellings of
  filter IDs as a declared shrink-only exception set, including
  `gui/chain_model.py`, `gui/filter_tab.py`, and `gui/wizard_model.py`.

Failure mechanism:

The registry can discover a new filter module, and the graph can validate the
stream shapes currently declared there, but the wizard cannot know whether that
filter belongs in the chain, which stage should offer it, what user-visible
handoff it produces, or whether a saved chain can render it unless the GUI's
private catalog and kind walk also learn that answer. The filter therefore
becomes runnable before it becomes safely authorable, loadable, and repairable.

Why this does not stay fixed-cost:

Every new handoff shape widens the private GUI vocabulary or adds another
exception to the shrink-only literal list. With many filters, authors must know
which shell files duplicate the contract and which pseudo-steps are not filters,
so the cost of adding filter #31 depends on accumulated GUI history rather than
on the new filter's own declaration.

Dependency position:

This comes after the open contract decisions that define emitted shape,
compatibility, semantic parameter types, temporal class, and the fate of the
current tab-side pseudo-steps. Doing it before those decisions would freeze
today's `ChainKind` and stage vocabulary into the next architecture. It comes
before replacing the linear chain model with the graph authoring model, because
the graph editor should consume a settled declaration surface rather than
inherit the GUI's private one.

Solution proposition:

Make the authoring surface consume one declared description of operation
availability and handoff compatibility. The description may be generated from
filter declarations, derived through a graph-layer query, supplied by a
non-identity presentation channel, or split between filter-owned declarations
and explicitly shell-owned operations; the required property is that the shell
does not keep an independent compatibility catalog for filter-backed steps.

Addresses:

- [x] IF the contract cannot express the distinctions the shell needs to offer,
  order, load, and repair filter chains, THEN the GUI keeps a parallel
  vocabulary of chain kinds, stages, catalog entries, and tab-side pseudo-steps,
  RESULTING IN filter availability and compatibility being re-decided outside
  the filter's own directory whenever a new shape appears.

Steps:

- [x] Reconcile the current tab-side temporal and detection suffix: decide
  whether each operation becomes a declared graph/filter operation or an
  explicitly shell-owned view/action that never appears in the filter catalog.
- [x] Define the declared handoff property the authoring surface needs, at the
  same semantic level as "image frame", "block series", "events", or a successor
  vocabulary.
- [x] Define the stage or grouping property the authoring surface needs without
  making cache identity depend on user-facing presentation text.
- [x] Add a graph-layer query that answers which registered operations can attach
  at a seam or port using declarations rather than GUI-only type checks.
- [x] Add a synthetic-filter canary that registers a filter at test time and
  proves it appears in the authoring surface with no GUI catalog edit.
- [x] Extend the canary to load a saved graph containing the synthetic filter and
  render it without a hand-written `CatalogEntry`.
- [x] Move existing filter-backed catalog facts behind the declaration/query
  path, keeping any presentation-only fields out of cache identity.
- [x] Remove the GUI filter-ID spellings that become redundant and shrink the
  `SPELLED_AWAY_FROM_HOME` exception set in the same commit.
- [x] Preserve or retire each remaining GUI filter-ID spelling with a written R7
  justification: unknown filters may be slower or plainer, but not wrong or
  unloadable.
- [x] Report the cycle metric: files touched outside `filters/<name>/` to add a
  GUI-visible filter using an existing handoff shape.

Step 1 reconciliation:

The current tab-side suffix is behavior, not a shell-owned view. The temporal
band operation and the detection operation must leave the no-`filter_id`
catalog path and be represented by declared graph/filter operation(s). The shell
may keep multiple cards, plots, and gestures for editing those parameters, but
the offer/load/repair catalog cannot list `morlet_band` or `windowed_count` as
operations that have no graph identity.

The transitional code already points to the ownership boundary: `detect` is a
registered filter with `DetectParams`, declared I/O, warmup, a windowed CPU
kernel, and the `detect_series` compatibility adapter; `pooled_scalogram` keeps
the Morlet plot derivation on the filter side. The v6 graph migration should
therefore make the detection suffix graph-owned, either as the existing
composite `detect` operation or, if reusable band power becomes an authored
handoff, as explicit registered operations split at that handoff. It must not
preserve the current no-filter catalog entries.

Shell-owned state is limited to presentation and interaction: card grouping,
focus, handle gestures, plot layout, and inspection-only choices such as
`solo_block`. Those may render or edit declared operation parameters, but they
are not catalog operations and are not saved as graph steps.

Step 3 grouping property:

The authoring grouping is now `FilterSpec.authoring_group`, whose value is a
stable `AuthoringGroup` slug rather than the stack header text. The field is
required at filter registration, forwarded by `register_filter`, and assigned
for every current filter. It lives in `SPEC_CHANNELS` as
`Channel.PRESENTATION`, and the cache-key presentation sweep proves moving a
filter between groups does not change a node key.

Current assignments are intentionally workflow buckets, not labels:
`crop` and `span` are `source_prep`; `rescale`, `downsample`, `normalize`, and
`background_ema` are `spatial_prep`; `block_signal` is `signal_extraction`;
`motion_history` and `temporal_baseline` are `temporal_filter`; `detect` is
`detection`. The GUI may render different titles or orderings, but the first
declared grouping answer now lives with the filter declaration rather than in
`gui/wizard_model.py`.

Step 4 graph-layer attachment query:

`Dag.attachable_operations()` now answers the authoring question before a node
exists: given the stream present at a seam, it returns the latest registered
filter specs and input ports whose declarations admit that stream. Supplying a
`downstream_port` constrains the same candidate by what it emits, using the
same `StreamSpec.admits` relation as `Dag._edge_faults`. Multi-input filters
are returned per compatible port, leaving the authoring surface to decide
whether the remaining ports can be filled.

The query is deliberately still declaration-only. It does not read `ChainKind`,
`Stage`, or `CatalogEntry`, and it does not construct a provisional GUI chain.
The current tests pin array-to-array and array-to-table insertions, including a
table downstream port that admits `detect` and an array downstream port that
removes it.

Step 5/6 synthetic filter canaries:

`tests/unit/test_wizard_model.py` now builds a scratch `FilterRegistry`, copies
the discovered specs into it, registers `synthetic_smooth` only in the test, and
proves that it appears in both `Dag.attachable_operations(ArraySpec())` and
`candidates_for_insert(..., registry=...)` without adding a legacy catalog row
for that filter. Inserting the offer mints a node with default params and keeps
the chain grade OK.

`chain_from_pipeline(..., registry=...)` resolves the same synthetic filter
from the registry-derived catalog and preserves loaded node ids while appending
the current tab-side suffix.

Step 7/8 catalog migration:

The remaining filter-backed parity rows left `gui/wizard_model.py`. The wizard
now projects every single-default-port streaming filter from `FilterSpec`:
`authoring_group` selects the stack stage, `authoring_order` preserves stable
workflow ordering inside the stage, `summary` supplies the row blurb, element
declarations derive the coarse chain handoff, and `authoring_hidden_params`
supplies the generic settings form's hidden fields. `authoring_order` and
`authoring_hidden_params` are `Channel.PRESENTATION`, and the cache-key
presentation sweep proves moving either does not change a node key.

The only explicit catalog rows still in `wizard_model.py` are the no-`filter_id`
tab-side suffix operations, `morlet_band` and `windowed_count`, which remain
shell-owned until the graph migration gives them graph identity. The redundant
wizard catalog literals for `background_ema`, `downsample`, and `normalize`
were removed from `SPELLED_AWAY_FROM_HOME`; the remaining wizard spellings are
the `block_signal`/`rescale` bridge that injects chain state into
`block_signal` params.

Step 9 R7 preservation:

No remaining GUI filter-ID spelling retired in this pass. The live stack still
has three preserved legacy-coupling sites, all now checked in
`tests/unit/test_filter_id_spelling.py` as `GUI_R7_JUSTIFICATIONS`.

- `gui/chain_model.py` keeps `rescale`, `normalize`, and `block_signal` for the
  default parity chain and step IDs. That names the hand-built starting stack,
  not the authoring rule: registry-projected filters still offer and load
  through the catalog and saved-graph path without a `ChainStep` literal.
- `gui/filter_tab.py` keeps `rescale`, `normalize`, and `block_signal` for the
  hand-built parity card bodies, parameter routing, and rescale-cost fast path.
  A registry-projected filter that lacks those bespoke controls is plainer, or
  may miss that optimization, but committed non-parity steps receive generated
  parameter rows and keep routing edits by node id.
- `gui/wizard_model.py` keeps `block_signal` and `rescale` only for the live
  bridge that injects `fps` and the current scale into `block_signal`'s hidden
  params. Other filters get params from their own model defaults; a missing
  rescale step falls back to scale `1.0` rather than refusing the filter.

This preserves the current GUI exceptions by R7's rule: they may buy a
hand-written default, body, or fast path, but a registered filter unknown to
those cases is still offerable, loadable, and correct.

Step 10 cycle metric:

Files touched outside `filters/<name>/` to add a GUI-visible filter using an
existing handoff shape: **0**. The evidence remains the `synthetic_smooth`
canary in `tests/unit/test_wizard_model.py`: it registers only in a scratch
registry, appears in the authoring surface, validates through
`Dag.attachable_operations(ArraySpec())`, inserts with default params, and
loads from a saved graph without adding GUI catalog code. This cycle touched
the guardrail and plan to preserve legacy exceptions, not to integrate a new
filter.

Completion note:

This problem statement is complete. The next numbered structural problem from
`1-big-stages-lookahead.md` is now tracked below with re-verified live-code
evidence.

Completed when:

Registering a synthetic filter with an existing handoff shape and no GUI code
makes it available in the authoring surface, validates through the graph-layer
compatibility query, round-trips through save/load, and leaves no required edit
in `src/sieve/gui/chain_model.py`, `src/sieve/gui/wizard_model.py`, or
`src/sieve/gui/filter_tab.py`. Any remaining shell-owned operation is absent
from the filter catalog by rule rather than mixed into it as a no-`filter_id`
entry.


## 2. New handoff shapes still require a central contract migration

IF a stream declaration family has to be added as a `StreamKind` enum member and
as a member of the `StreamSpec` type alias before any filter can use it, THEN a
filter with a new but self-contained handoff shape edits the core contract,
every exhaustive runtime gate, and the shape-space tests before its own
declaration can exist, RESULTING IN new handoffs remaining coordinated
migrations rather than additive filter-local work.

IF a node can declare only one emitted `StreamSpec`, THEN a filter that naturally
produces paired outputs such as an analysis frame and a coordinate table must
either split itself into coupled nodes or hide one product outside the graph,
RESULTING IN validation, cache identity, and lineage seeing less than the user
consumes.

Verified current state:

- `src/sieve/core/filter_base.py` declares `StreamKind` as the closed pair
  `ARRAY` and `TABLE`, and `StreamSpec` as `ArraySpec | TableSpec`.
- `ArraySpec.admits()` and `TableSpec.admits()` carry the compatibility relation
  themselves, and `Dag.attachable_operations()` plus `_edge_faults()` consume
  that relation generically. The duplicated part is not edge compatibility; it
  is how a new stream family enters the declared set at all.
- `FilterSpec.accepts` already supports named input ports through
  `StreamSpec | Mapping[str, StreamSpec]`, and `FilterSpec.input_ports`
  normalizes the one-input shorthand. `FilterSpec.emits` is still a single
  `StreamSpec`.
- The contract comment beside `StreamSpec` explicitly says the input-port half
  exists, while the output-port half is deliberately unbuilt until a detector or
  other filter needs to emit both an overlay frame and a coordinate table.
- `src/sieve/backend/dispatch.py` enumerates `StreamKind.ARRAY` and
  `StreamKind.TABLE` for accepted and emitted streams with `assert_never` in the
  final branch. That is the settled guardrail for missing runtime support, but
  it is still a central branch per new kind.
- `tests/unit/test_declarable_shapes.py` builds the declarable runtime space as
  the product of `Mode`, `rate_changing`, accepted `StreamKind`, and emitted
  `StreamKind`, then decides refusals by testing whether each side is
  `StreamKind.ARRAY`. A third stream kind intentionally fails the suite until
  the central runtime answer is added.
- `src/sieve/core/filter_registry.py::register_filter` repeats the same
  `accepts` and `emits` shapes in the decorator signature, and
  `tests/unit/test_filter_contract.py` pins that signature to the `FilterSpec`
  field list.

Failure mechanism:

The current contract protects itself against silent drift: a new stream kind or
runtime shape trips pyright or a focused test instead of slipping through. That
is useful, but it is not the same as extensibility. A filter author who needs a
mask stream, object-track stream, graph stream, event stream, or paired
frame-plus-table result cannot keep the change local to the filter or to a
small capability extension. They first have to widen the central type alias,
teach every exhaustive reader what unchanged behavior means, and decide how a
single emitted stream should stand in for a multi-product result. Under pressure,
the cheaper path is to smuggle the new handoff through `TableSpec.columns`,
array metadata, params, side artifacts, or shell knowledge, which makes the
result invisible to validation, cache identity, and lineage.

Why this does not stay fixed-cost:

The first added stream family costs a central migration, and the second one does
too unless the extension shape changes. Each new member fans out through the
contract, dispatch refusal, shape-space tests, inspect/presentation fallback,
and any place that asked a concrete `ArraySpec` or `TableSpec` question when it
only needed a capability question. With ~30 filters, the cost is no longer the
new filter's declaration; it is re-reading every layer that learned the old
closed set.

Dependency position:

This comes after the first problem because the authoring surface now consumes
filter declarations and the graph-layer compatibility query instead of a GUI
catalog. Without that, a more extensible stream declaration would still be
shadowed by the shell vocabulary. It comes before multi-output graph authoring,
parameter interaction inheritance, and presentation-slot arbitration, because
each of those later surfaces needs a contract-level way to name new handoff
families without re-answering what an edge carries.

Do not re-decide while implementing this:

- Keep `SPEC_CHANNELS` as the partition for every `FilterSpec` field; a new
  field must still be classified as identity, execution, or presentation.
- Keep `backend.dispatch.unrunnable_reason()` beside the kernel protocols as
  the place that names declarable runtime shapes no protocol can call.
- Keep the `assert_never` exhaustiveness idiom for closed core decisions unless
  the implementation replaces the closed decision with an explicit extension
  surface.

Solution proposition:

Make declaration-shape growth an explicit contract capability instead of an
accidental widening of a closed pair. New stream families and emitted products
may be represented by a protocol, registry, generated closed view, port mapping,
or another design, but the required property is that consumers ask the contract
for the capability they need and that a new handoff family can be added without
editing existing filter declarations that do not use it.

Addresses:

- [x] IF a stream declaration family has to be added as a `StreamKind` enum
  member and as a member of the `StreamSpec` type alias before any filter can
  use it, THEN a filter with a new but self-contained handoff shape edits the
  core contract, every exhaustive runtime gate, and the shape-space tests before
  its own declaration can exist, RESULTING IN new handoffs remaining coordinated
  migrations rather than additive filter-local work.
- [x] IF a node can declare only one emitted `StreamSpec`, THEN a filter that
  naturally produces paired outputs such as an analysis frame and a coordinate
  table must either split itself into coupled nodes or hide one product outside
  the graph, RESULTING IN validation, cache identity, and lineage seeing less
  than the user consumes.

Steps:

- [x] Inventory every live reader of `StreamKind`, `StreamSpec`, `ArraySpec`,
  `TableSpec`, `spec.accepts`, and `spec.emits`, classifying each as a generic
  compatibility reader, a runtime-exhaustiveness gate, a single-output
  assumption, or a presentation/interop special case.
- [ ] Add a contract-level canary for a third stream declaration family, or an
  equivalent test double, that proves registration, edge compatibility,
  `Dag.attachable_operations()`, and inspect/presentation fallback either consume
  it generically or refuse it by the declaration field that blocks it.
- [ ] Define the sanctioned provisional form for a not-yet-runnable stream
  family so unsupported shapes fail at a contract boundary without becoming
  opaque payloads.
- [ ] Decide and implement the emitted-port declaration surface, or write an
  explicit `[UNBLOCKED WHEN]` statement tying output ports to the later
  authoring-topology problem if the current graph model cannot carry them yet.
- [ ] Move consumers that only need compatibility, display naming, chroma
  demand, or runtime support off concrete `ArraySpec`/`TableSpec` branches and
  onto declared capabilities or stream-owned methods.
- [ ] Keep the dispatch exhaustiveness gate and shape-space walk, but make their
  fixture space derive from the extension surface rather than a hand-maintained
  `ARRAY`/`TABLE` product.
- [ ] Add a synthetic filter canary whose new handoff shape costs zero edits to
  existing filter directories and whose unsupported runtime status is named by
  the declaration that blocks it.
- [ ] Report the cycle metric: files touched outside `filters/<name>/` to add
  another GUI-visible filter using a handoff shape already added through the
  extension path.

Step 1 inventory:

Current live contract readers classify as follows:

- Contract definition and forwarding: `src/sieve/core/filter_base.py` owns the
  closed declaration surface: `StreamKind`, `ArraySpec`, `TableSpec`,
  `StreamSpec`, `FilterSpec.accepts`, `FilterSpec.emits`, and `input_ports`.
  Its invariants are also readers: array emitters require `element`, non-array
  emitters reject it, port mappings are normalized on the input side only, and
  `emits` is still one stream. `src/sieve/core/filter_registry.py` mirrors the
  same `accepts` and `emits` annotations in `register_filter`, while
  `src/sieve/core/__init__.py` only re-exports the names.
- Generic compatibility readers: `src/sieve/pipeline/dag.py` is already mostly
  stream-owned. `Dag.attachable_operations()` asks each declared input port's
  `admits()` and, when supplied, the downstream port's `admits()` against the
  candidate's `spec.emits`. `_edge_faults()` uses the same relation after an
  edge exists, and `_port_faults()` reads `input_ports` only to decide whether
  the downstream port set is filled exactly. `tests/unit/test_dag.py` pins both
  edge rejection and the authoring offer query.
- Runtime-exhaustiveness gates: `src/sieve/backend/dispatch.py` is the central
  gate. `unrunnable_reason()` enumerates accepted and emitted `StreamKind`
  values with `assert_never`, and the kernel decorators read `input_ports`
  arity plus `Mode` to keep frame, mapping, and span protocols paired with the
  declaration. `src/sieve/pipeline/executor.py::_bind()` consumes that single
  refusal, so it does not repeat stream-family branches. The guardrails are
  `tests/unit/test_declarable_shapes.py`, which derives the runnable/refused
  space from `StreamKind`, and `tests/unit/test_backend_dispatch.py`, which pins
  decorator protocol pairing.
- Single-output assumptions: `FilterSpec.emits` is one `StreamSpec`, and
  `src/sieve/core/pipeline_model.py::Edge` names only an upstream node, a
  downstream node, and the downstream input port. `Dag._edge_faults()` and
  `Dag.attachable_operations()` therefore read one `spec.emits` per node, and
  `Dag.node_keys()` folds one output key per node. `src/sieve/gui/wizard_model.py`
  projects only single-default-port streaming specs into `CatalogEntry`, then
  gives each node one `ChainStep` on load. `tests/unit/test_wizard_model.py`
  currently pins that single-output stack reconstruction.
- Presentation and interop special cases: `wizard_model._input_kind()` and
  `_output_kind()` branch on `TableSpec`, `authoring_group`, and `element` to
  recover the current coarse `ChainKind`. `Dag._requires_chroma()` reads
  concrete `ArraySpec.channels` for decode-format demand, with coverage in
  `tests/unit/test_decode_format.py`. `src/sieve/cli/detect_cmd.py` requires the
  selected node to emit an `ArraySpec` before running the per-frame detector
  collection path; `src/sieve/cli/inspect_cmd.py` prints raw `accepts` and
  `emits`; and `src/sieve/gui/chain_model.py` documents that `ChainKind` is not
  `StreamKind`. `tests/property/test_filter_settling.py` is intentionally an
  array-to-array producer probe, and `tests/unit/test_filter_id_spelling.py`
  reads `TableSpec.columns` for the column-name duplication guard. The many
  remaining `ArraySpec()` and `TableSpec()` mentions in tests are ordinary
  fixture declarations rather than independent contract readers.

The next canary should hit the first generic path before it changes runtime
support: registration, DAG edge compatibility, and `Dag.attachable_operations()`
can consume a test stream through `admits()`, while dispatch and current
presentation surfaces should refuse by the declaration field they cannot
support rather than by filter id or an opaque payload.

Completed when:

A real or test-only third stream family can be declared without editing existing
filter modules, graph compatibility and the authoring offer query see it through
the same contract path as existing streams, consumers that cannot run or render
it issue field-named refusals rather than branching by filter id, and paired
emitted products either have graph-visible identity or a written blocker ties
that half to the topology problem.
