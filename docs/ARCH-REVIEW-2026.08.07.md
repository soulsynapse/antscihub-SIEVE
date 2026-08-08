# Architecture review, 2026-08-07 — parked, not adopted

Status: **holding doc.** Nothing here binds. Each conclusion becomes real only
when it is minted as an ADR, folded into an item, or refuted — and several of
the items it names were edited by the loop the same evening this was written,
so re-read every cited item at adoption time rather than trusting this
snapshot. Kendrick circles back to disposition it; until then the loop should
not act on it.

Evidence base: a four-way survey (v3 source read against VISION's six
scenarios; v2's findings/completed-todo/todo record; v1's full architecture;
v2.5's spike and session archive), plus the reviewer logs of the evening's
last five runs.

## Verdicts against the five goals

**Tools do what they say — holds, best of the four generations.** Emissions
refused in both directions at registration (`core/tool_base.py`), stereotypes
total over the params model, `warmup_kind` separating lead-in from
cache-admission, rate/selection flags cross-checked against method overrides.

**A new tool is one file — holds.** Ten tools, no cross-tool imports,
registration is one decorator, discovery is a package scan with an AST guard.
At 50 tools the scan is non-recursive (flat directory) and the pressure lands
on the closed vocabularies, which is the design.

**Fast and responsive — proven headless for the reference workload, with one
structural hole.** `background_ema` is `EPSILON`-warmup, so it is unkeyed and
denies keys to everything downstream (`pipeline/preview.py`'s own docstring:
the whole lead-in re-runs on every render). VISION's background-subtraction
scenario therefore lands on the uncacheable path by construction, and the
stated remedy — a materialized checkpoint upstream — sits behind a three-deep
gate chain: checkpoint read-back → source-tool migration
(`docs/todo/crop-serving-and-checkpoint-read-back-become-source-tools.md`) →
the first source tool
(`docs/todo/the-first-source-tool-moves-the-three-single-root-assumptions.md`),
which nothing schedules.

**User can do the things — three of six VISION scenarios expressible today.**
The one-file outsider tool works now. The reviewer scenario is half-real
(emissions yes; external inputs now have an item after `dd333f8`;
"deterministic run as a param" exists nowhere — `ToolSpec.deterministic` is a
spec constant no param can express). The merge, the broadcast-as swap, and the
folder picker are each blocked on named absences, below.

**GUI rework is plug and play — unproven, and the plan understates the gap.**
Spec data suffices for a per-kind generator on scalar/enum tools; the
exceptions are the front-page tools: composite params (`crop.region`, detect's
bands) hit the JSON-Schema wall
(`docs/todo/a-composite-parameter-prints-no-shape-and-no-bounds.md`), the
bands are declared `SPAN` — ruled a lie, `BAND` ruled the sixth stereotype and
not yet in the enum (`docs/todo/a-band-has-no-stereotype-of-its-own.md`) — and
no `PATH` stereotype exists. The intent-kind list VISION calls "the list of
required bindings for a complete GUI" appears nowhere in the tree.

## The merge (VISION's primary scenario)

Structurally refused, not merely unbuilt: `Pipeline` raises "two edges feed
X" (`core/pipeline_model.py`), `accepts` is one stream, `ToolRun` takes one
window. The port-labeled shape is settled
(`docs/todo/a-merge-keys-its-inputs-by-port.md`) and two of the sites that
predict a second input already disagree with two others
(`docs/todo/a-nodes-inputs-are-labeled-and-variadic.md`, open, high). Two
costs are written down nowhere and should be priced into the item before it is
picked up:

- The executor's no-alignment invariant breaks. Two parents of different lag
  hand a node frames with different indices at the same step
  (`executor.py`, the `emitted[parent]` read and the `max()` over parent
  lags); a merge needs per-port delay buffers of `max_lag - lag[port]`. New
  machinery in the loop, not a signature change.
- The node key's one `upstream` slot becomes ordered `(port, key)` pairs — a
  `HASH_VERSION` bump; the whole store turns over.

## The undesigned semantic axis

"Broadcasts as generated background" has no mechanism at any layer:
`ArraySpec` is structural, `ElementKind` is a counting noun, `Emission` is a
product a user picks and is read by no graph machinery. Three scenarios (the
swap, the folder picker, the offering shortlist) sit on this one axis, and the
source-tool item explicitly reserves the decision — Emission-name vs a new
`ElementKind`-member reading — for Kendrick. `e0370f5` settled the negative
(`admits` is not the offering predicate); the positive keying is the open
half. This is the largest single undesigned surface in the system.

## What v1 still does better, mechanism by mechanism

The tuning loop's *feel* in v1 rests on three mechanisms absent from v3's
plan:

1. **The `TrackStamp` split** (`core/live_track.py` in
   `../antscihub-optical-flow-detector`): params that invalidate the retained
   expensive intermediate (band power) are separated from params re-derived
   from it instantly — a threshold drag re-tunes the whole clip without
   graying anything. v3's invalidation is cache-key transitivity only; it has
   no expression of "this edit is cheap over retained upstream output."
   Bounded-warmup admission covers `block_signal`/`detect` per-frame; nothing
   gives a downstream-threshold drag v1's instant whole-clip response.
2. **The interaction-cadence layer**: three signals per drag
   (pressed/scrubbed/committed), a measured debounce table (60 ms scrub,
   200 ms retune, 500 ms knob, 1 s sidecar save), display-width capping
   (`DISPLAY_MAX_W = 1280` — ~15× less pixel traffic), newest-request-wins
   with no queue. Phase 7 names this "a transport layer" and defers it; v1's
   record says it is where half the perceived speed lives.
3. **The three-state coverage vocabulary**: unexamined / examined-and-quiet /
   examined-under-stale-settings, painted as different surfaces
   (`gui/explorers/detection_timeline.py`). v2's
   `coverage-and-detection-lanes.md` names collapsing the first two as v1's
   own standing failure. VISION's "a stale frame is labeled stale" gestures at
   it; no v3 item owns it.

## Constraints currently overlooked

- **Undo granularity.** ADR-14's two-stacks-of-whole-values is right for the
  session layer, but v2 tried collapsing commands onto one before/after shape
  and reverted it (`937ac91` in v2): every Ctrl+Z became a full broadcast and
  the parameterized signal lost its producer. In v3 the GUI must diff two
  whole pipeline values to know what changed, or every undo redraws
  everything against a <200 ms budget. Nothing in Phase 7 answers
  change-notification granularity.
- **Schema forward-evolution.** `extra="forbid"` plus restamp-to-current is
  the combination v2.5's Exchange 1 names as data-destroying once two builds
  coexist (a newer build's field is a parse error here; a save strips what a
  reader tolerated). v2's record: five schema versions in thirteen days, four
  purely additive, zero transform code needed — the cheap discipline is
  additive-only plus refuse-the-future, and it is recorded nowhere in v3. The
  `Edge.port` bump will be the first test.
- **Cost estimates.** VISION's process screen revives declared cost models;
  v2.5 explicitly cut them in favour of extrapolating from the sample the
  user already ran, and v2's `lowering.py` audit is the local evidence that
  declared constants drift (hardcoded versions silently disabling behaviour).
  Measurement-based estimation needs no `ToolSpec` field at all, which
  `adr/declared-means-verified.md` should prefer.
- **Decode lowering's unmeasured seek.** If Phase 6 ever revives lowering,
  v2's findings carry over (route in the cache ancestor, `exact=1`,
  subprocess as a resource tenant) plus the hole v2 never closed: nobody
  measured a scrub on the lowered route, and the subprocess respawns on every
  non-sequential read.
- **Project identity/registry.** The v2.5 spike's `app_state` cannot port
  without a notion of "the projects the app knows about" (v2.5 built a
  registry and recorded why scanning a directory is wrong — it stands in for
  a user's decision). VISION's opening screen is that registry. No item
  covers it.

## Utility given up that may be wanted back

Ranked by the strength of the record behind it:

1. **Detection-quality feedback** (v2 `annotation-spans.md`: "the deepest gap
   between VISION as written and a tool that produces defensible results" — a
   user learns what a threshold drag cost and nothing about what it caught).
   v1 had the corpus half: marks carrying full provenance, which validated
   the wingbeat band against 152 hand-verified bouts. Neither half is in v3.
2. **Autosave + history snapshots** (v2: 115 lines, 190 snapshots on disk,
   one hand-repaired corrupted project file as lived evidence). v3 deferred
   the history *dialog*; the safety net is not the dialog, and nothing owns
   crash/corruption recovery of the project file.
3. **Sampling strategies** (v1 `core/process_plan.py`: van der Corput
   bisection so any prefix of a whole-video pass is spread over the clip;
   gaps-only; budget-against-uncovered). Real incremental-recompute utility
   with an anti-bias argument; no v3 equivalent.
4. **Surrogate calibration** (v2: same settings on longer clips produce more
   detections for no biological reason). Scientific-validity debt.
5. **v2.5's two authoring ideas** the offering item does not cover:
   greyed-ineligible with the missing requirement named, and backward
   chaining from a desired output.
6. **The CSV sink** — unwritten across three generations; `run_cmd`
   currently refuses projects with sinks.

Dropped things the record says stay dropped: `backend/` (zero GPU kernels
ever; v2's own arithmetic has a per-node PCIe round trip losing to the CPU
kernel), `graph-system/` (one commit, zero findings produced), the migration
framework (four of five bumps needed no transform), per-tool `.md` files
(their main consumer was the wizard).

## Signals from the evening's reviewer logs

- **41 open items have no `done_when`** — printed by `doc_index.py --next`
  and carried as "inherited, not acted on" in every review verdict. Items
  without executable criteria are the wrong-but-green channel; any fix-up
  pass should price this, not inherit it again.
- **Tailored review prompts go stale in the queue** — the 19:02 review
  cancelled three pending tailored reviews whose subjects the tree had left.
  If a queued prompt is the only home of a case list, cancellation discards
  it; content meant to survive belongs in an item, not a queue entry.
- **A consequence that lives only in findings recurs until it reaches a
  loaded file** — the here-string trap was diagnosed at 03:02 and recurred
  four times before reaching CLAUDE.md at 18:48. Decisions from this review
  must land where the loop actually reads: items with criteria, ADRs cited by
  items, CLAUDE.md for platform rules.

## Constraint on any fix-up pass over the items

Reviewer edits fold refinements into items, delete item text on completion
(recoverable only via `git log --diff-filter=D`), and treat the item file as
the single home of a decision's reasoning. Several items this review cites
were edited by the loop after the survey snapshot (`dd333f8`, `d21ad8b`,
`e0370f5`, `dcdd56f`, `9b6fd25`). Therefore: re-read each item at edit time
and extend rather than replace; never rewrite an item from this doc's
description of it; leave `awaiting-review` status and the queue alone so
pending runs are not orphaned.
