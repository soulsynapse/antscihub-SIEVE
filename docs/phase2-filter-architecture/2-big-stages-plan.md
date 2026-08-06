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
1.

## Working with this plan:
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
- [ ] Define the stage or grouping property the authoring surface needs without
  making cache identity depend on user-facing presentation text.
- [ ] Add a graph-layer query that answers which registered operations can attach
  at a seam or port using declarations rather than GUI-only type checks.
- [ ] Add a synthetic-filter canary that registers a filter at test time and
  proves it appears in the authoring surface with no GUI catalog edit.
- [ ] Extend the canary to load a saved graph containing the synthetic filter and
  render it without a hand-written `CatalogEntry`.
- [ ] Move existing filter-backed catalog facts behind the declaration/query
  path, keeping any presentation-only fields out of cache identity.
- [ ] Remove the GUI filter-ID spellings that become redundant and shrink the
  `SPELLED_AWAY_FROM_HOME` exception set in the same commit.
- [ ] Preserve or retire each remaining GUI filter-ID spelling with a written R7
  justification: unknown filters may be slower or plainer, but not wrong or
  unloadable.
- [ ] Report the cycle metric: files touched outside `filters/<name>/` to add a
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

Step 2 declared handoff property:

The property the authoring surface needs is a graph-owned semantic handoff role
on each operation port. It is not `StreamKind` alone and not the dtype/channel
detail inside `ArraySpec`: it names the user-meaningful product that can be
offered across a seam, at the level currently approximated by `ChainKind`.
Minimum current roles are source/image frame, block series, and detection gate;
`events` is not the registered detector's array output until an operation emits
interval or table rows. If a later filter introduces coordinates, tracks, masks,
embeddings, or another product that users can wire independently, it adds a
role there instead of widening GUI vocabulary.

A handoff role is identity contract data because it decides edge legality,
authoring availability, saved-graph repair, and whether two outputs can be
substituted. It must be declared or resolved per port from the filter's spec
without reading a GUI catalog. The declaration may be concrete ("this output is
block series") or relational ("preserve the upstream role") the same way element
meaning is concrete or preserved/aggregated, but after DAG resolution every node
output and every input port must have a concrete role or be explicitly
unofferable with a diagnostic.

The role is narrower than presentation and broader than storage shape. It does
not say where a card is grouped, what icon/title/caption the shell uses, what
plot slot renders it, or how expensive it is. It also does not replace
`StreamSpec.admits`: dtype, channel, table-column, and port checks still reject
impossible graphs before handoff-role compatibility decides semantic
attachability. The next graph-layer query should require both structural stream
compatibility and handoff-role compatibility, and the shell should display that
answer rather than recomputing either half.

Concretely against today's chain:

- source, `rescale`, `downsample`, `normalize`, and `background_ema` preserve or
  emit an image-frame role;
- `block_signal` emits a block-series role and must declare that role beside its
  filter declaration, not in `ChainStep`;
- `detect` emits a detection-gate/per-frame-state role; the current tab's
  "events" label is presentation or a future table/interval emitter, not the
  role of the registered filter's array output;
- `morlet_band` remains no catalog operation unless it becomes a registered
  operation with its own declared input and output roles.

Completed this step when:

The plan has one semantic answer for "what travels across a seam" that the next
code step can implement without asking `gui.chain_model.ChainKind`. It
deliberately leaves the concrete Python representation open, but forbids any
representation whose only reader is the GUI catalog or whose values are stage
names, titles, icons, or other presentation fields.

Completed when:

Registering a synthetic filter with an existing handoff shape and no GUI code
makes it available in the authoring surface, validates through the graph-layer
compatibility query, round-trips through save/load, and leaves no required edit
in `src/sieve/gui/chain_model.py`, `src/sieve/gui/wizard_model.py`, or
`src/sieve/gui/filter_tab.py`. Any remaining shell-owned operation is absent
from the filter catalog by rule rather than mixed into it as a no-`filter_id`
entry.
