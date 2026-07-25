# Architecture digest

[INTENT] The invariants a session codes against, extracted from
`ARCHITECTURE.md` and `FILTER_CONTRACT.md`. Enough to judge whether a change
belongs; not enough to design a subsystem. The routing table in
`00-agent-orientation.md` says when the source is worth loading.

[STALE WHEN] `ARCHITECTURE.md` §1, §3, §5.5, or §14 changes, or the filter
contract's required declarations change. Sources win on disagreement.

---

## The commitment everything else serves

[STABLE] The tuning loop is the product. A layer that adds measurable latency
to the interactive loop is a regression regardless of how clean it is. Two
regimes, both load-bearing: pre-pipeline (open → scrub → replicate cut) must
feel like a video editor; in-pipeline (slider → graph) must feel like direct
manipulation.

[STABLE] The latency budgets in `ARCHITECTURE.md` §1 are the operational
definition of that commitment, not aspirations. They are per-interaction wall
times on a mid-range laptop with no discrete GPU required for the pre-pipeline
regime. A PR regressing any budget past its stated margin needs explicit
justification. The table is short and load-bearing enough to read in full at
its source rather than be paraphrased here — paraphrasing invites drift in the
one place drift is most expensive.

## Layer model

[STABLE] Dependencies run one way. Each layer knows the layers below it and
never those above:

```
gui/  cli/  review/     ← user-facing
bench/                  ← observation
workers/                ← execution isolation
pipeline/               ← orchestration (DAG, executor, cache, preview)
backends/  io/          ← runtime/storage
core/                   ← pure logic (filters, contract, dtypes)
```

[STABLE] The enforced consequences: `core/` imports nothing above it and no
Qt, Zarr, or subprocess. `pipeline/` never imports Qt. `bench/` never imports
Qt, so headless and CLI runs can observe without a GUI toolkit — the QObject
adapter over the metric bus lives in `gui/`. `gui/` reaches `workers/` only
through `pipeline/`. This is the mechanism that makes CLI and HPC parity real
rather than aspirational — a violation is not a style problem, it is the loss
of a product guarantee.

[INTENT] The rule is encoded as a machine-checked contract rather than
enforced by review. See `NOTES.md` for its current home.

## Component placement

[STABLE] `ARCHITECTURE.md` §14 holds the authoritative tree: which module owns
which responsibility, one responsibility per file. Placement questions are
answered there rather than by precedent from neighbouring code. Two invariants
worth carrying without reading it:

- A filter is `<name>.py` plus `<name>.md` guidance sitting beside it in a
  category directory under `core/filters/`. The pair is the extension unit.
- Each load-bearing contract has exactly one owning module — the Zarr store,
  the results table, the cache, the tracer. Callers do not construct these
  independently; they go through the owner.

## The four commitments

[STABLE] Stated in `ARCHITECTURE.md` §1 and never violated:

1. **The filesystem is truth — at rest.** Materialized artifacts are legible
   by navigation without SIEVE running. During interactive tuning truth lives
   in the decoder and in-memory state; the contract binds at compaction and
   terminal output, not on every slider drag.
2. **The pipeline is a data structure.** GUI, CLI, and HPC consume the same
   serialized artifact. No GUI-only state affects execution. Pre-pipeline
   interaction state (scrub position, zoom, layout) is UI state and stays out
   of the artifact.
3. **The filter is the extension unit.** One class plus one markdown file.
   GUI, CLI, cache, and HPC handoff pick it up with no other change.
4. **Nothing materializes without reason.** In-memory while editing;
   compaction is user-initiated or explicitly pressure-triggered.

## The DAG

[STABLE] The pipeline model is a directed acyclic graph from day one, because
filters fork and merge. A linear pipeline is a degenerate DAG and renders
identically. Consequences that ripple: cache keys include upstream content
hashes so siblings don't invalidate each other; materialization happens at a
node, not a step index; the schema is a node list with explicit `inputs:`
references rather than an ordered array with implicit chaining.

## The pre-pipeline loop

[STABLE] Opening, scrubbing, cutting replicates, and selecting a
representative clip do not route through the pipeline executor, the cache, or
a worker subprocess. A scrub is a decoder call and a widget repaint. Decode
for display stays in the main process (with a decoder thread where
appropriate); the subprocess boundary exists for filter execution.

[STABLE] Treating crop and replicate selection as pipeline nodes is
architecturally tempting for uniformity and is rejected: it routes every scrub
through DAG construction, cache-key derivation, and IPC. Replicates become
*sources*, not filters — the crop is intrinsic to the source, and the DAG
contains no crop node for it.

[STABLE] Replicates materialize in the background on commit rather than
staying virtual. Cropping a small ROI out of an HD decode is where the large
speedup lives, and keeping the crop virtual pays the full decode cost again on
every later scrub, filter add, and slider drag. The UI reports progress
non-modally and the user is not blocked; the executor swaps its source pointer
when the materialized version is ready. Materialized replicates are source
artifacts owned by the project, keyed to the replicate record — they are not
cache entries and are invalidated by geometry edits, not by pipeline changes.

[STABLE] The handoff point is the first filter add. Until then no worker
process needs to exist.

## Filter contract

[STABLE] `docs/02-requirements/FILTER_CONTRACT.md` specifies it; read it in
full before writing a filter. The shape: a Pydantic model plus one or more
backend implementations, registered by decorator, colocated with a markdown
guidance file whose existence the registry validates.

[STABLE] Every filter declares — and registration fails loudly at import time
if any declaration is missing: identity (`name`, semver `version`), input and
output stream specs, output topology, warmup frames, streaming capability,
determinism, storage dtype policy, backend set, a cost estimate that must not
run the filter, and the process implementation. Parameters are Pydantic fields
and are the *sole* declaration — GUI widgets, CLI flags, YAML schema, cache
key contribution, and cost model all derive from them, and a parallel
definition anywhere is a contract violation.

[STABLE] Discovery is by explicit import in `core/filters/__init__.py`, not
filesystem scanning. Registration failure is intentional and loud: a broken
filter does not silently disappear from the registry.

[STABLE] Filters do not know whether they run in preview or full-video mode.
Warmup is a filter property; composing it along temporal paths is the
executor's job. Filters read calibration from `ctx.replicate` rather than
storing it as parameters, which is what keeps temporal frequencies in Hz and
spatial scales in mm without every filter reinventing calibration.

[STABLE] Filters do not select their own backend, read from disk, spawn
threads, or mutate global state through the context.

## Guidance and measurement posture

[STABLE] Guidance is data: markdown beside the filter, rendered by one widget.
Refining suggestions is a documentation change, not a code change.

[STABLE] SIEVE reports delta characterization, never a preservation score. For
a candidate swap it reports observable differences against the user's current
pipeline — detection count, temporal lag, spatial footprint, cost — and never
claims the alternative is closer to truth. Where the user supplies labeled
intervals, supervised metrics use them; absent labels, SIEVE does not invent
ground truth. More smoothing is a different point in a (fidelity × latency ×
economy) space, not a wrong answer, and which point is correct is a domain
judgment SIEVE is not entitled to make.

## UI posture

[STABLE] The six-region layout in §15 is the maximum GUI, not the default. The
tool opens into video, overlay toggles, a curated toolbar, and graphs.
Operations list, operation detail, guidance, and benchmark HUD are dockable and
closed on first launch; a user who never opens them still has a working tool.

[STABLE] Adding a filter to the codebase does not add it to the toolbar.
Toolbar contents are a curated project-level list drawn from filters that
declare themselves candidates. New filters do not silently appear in a user's
primary workflow.

[STABLE] The DAG minimap stays hidden until the graph forks.

## Rule of three

[STABLE] From `SIEVE-HANDOFF.md`, and consistent with the architecture
reserving space it does not yet occupy: no plugin system before three plugins,
no DAG executor before a fork, no backend dispatch before two backends, no
cache before caching is a *measured* bottleneck. The architecture reserving
room for a capability is not a licence to build it early.
