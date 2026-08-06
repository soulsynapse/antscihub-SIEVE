# Phase 2: Structuring for future filter development

**End goal:** three years of ordinary churn from now, with ~30 working filters
in the repo, adding filter #31 touches only that filter's own directory — and if it requires new functionality, the capability to safely add that in without breaking everything else. Nothing else in the repo has to be edited, re-read, or re-reasoned about to add it.

Thus, below is a list of what is reasoned to be **what must be true for SIEVE to absorb a filter it was not designed for — such that the cost of adding the 31st filter is equal to or less than the cost of adding the 1st.**

## Using the MCP to queue tasks
During any given pick up, you can do one of three things:

1. Implent a single unfinished plan step. If you finish it and are under 30 steps, you can do another.
2. Add a new problem statement and steps.
3. If no actionable item remains, drain the rest of the queue. This should only be done when there isn't a clear way forward.

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

1. Reconcile the current tab-side temporal and detection suffix: decide whether
   each operation becomes a declared graph/filter operation or an explicitly
   shell-owned view/action that never appears in the filter catalog.
2. Define the declared handoff property the authoring surface needs, at the same
   semantic level as "image frame", "block series", "events", or a successor
   vocabulary.
3. Define the stage or grouping property the authoring surface needs without
   making cache identity depend on user-facing presentation text.
4. Add a graph-layer query that answers which registered operations can attach
   at a seam or port using declarations rather than GUI-only type checks.
5. Add a synthetic-filter canary that registers a filter at test time and proves
   it appears in the authoring surface with no GUI catalog edit.
6. Extend the canary to load a saved graph containing the synthetic filter and
   render it without a hand-written `CatalogEntry`.
7. Move existing filter-backed catalog facts behind the declaration/query path,
   keeping any presentation-only fields out of cache identity.
8. Remove the GUI filter-ID spellings that become redundant and shrink the
   `SPELLED_AWAY_FROM_HOME` exception set in the same commit.
9. Preserve or retire each remaining GUI filter-ID spelling with a written R7
   justification: unknown filters may be slower or plainer, but not wrong or
   unloadable.
10. Report the cycle metric: files touched outside `filters/<name>/` to add a
    GUI-visible filter using an existing handoff shape.

Completed when:

Registering a synthetic filter with an existing handoff shape and no GUI code
makes it available in the authoring surface, validates through the graph-layer
compatibility query, round-trips through save/load, and leaves no required edit
in `src/sieve/gui/chain_model.py`, `src/sieve/gui/wizard_model.py`, or
`src/sieve/gui/filter_tab.py`. Any remaining shell-owned operation is absent
from the filter catalog by rule rather than mixed into it as a no-`filter_id`
entry.




