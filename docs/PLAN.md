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
- No files beyond what the item names — no per-tool `.md` (an open question
  below), no helper modules (`adr/a-tool-is-one-file.md`,
  `adr/ops-admission-is-two-tools.md`).
- When the item cannot be done as written, it stays `awaiting-review` with
  the blocker written at the bottom. Wrong-but-green is the one outcome the
  loop cannot detect; a stopped item is cheap.

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

## Phase 2 — Vertical slice

One tool, one video, end to end, before the rest of anything. `decode/`
verbatim (all six modules). `pipeline/dag.py` and `cache_key.py` verbatim;
`executor.py` verbatim plus one reviewed extension — honor lookahead by
delaying emission (a centered window is warmup + lookahead); `plan.py`
port-with-rename. One tool (`tools/downsample.py`) and a minimal `sieve run`
over an inline/YAML pipeline.

Two files arrive here that an earlier draft of this plan put later, because
`decode/`'s port reaches them and a verbatim port may not be trimmed to fit
its phase. `mutual/` — all four modules, 682 lines whose only outside
dependency is `psutil` — comes first: `decode/ffmpeg.py` and `prefetch.py`
import `available_cpus`, `PoolMeter` and the share constants, and
`test_decode_workers.py` is entirely about `resolve_workers`, so the caps are
its subject and not an incidental import. It brings its layer with it (v2
seats `sieve.mutual` between the decode row and `core`, with `core-purity`
covering both), which is a Phase-0 artifact edited under a Phase-2 step.
`storage/crop_writer.py` comes with `decode/` for one reason: `write_ffv1`
synthesizes the NTSC-rate file `test_decode.py` reads, and rewriting a ported
test's fixture is the decision the porting discipline refuses. Its first
consumer is therefore a test, and `crop` in Phase 4 lands only the tool.

Gate: `sieve run` on `synthetic_video` produces output; first per-tool parity
test — v3 output equals v2 golden arrays.

## Phase 3 — Schema v1

`core/pipeline_model.py` re-derived as schema v1: crop, span, and **detector**
are graph nodes natively (`adr/detector-is-a-node.md`). Kept verbatim in
spirit: `extra=forbid`, registry-blind, no
measurements in the artifact, checkpoints/outputs on `Project` not `Node`.
No v2 project imports and no module spells a v2 field name
(`adr/v2-does-not-import.md`) — schema v1 is written as if v2 never existed.

Gate: v3 save/load round-trip; a v2 field name appears nowhere in `src/`.

## Phase 4 — Tools, one at a time

Order: `crop` (its writer landed in Phase 2), `span`, `normalize`,
`rescale`, `block_signal`, `temporal_baseline`, `background_ema`,
`motion_history`, then **`detect` last** — re-derived as a centered windowed
tool on the Phase-1 lookahead contract, absorbing `detect/`'s composition.
Kernels port as the Phase-1 shape: one plain `run` per tool module,
`backend/dispatch.py` scaffolding stripped; a declared version on the spec
(entering the cache key) keeps cv2 kernels honest. v2's `core/ops/` does not
port: its math lands in `tools/detect.py`, and `ops/` appears only on the
two-tool rule (`adr/ops-admission-is-two-tools.md`).

Gate per tool: numeric parity against v2 goldens. For `detect`, the parity
target is v2's `detect/` **package output** (centered whole-record — what was
tuned against), not the trailing `filters/detect.py` kernel.

## Phase 5 — Full CLI and the oracle in CI

`cli/` port-with-rename (inspect and sweep; `detect_cmd` folds into
run/inspect — detection is a node now). `preview` is not here: every module
`preview_cmd.py` stands on — `bench/budgets.py`, `bench/metrics.py`,
`pipeline/preview.py` — is Phase 6, and the command is the headless surface
Phase 6's gate measures through, so it lands there with them. The
stirred-clip fixture (the one that
can disagree with itself) extracted from v2's parity test into shared
fixtures — in v2 it lives inside `tests/gui/test_gui_cli_parity.py`, which is
why the oracle could not run before the GUI did.

Gate: build the equivalent pipeline by hand in v2 (sibling worktree) and v3
— the frozen identity values make the correspondence mechanical — run both
CLIs, diff outputs at the product level, never the resolved plan.

## Phase 6 — Bench and the headless loop budget

`bench/budgets.py` + `metrics.py` verbatim (two-regime table, character-exact
pin test); `pipeline/preview.py` and `cli/preview_cmd.py` port-with-rename.

Gate: in-pipeline budgets (<100 ms slider→preview, <200 ms slider→graph)
measured headless through the preview session — the value proposition proven
before a single widget exists, so any later regression is attributable to the
GUI.

## Phase 7 — GUI, re-derived

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
| HPC handoff | a real cluster target |
| Materialization / result store / zarr | a user needing persisted results beyond the crop writer |
| Sink writers beyond `crop_writer` | a second output format someone asks for |
| Rate-changing kernels | a tool that needs one |
| v2 project import (`compat/`) | a real v2 project that must come over (`adr/v2-does-not-import.md`) |
| nox, completion tool, graph-system | something here concretely needing the mechanism |

## Port disposition

**Verbatim:** `core/types.py`, `decode/*`, `mutual/*`, `pipeline/dag.py`,
`cache_key.py`, `executor.py` (+ lookahead extension),
`storage/crop_writer.py`, `bench/budgets.py`+`metrics.py`,
`tests/conftest.py` fixture, most kernels.

**Port-with-rename:** `core/filter_base.py`, `filter_registry.py`,
`filters/*`, `cli/*`, `pipeline/plan.py`, `preview.py`, `gui/transport/`,
`gui/timeline/`, `gui/param_form.py` (as generator seed).

**Re-derived:** `pipeline_model.py` (schema v1),
`detect/`+`filters/detect.py` → centered `tools/detect.py`,
`document.py`+`commands.py` → intent command layer, everything else under
`gui/`.

**Dropped:** `backend/`, `gui/filter_tab.py`, `detect/`, `upgrade.py`,
`pipeline/materialize.py`, `cli/materialize_cmd.py`, `cli/detect_cmd.py`.

## Open questions

Each carries a decision item in `docs/todo/`, so a question blocking a step
is visible in the index rather than only here.

- Detect parity target: confirm centered whole-record (`detect/` package
  output) and abandon the trailing kernel as a target.
- Per-tool `.md` files: hand-written like v2, generated from `ToolSpec`, or
  dropped.
- First GUI cut: which v2 surfaces (wizard, replicate tab, history dialog,
  sweep) are in Phase 7 vs later.
- Phase 2 before Phase 3, which 02.2's deferral says cannot stand:
  `dag.py`, `cache_key.py` and `plan.py` take `Node`, `Pipeline` and
  `ClipRange` in their signatures, so "verbatim in Phase 2" and "the schema is
  re-derived in Phase 3" cannot both be true of them
  (`findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`).
  Either schema v1 moves ahead of the graph, or those three modules stop being
  verbatim ports. Dropping `backend/` already moves every node digest, so the
  second reading is closer to the truth than the disposition admits.
- The disposition above covers six of v2's fourteen `pipeline/` modules. The
  other six — `cache.py`, `crop_binding.py`, `lowering.py`,
  `resolve_source.py`, `series_collector.py`, `source_home.py` — plus
  `core/replicates.py` and `bench/sweep.py` have no verdict in either
  direction, and `sieve run` reaches four of them. A module with no verdict
  is the one thing this plan is supposed to prevent.
- `core/replicates.py` cannot come over as it stands:
  `adr/core-membership-is-closed.md` enumerates core's children and does not
  admit it, while VISION's project pane is built on replicates. Either the
  ADR is revised or replicates live somewhere else.
