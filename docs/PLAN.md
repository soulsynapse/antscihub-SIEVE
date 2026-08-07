# The port plan

v3 is v2 with the separation of responsibilities enforced from the first
commit. The evidence for the shape below is v2's own record: the non-GUI half
(~18k lines) had boundaries that held — four of its six import contracts exist
precisely because the plain layers contract couldn't say what mattered, and
those bespoke contracts worked — while `gui/` is 51% of the codebase and holds
nearly all the tangle (`filter_tab.py` at 2,321 lines and eleven jobs,
`document.py`+`commands.py` co-changing 7/7, 2,072 Qt-free lines stranded
above every consumer). So the rewrite is asymmetric: **port the half that
held, with the contracts installed first; re-derive the half that didn't.**
"Everything makes it over" was never the goal: a v2 decision comes over one
at a time, each on its evidence, and the ADRs record where v3 decided
otherwise.

The anti-v2.5 constraint governs every phase: each lands something runnable
and gated. No phase is a pile of specs.

Terminology: v3 says **tools**, not filters, with the identity values frozen
(`adr/tools-not-filters.md`). The kernel question is decided — no kernel
apparatus, one plain `run` per tool module (`adr/no-kernel-apparatus.md`).

Work is chunked into `docs/todo/` items attached to these phases;
`scripts/doc_index.py` generates the index and answers what to take next.

## Porting discipline

Every port item runs under these rules; items cite this section instead of
restating it.

- Read v2 through `git -C ../antscihub-SIEVE-v2 show main:<path>` — the
  worktree can hold uncommitted edits.
- Verbatim means identical modulo import paths and ADR-1's renames. Diff the
  ported file against the v2 blob before claiming done; any other difference
  is a decision, and a decision never rides along with a port.
- The ported v2 tests are the spec. Port the test file first and do not
  rewrite it: a test that must *change* to pass is a decision — stop and
  write the question at the bottom of the item. Deleting a case whose subject
  the item's cut list names is in scope; adapting one is not.
- A v2 declaration the item's cut list does not name and no v3 machinery
  consumes is refused, not carried (`adr/declared-means-verified.md`).
- No files beyond what the item names — no per-tool `.md`, no helper modules
  (`adr/a-tool-is-one-file.md`, `adr/ops-admission-is-two-tools.md`).
  Guidance is not a file in v3: what a tool is for goes in its module
  docstring while it is being written, and is promoted to a `ToolSpec` field
  in Phase 7 when the expander that shows it exists.
- When the item cannot be done as written, it stays `awaiting-review` with
  the blocker written at the bottom. Wrong-but-green is the one outcome the
  loop cannot detect; a stopped item is cheap.

A module **re-derived against schema v1** runs under a different rule for its
tests, and only for its tests. The algorithm is still copied line for line
and a deviation is still a decision — what cannot hold is "port the test file
first and do not rewrite it", because v2's cases construct `Pipeline`, `Node`,
`Backend` and `Replicate` literals and fail at import before reaching an
assertion. So the item carries a table instead: every case in the v2 file is
one row, and each row says *survives*, *replaced by* a named v3 case, or
*dropped* citing the decision that removed its subject. The item states v2's
case count up front, so a table with fewer rows than v2 has cases is visibly
wrong rather than quietly short. A re-derivation with no table is the failure
mode this whole discipline exists to prevent, wearing a different hat.

## Phase 0 — Skeleton and enforcement

Before any logic: the package tree (`core`, `tools`, `pipeline`, `decode`,
`cli`; `gui`/`bench`/`storage` declared in contracts but empty),
`.importlinter` adapted — not copied — from v2 (layers with `sieve.tools`, no
`detect` or `backend` layer; `core-purity`, `opencv-containment` with tools
the named exception, `headless` minus its detect entry; `gui-computes-nothing`
with an **empty exception list** and `unmatched_ignore_imports_alerting =
error` from commit one), CI running ruff + import-linter + pytest, and the
`synthetic_video` fixture ported verbatim.

Gate: CI green, and a deliberate violation on a branch proves each contract
fails red.

## Phase 1 — Core types and the tool contract

`core/types.py` verbatim (four dimensioned quantities, rational media time).
`core/tool_base.py` port-with-rename of `filter_base.py`, cut to what v3
consumes: id, version, params model, window shape, presentation stereotypes.
Declarations that served deferred machinery (cost estimates,
`backend_agnostic`, `frame_bytes_ratio`) arrive with their consumer, not
before. Two contract additions, as spec data:

1. **Declared lookahead** beside `warmup_frames`, same bound/refinement/
   cross-check discipline — what v2's trailing-only windowed contract lacked
   and what blocked the detector node.
2. **Presentation stereotypes** — each param field declares a population kind
   (`scalar-range`, `enum`, `span`, `region`, `point`, …) as Qt-free spec
   data, unread until Phase 7.

Every forgettable declaration fails loud at registration
(`adr/declared-means-verified.md`).

Gate: v2's `filter_base`/`types` unit tests ported and green; the `tool_id`
spelling gate (shrink-only) in place.

## Phase 2 — Schema v1

The artifact comes first, because everything that resolves a graph is written
against it. `core/pipeline_model.py` re-derived as schema v1: crop, span, and
**detector** are graph nodes natively (`adr/detector-is-a-node.md`). Kept
verbatim in spirit: `extra=forbid`, registry-blind, no measurements in the
artifact, checkpoints/outputs on `Project` not `Node`. No v2 project imports
and no module spells a v2 field name (`adr/v2-does-not-import.md`) — schema
v1 is written as if v2 never existed.

The replicate is part of it. v2 keeps `core/replicates.py` beside the model
because the model was already 1,273 lines, but a replicate is an ordered set
of named regions carrying per-node param overrides, which is a schema
question end to end — and `adr/core-membership-is-closed.md` admits
`pipeline_model.py` and not a second file, so putting it anywhere else is an
ADR revision bought for nothing. `DetectorSettings` does not come over —
detection is a node, and its settings are that node's params.

What does come over is everything about results at rest: `checkpoints` (node
ids whose output is written), `outputs` (the `Sink` records), and
`CropArtifact` with the `backs` matching that associates a written crop with
the box it was cut from by geometry and parentage rather than by name. These
are the fields Phase 5 builds the machinery for, and they are recorded on
`Project` rather than on `Node` or `Replicate` for one reason worth carrying
verbatim: none of them may reach a cache key. Turning a checkpoint off for a
cluster with the memory to skip it must not change a single key, or the
handoff stops being the same run.

Gate: v3 save/load round-trip; a v2 field name appears nowhere in `src/`.

## Phase 3 — Vertical slice

One tool, one video, end to end. `mutual/` first — `decode/ffmpeg.py` and
`prefetch.py` import `available_cpus`, `PoolMeter` and the share constants,
and `test_decode_workers.py` is entirely about `resolve_workers`, so the caps
are its subject and not an incidental import; it brings its layer with it,
which is a Phase-0 artifact edited under a Phase-3 step. Then `decode/`
verbatim, all six modules, with `storage/crop_writer.py` beside it because
`write_ffv1` synthesizes the NTSC-rate file `test_decode.py` reads and
rewriting a ported test's fixture is the decision the porting discipline
refuses — its first consumer is a test, and `crop` in Phase 4 lands only the
tool.

Then the resolved-graph layer, one module at a time: `dag.py`,
`cache_key.py`, `plan.py`, `executor.py` — re-derived against schema v1, not
ported. An earlier draft called the first three verbatim, which the import
graph refutes: they take `Node`, `Pipeline` and `ClipRange` in their
signatures, and dropping `backend/` moves the node digest by itself, since
`backend_agnostic` was the sixth position of the node key and Phase 1 cut it
(`findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`).
`pipeline/cache.py` comes verbatim with the executor — 114 lines over
`core.types`, the store the one execution loop writes into — and the
executor keeps its one reviewed extension: honor lookahead by delaying
emission, a centered window being warmup + lookahead.

Finally one tool (`tools/downsample.py`) and a minimal `sieve run` over an
inline/YAML pipeline.

Gate: `sieve run` on `synthetic_video` produces output; first per-tool parity
test — v3 output equals v2 golden arrays. Cache keys are not compared against
v2: the node digest moved when `backend/` went, so a key-level parity test
would be asserting that a decision this plan made did not happen.

## Phase 4 — Tools, one at a time

Order: `crop` (its writer landed in Phase 3), `span`, `normalize`,
`rescale`, `block_signal`, `temporal_baseline`, `background_ema`,
`motion_history`, then **`detect` last** — re-derived as a centered windowed
tool on the Phase-1 lookahead contract, absorbing `detect/`'s composition.
Kernels port as the Phase-1 shape: one plain `run` per tool module,
`backend/dispatch.py` scaffolding stripped; a declared version on the spec
(entering the cache key) keeps cv2 kernels honest. v2's `core/ops/` does not
port: its math lands in `tools/detect.py`, and `ops/` appears only on the
two-tool rule (`adr/ops-admission-is-two-tools.md`).

Gate per tool: numeric parity against v2 goldens. For `detect`, the parity
target is v2's `detect/` **package output** — centered whole-record, which is
what was tuned against — and not the trailing `filters/detect.py` kernel.
The trailing kernel is the shape that could not express what a detector does;
it is why the detector node blocked in v2 and why Phase 1 added the second
side of the window, so parity against it would certify the artifact this plan
replaced.

## Phase 5 — Results at rest, the full CLI, and the oracle in CI

Everything computed so far dies with the process. This phase is where a
result leaves the pipeline for a folder, which is half of what the product
is for: VISION's user checks off the outputs they want persisted before
pressing process, and the reviewer who reruns the project a year later gets
the same files back. Three parts, and only the first is a port.

**Crop artifacts.** `pipeline/materialize.py` port-with-rename — one
replicate's crop cut to an FFV1 file that opens in any player and opens in
SIEVE as an ordinary source with an identity of its own. Its verification
pass is not optional and does not get trimmed: v2 measured a *lossless*
encoding whose pixels came back wrong on every frame through the same reader
(`docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md` in v2), and the
guard is what stands between that and a silently wrong dataset. With it,
`resolve_source.py`, `source_home.py` and `crop_binding.py` re-derived: which
file a run opens, in whose frame numbering, and which of the four states a
reader is being shown when a record stops backing a box.

**Checkpoints and sinks.** `Project.checkpoints` and `Project.outputs` are
schema v1 fields (Phase 2) with no machinery under them, in v2 either — v2
validates both and then only *prints* the sink list from `run_cmd`. So this
is built, not ported: a run writes each checkpointed node's output to the
project folder, and `adr/declared-means-verified.md` is what makes it
mandatory rather than optional, since v3 does not carry a field nothing
consumes. The array format is a decision this phase makes and records; the
revival table holds zarr and a result-store API against a measured need.
`storage`'s never-line reads "a second output format *before someone asks*"
(VISION's component table) — this is the ask, and the second writer is the
answer to it rather than an exception to the line.

**What a tool can emit.** VISION's save screen shows *all the possible*
outputs the tools could emit, declared on the specs so the list cannot lie.
That declaration is a `ToolSpec` addition, and it arrives here rather than in
Phase 1 for the reason Phase 1 states: a declaration arrives with its
consumer, and this phase is the consumer.

Then the commands. `cli/` port-with-rename (inspect, sweep, and
`materialize`; `detect_cmd` folds into run/inspect — detection is a node
now). `preview` is not here: every module
`preview_cmd.py` stands on — `bench/budgets.py`, `bench/metrics.py`,
`pipeline/preview.py` — is Phase 6, and the command is the headless surface
Phase 6's gate measures through, so it lands there with them. The
stirred-clip fixture (the one that
can disagree with itself) extracted from v2's parity test into shared
fixtures — in v2 it lives inside `tests/gui/test_gui_cli_parity.py`, which is
why the oracle could not run before the GUI did.

Gate: build the equivalent pipeline by hand in v2 (sibling worktree) and v3
— the frozen identity values make the correspondence mechanical — run both
CLIs, diff outputs at the product level, never the resolved plan. Second
gate, and the one this phase exists for: a project with checkpoints runs,
writes its folder, and a rerun that reads the written artifacts produces
results identical to the run that computed them — with the checkpoint list
changed between the two runs and every cache key unmoved.

## Phase 6 — Bench and the headless loop budget

`bench/budgets.py` + `metrics.py` verbatim (two-regime table, character-exact
pin test); `pipeline/preview.py` and `cli/preview_cmd.py` port-with-rename.
`bench/sweep.py` and its command port here too, and they are not optional
tooling: v3 carried `mutual/shares.py`'s worker constants over verbatim,
chosen on v2's machine, and sweep is what says whether such a constant is
defensible at all — it measures the curvature of the response surface over
core sets and worker counts, and a flat optimum makes a per-machine constant
harmless while a sharp one makes it wrong everywhere it was not measured.
Having imported the constants, this repo owns that question.

Gate: in-pipeline budgets (<100 ms slider→preview, <200 ms slider→graph)
measured headless through the preview session — the value proposition proven
before a single widget exists, so any later regression is attributable to the
GUI.

## Phase 7 — GUI, re-derived

The first cut is a capability, not a surface list: open a project, see the
pipeline the way VISION describes it, tune a param with the graphs refilling
inside the budget, check off the outputs to keep, run. Everything v2 had
beyond that — the wizard, the replicate tab, the history dialog, the sweep
view — waits, and each waits for a reason rather than for room: the history
dialog would make undo a visible object, which is the opposite of the two
stacks of whole values the v2.5 spike settled on. A layout can be rearranged
later at low cost; a capability that implies machinery cannot, which is why
the cut is drawn here and not at the widget level. Guidance text lands in
this phase as a `ToolSpec` field, promoted from the tool docstrings that hold
it until the expander exists to read it.

Not ported; `filter_tab.py` is never opened. The starting skeleton is the
v2.5 spike's `gui`/`session` packages, with v2's held parts ported into it
(`adr/gui-base-is-the-v25-spike.md`). One generator reads `ToolSpec`
presentation stereotypes and emits param widgets — adding a tool adds zero
GUI code unless it declares a new stereotype. Handoff services generalize
crop-as-contract: a `region` param gets the canvas-draw surface, `span` gets
timeline handles, a future stamp tool declares `point`; a handoff's output is
only a param value, entering through the same command path as a spinbox edit.
One command layer is the document's only writer, keyed by intent kind
(SetParam, DrawRegion, SetSpan, AddNode) — dissolving the document/commands
co-change. Undo/redo is two stacks of whole immutable pipeline values in a
Qt-free session layer, not command inversion — the v2.5 spike proved the
shape (`proto_sieve/docs/DECISIONS.md`, 2026-08-03): moving a pointer through
values is cheap on a small value, and prefix reuse falls out of the
executor's cache with no history-aware code. Same source, the one boundary
*not* to draw: canvas and widget-control are genuinely coupled — a dragged
crop box is the active control's current step drawn elsewhere — so no import
fence between them; the handoff services above are that coupling given a
shape. Port-with-care: `gui/transport/` and `gui/timeline/`, whose
contract held in v2. The GUI renders values, emits intents, holds view state;
it computes nothing, and the Phase-0 empty exception list is now load-bearing.

Gate: GUI/CLI parity at the executor level on stirred-clip; both budget
regimes measured through the GUI; the exception list still empty.

## Not built, and what revives it

| Not built | Revived by |
|---|---|
| GPU execution, `backend/` type system | a kernel measured over budget on CPU on target hardware, and a second backend actually written |
| `detect/` as a package | never — dissolved into `tools/detect.py` |
| Process isolation / workers | a measured stall prefetch cannot hide |
| Job templates and chunking across nodes | a real cluster target — the handoff itself is built, being the saved file plus `sieve run` executed headless (VISION) |
| A result store API / zarr as the on-disk format | a result too large or too random-access for a file per checkpoint — the folder of files is the format until then |
| Sink writers beyond FFV1 video and the array format Phase 5 picks | a third output format someone asks for |
| Rate-changing kernels | a tool that needs one |
| `pipeline/lowering.py` — crop and scale pushed into the decoder | a loop budget missed without it (Phase 6's measurement), which is the only evidence that would justify 215 lines reaching across the graph, the schema and `decode/lowered` |
| v2 project import (`compat/`) | a real v2 project that must come over (`adr/v2-does-not-import.md`) |
| nox, completion tool, graph-system | something here concretely needing the mechanism |
| `bench/retention_trace.py` — recording a tuning session and replaying it through candidate proxy-retention policies | a Phase-7 proxy ring plus a proposal to change its policy; the module exists because a reasoned guess about retention is not adoptable without a replay, and there is nothing to replay until the ring is built |

## Port disposition

**Verbatim:** `core/types.py`, `decode/*`, `mutual/*`, `pipeline/cache.py`,
`storage/crop_writer.py`, `bench/budgets.py`+`metrics.py`+`sweep.py`,
`tests/conftest.py` fixture, most kernels.

**Port-with-rename:** `core/filter_base.py`, `filter_registry.py`,
`filters/*`, `cli/*`, `preview.py`, `gui/transport/`, `gui/timeline/`,
`gui/param_form.py` (as generator seed).

**Re-derived:** `pipeline_model.py`+`replicates.py` (schema v1),
`pipeline/dag.py`, `cache_key.py`, `plan.py`, `executor.py` (+ lookahead
extension) against that schema, `detect/`+`filters/detect.py` → centered
`tools/detect.py`, `document.py`+`commands.py` → intent command layer,
everything else under `gui/`.

**Dropped:** `backend/`, `gui/filter_tab.py`, `detect/`, `upgrade.py`,
`cli/detect_cmd.py`.

**Phase 5, results at rest:** `pipeline/materialize.py` and
`cli/materialize_cmd.py` port-with-rename; `pipeline/resolve_source.py`,
`source_home.py` and `crop_binding.py` re-derived against schema v1 — they
are the read-back path, and a written crop that nothing can read back is a
file, not an artifact.

**Landing later than v2 would suggest:** `pipeline/series_collector.py` in
Phase 6 — it assembles a node's per-frame outputs into the series a graph is
drawn from, which is the plotting path and not the run path.

## Open questions

Each carries a decision item in `docs/todo/`, so a question blocking a step
is visible in the index rather than only here.

None open. The four that stood here on 2026-08-07 — the detect parity
target, per-tool documents, the first GUI cut, and the last two `bench/`
modules — were answered in the same pass that answered the phase order, and
each answer is in the phase it binds rather than in this list. A question
returns here when something measured contradicts one of them.
