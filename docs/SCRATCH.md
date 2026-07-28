# Scratch

Running notes from the fast pass of 2026-07-28. Not a doc — the item files and
`docs/completed-todo/` still own the record, and nothing here has been moved
there yet.

---

## Housekeeping first: a prior session's sweep was uncommitted

The tree had 99 modified files on arrival — the "entries lose their bodies"
sweep (3.8k lines of completed-entry bodies removed, `tools/complete_item.py`
and CLAUDE.md rewritten to say the frontmatter *is* the entry, plus the new
comment/split rules). Committed as `4a11c01` on its own so everything below is
separable from it. Not my work and not attributed as anyone's.

## proxy-retention-policy — the fraction, done

`RENDER_RING_SHARE` was `floor_bytes=256 MB, fraction=0.0`, with the zero
deliberate: how much of a bigger machine the ring deserves was the item's
question and growing it elsewhere would have decided it by side effect. The
finding answered it (capacity beat eviction policy ~60:1), so:

- `gui/concurrency.py` — `fraction=0.01`. Arithmetic for the choice: the
  finding's machine had 68.4 GB available, reserve is 4 GB, so the budget is
  64.4 GB and 1% is ~644 MB — ~700 gray 1280-wide proxies at 921,600 B each,
  against the ~720 where that session's working set saturated. Sized to reach a
  large machine's own knee, not to hardcode 720.
- Below ~26 GB total the fraction falls under the 256 MB floor and the floor
  resolves, so a small machine pays nothing for this. That is also exactly the
  case the finding said it could not settle, left as it was.
- `gui/render_ring.py` docstring updated — it said the bound was fixed "until
  the item replaces the number with policy".

**Still open in that item:** the scrub half. 16 scrub events, 0.00% hit under
every policy, no sample. Reopening the eviction rule is a *stall*-length
argument, not a throughput one, and needs a session that scrubs.

## headless-detection — built, including the two things that fall out

New `src/sieve/detect/` (layers: sibling of decode/storage/backend, above
core, below pipeline; added to the headless no-PySide6 contract).

- `detect/detector.py` — `DetectorUpdate`, `detect`, `settled_for`, `gate_to`.
  Takes a resolved `DetectorSettings`, never a `DetectorState` and never a
  `Project`, as the item required.
- `gui/chain_model.recompute` and `gui/detector_worker.settled_for` are now
  two-line adapters that convert the live state at the boundary; `gate_to`
  moved outright and `filter_tab` imports it from `sieve.detect`.
- `DetectorState.to_settings()` added — the item claimed it already existed; it
  did not, only `as_settings_changes()` returning a dict for partial submits.
- `sieve detect` in `cli/detect_cmd.py`, wired in `cli/app.py`.
- `tests/integration/test_cli_detect.py`, three tests, no `gui` marker.

Two decisions the item did not make, both taken here:

1. **Which node's output is the series.** The sink, and a graph with two sinks
   is refused with `--node` named rather than one being picked. Which series a
   detection was taken over is part of what the answer means.
2. **`Project.detector is None`.** Reported as "this project has no detector,
   so it claims nothing" — not resolved to `DetectorSettings.default_for(fps)`
   and not printed as zero intervals. Two distinct absences (never tuned vs
   tuned-but-disarmed) and neither is "found nothing".

A whole-clip CLI pass is `final` by construction, so none of the partial-record
frontier arithmetic runs — `settled_for(..., final=True)` is the whole record.

**Not done, and it is the next obvious step:** the HPC item
(`docs/todo/hpc-handoff-and-review-mode.md`) rests on a premise this item
falsified — "HPC consumes the same serialized DAG the CLI does", true of the
executor and false of detection. That is now true of detection too, and that
item does not know it yet.

## the-decode-format-has-six-derivations — done, plus a loud break

**Measured first, as the item asked.** `graph_needs_chroma` over a three-node
chain: median 8.9 us, p95 13.2 us, max 77.5 us, no caching anywhere on the path
(checked — a memoized `Dag.build` would have made the number meaningless). The
render thread paid ~18 us per render inside a 3000 ms span. The cost half is
nothing; the correctness argument carries the whole change. Written up as
`docs/findings/2026.07.28-the-decode-format-is-free-to-derive.md`.

**What changed:**

- `RenderRequest.luma` — a field, derived in `PreviewRunner._request`, which is
  now the only constructor. The two render-thread derivations two methods apart
  are gone, and the `Dag` build leaves the render thread as a side effect.
- `ExecutionPlan.luma` — `not dag.needs_chroma`, for anything holding a plan.
- `executor._check_format` + `FormatMismatchError` — **the addition the item did
  not ask for and the one that matters.** The item's own "what breaks if this is
  wrong" was *nothing loudly, which is the danger*. Now a reader whose format
  disagrees with the plan's keys raises on the first decoded frame, per frame
  (one enum comparison; a first-frame check would miss a reader that changed
  format mid-run).

**It caught things immediately**, which is the argument for it: ten tests were
handing BGR frames to plans keyed for luma. `tests/unit/test_executor.py`'s
`ListSource` and `tests/integration/test_executor_run.py`'s `VideoReader` were
both opening colour under luma plans — harmless in a test, exactly the poisoned
cache in a session.

**Fixture limitation found on the way, and left.** `conftest`'s synthetic video
marks frame *n* by the blue channel at `n * 5`. BT.601 weights blue at 0.114, so
one frame of separation is ~0.6 luma levels — inside `mp4v`'s own error. Under
the luma decode, adjacent frames are indistinguishable: `test_executor_run`'s
"these are not four copies of one frame" went from 4 distinct to 3. Weakened to
`>= 3` with the reason stated in the test. **CLAUDE.md advertises the opposite**
("a test can assert *which* frame a seek landed on"), and that is now true only
on the colour path, which most graphs no longer take. A fixture whose marker
survives both formats is its own item and probably a real one — every test that
asserts `blue == n * 5` would move with it.

**Two of the six sites remain, correctly.** `cli/preview_cmd.py` and
`cli/materialize_cmd.py` must choose a format *before* they have a plan, so they
call `graph_needs_chroma` once each — one derivation per command, not a second
answer. `cli/run_cmd.py` and `cli/detect_cmd.py` read it off their own `dag`,
which is the same object the plan's keys come from.

## budget-checks-under-ambient-load — the audit landed, the diagnosis did not

**The item's second diagnosis does not reproduce.** It claimed the slowdown was
a deterministic function of how much of the suite pytest had collected. Tested
directly: importing all 97 test modules in a fresh process changes the reading
by under 1% (81.5/81.8 before, 82.3/82.5 after), and `pytest -k density_rebuild`
under full collection passed 5/5. So "it is not ambient load, it is collection"
is wrong, and the original observation was the flaky-looking thing it looked
like.

**What is actually true is worse.** Fresh processes on the reference
workstation today: 89.3, 92.8, 93.3, 99.7 ms at B = 16,384 against a 100 ms
ceiling — where the finding that set the bound measured 84.1 ms the same
morning. Inside pytest, 100-118 ms. Scaling confirmed linear: 23.6 / 47.0 /
97.6 ms at B = 4,096 / 8,192 / 16,384. The headroom is smaller than the
machine's own state-to-state variation, so **no statistic and no retry policy
can adjudicate it** — which is the one thing the item was sure of and the one
thing that turned out not to matter.

**The audit's real result, and it stands on its own.** The statistic is the
kind of claim, not a house style, and the two kinds in this suite were already
right by accident:

- `density_rebuild` is a *capability* bound — can the machine do it at all —
  so `min` is correct, and it already used `min`.
- `open_to_first_frame` / `scrub_settle` are *felt latency* — a ceiling only
  the best round meets is one a user misses half the time — so `median` is
  correct, and they already used `median`.

Nothing was written down anywhere, which is how the item came to recommend
best-of-N globally. Now in `tests/bench/gate.py` as `BEST` / `TYPICAL` with the
argument, plus `within_budget`, which re-takes a missed batch up to three times
before believing it. The limit never moves — this is deliberately not the
item's option (3); what changes is how much evidence a regression claim needs.

**One real bug found while converting.** Pre-building nine 39 MB arrays so
every retry had one made the thing under test 50% slower (82 -> 150 ms). One
array is 600 x 16,384 float32; the binning is bandwidth-bound over it. Retries
now generate lazily, so the resident footprint is the same on the tenth reading
as on the first. A benchmark whose own fixture setup dominates its subject is a
shape worth watching for elsewhere.

**Then Kendrick overturned the premise, and it is the important part.** The
whole question was framed as "what should the cap be", and there should not be
a cap. `MAX_BLOCKS` is a dev-workstation timing turned into a refusal on a
*scientific* parameter; the HPC target has neither this machine's clock nor
this refusal's justification. The user may ask for whatever they want; the
obligation is on the app to stay responsive and to *say what is costing the
time* in a persistent field. That is the point of having budgets at all.

Written up as `docs/todo/budgets-attribute-cost-they-do-not-cap-it.md` with the
order fixed (off-thread rebuild first, then the cap comes off, then the HUD
attributes), `density_rebuild` declared in `IN_DEBT` against it, and the
`MAX_BLOCKS` docstring corrected in place so nobody derives anything new from
it or tunes it to a better wrong value.

## budgets-attribute-cost — step 1 started, half done

`density_surface(band_power) -> DensitySurface` extracted from
`DensityPlot.set_series`: the max, the bincount histogram, the log1p norm and
the ramp lookup, producing an ARGB array and nothing Qt. `set_series` gains an
optional `surface=` for a caller that already paid for it, guarded by the same
identity check that makes the cheap tier free — a surface handed for a
*different* array would put one population's picture under another's axis, and
the identity check is what makes accepting one safe. Pure refactor, no
behaviour change, suite green and the `density_rebuild` debt xfails visibly in
`nox -s benchmark`.

**What is left of step 1, and it is the load-bearing half:** nobody passes
`surface=` yet, so the binning is still on the GUI thread. The wiring is

- `gui/detector_worker.derive` calls `density_surface(update.band_power)`
  beside its `morlet_power` — it already holds that array on its own thread —
  and carries the result on `DetectorResult`.
- `gui/filter_tab.py:1244` and `gui/wizard.py:519` pass `surface=result.density`
  instead of letting the widget bin.
- The cheap tier is untouched by construction: it hands the same array back and
  never reaches the binning.

Then step 2 (the cap comes off) and step 3 (the HUD attributes) as the item
sets out. `MAX_BLOCKS`'s refusal branch now lives in `density_surface` and is
one `return` to delete when the responsiveness work lands.

## budgets-attribute-cost — all three steps, done

**Step 1's load-bearing half (the wiring).** `derive` now binds the surface
beside `morlet_power` on the detector thread and carries it back:
`DetectorResult.density` (a `DensitySurface`) and `density_ms`. `filter_tab`
holds the surface with the update and hands it to both plots — its own and the
wizard's, which is a second view of the same array and would otherwise have
doubled the cost the item exists to remove.

**The producer moved with the work, and that was the real decision.** Keeping
the `perf_counter` around `set_series` would have published the `QImage` wrap —
a number nothing waits on — and shown a met budget for work nobody timed, which
is rule 6 with the sign flipped. `density_ms` is measured on the thread that
does the binning and published by the GUI thread on arrival.

**Step 2, the cap.** `MAX_BLOCKS` deleted; the refusal branch in
`density_surface` deleted, so `DensitySurface.argb` is never None and `notice`
is gone with it (the density plot's centered-notice paint went too — it had no
other producer). `block_spin.py` rewritten: no floor, no hole, no `set_floor`.
What survived is the one boundary that was never about performance — `0` is a
*mode*, so an accelerated wheel run down stops at 1 before reaching auto.
`filters/block_signal.min_block_for` and `tests/unit/test_min_block_for.py`
deleted outright: the floor was their only consumer, and the arithmetic is in
git if a bound ever comes back. `filter_tab._refresh_block_floor` and
`_working_extent` went with them.

**Step 3, the attribution.** `Sample` gains `detail: str = ""` and
`MetricBus.publish(..., detail=)`, so a publisher can say what the span was
*for* — `filter_tab` sends `B = 16,384`. `GraphHud.show_sample` now keeps every
key, not just `WATCHED`, and `attribution_line()` names the leader **ranked by
`elapsed / limit`, not by raw milliseconds**. That ratio is the whole design:
by wall clock the render wins every session (3000 ms ceiling against 100), and
a field that always says "render" attributes nothing. Drawn bottom-right,
persistently, in the band color only when the leader is actually over.

**The debt was repaid halfway and repointed.** `IN_DEBT["density_rebuild"]` now
names `budget-checks-under-ambient-load.md` instead of this item: the *cap*
half is repaid, and what is left is the timing — `density_surface` at
B = 16,384 reads 98.3 ms min / 139 ms median on this workstation against the
100 ms ceiling, so it passes standalone under `BEST` and xfails inside a full
collection. Both of those are visible in `nox -s benchmark` / `nox -s checks`.

**The question that is now Kendrick's, and it is a small one.** With the
binning off the GUI thread a miss here means a graph filling late, not a frozen
window — so 100 ms may simply be the wrong ceiling now. It was set as a
perceptual bound on a GUI-thread stall that no longer exists. I did not move it;
moving a budget limit is a decision, not a cleanup.

**Tests:** two on the HUD (ratio beats milliseconds; the field persists when
nothing is over), one on `derive` (the surface matches its own array's shape and
maximum — a surface for the *wrong* array is the one wrong answer that still
renders), and `test_block_spin.py` rewritten to pin the absence of the floor
rather than its presence. `test_density_rebuild.py` now times `density_surface`
rather than `set_series`, at `REFERENCE_BLOCKS` — the same 16,384, no longer as
a bound.

## the-todo-dag-is-prose — done

**Checked the load-bearing property first, as the item asked.** A slug does
survive completion: `completed-todo/2026.07.25-executor.md` yields `executor`
under a `^\d{4}\.\d{2}\.\d{2}-` strip, so an edge pointing at an item never has
to be rewritten when that item finishes. Everything else rests on that.

- `tools/doc_index.py` — `after_slugs`, `item_slug`, `build_graph`, and an
  `ItemGraph` with `unresolved()` / `cycles()` / `blockers()`. `after:` is a new
  optional key; `gated_on` untouched and unchanged in meaning.
- `tests/docs/test_todo_hygiene.py` — the two assertions the item specified.
- Twelve `after:` edges backfilled from the item's own table.

**Two renders, and the frontier is the one that pays.** "Open items whose
`after:` have all completed" reads 11 of 12 — only `qt-free-logic-under-gui` is
blocked, on `headless-detection`. Blocked items are *shown with their blocker*
rather than omitted, so the frontier partitions the open list instead of being a
second shorter list a reader has to diff against the first.

**The mermaid block draws 17 nodes, not 34**, because only items carrying an
edge are drawn. That is the item's own "cut the graph rather than tune the
layout" instruction applied to the axis that costs nothing: an item with no edge
contributes nothing to a picture *of edges* and is already listed above in full.

**`serves:` backfill deliberately not done.** The item predicted the honest
outcome is that most items serve nothing in ASPIRATIONS.md and should say so by
staying blank — and with only edge-carrying nodes drawn, the ungrouped block is
already small and readable. Inventing edges to avoid showing a large body of
work under no aspiration is the one failure mode the item named. Left blank.

**Not done:** `conflicts_with:`, correctly — the item says not to design a
second edge kind before `after:` has been used and shown what it costs.

## machine-share-policy-is-above-its-consumers — done, and one of its symptoms was wrong

**The file argued against the item, and the argument had a hole.**
`gui/concurrency.py`'s docstring said outright "**`core/` holds none of this** —
policy about sharing a machine belongs to the process that is sharing one",
with `core.wavelet` defaulting to every core as the supporting case. That is a
real invariant and it is about **defaults**, but it had been applied to
**location**, and the two come apart: a declaration being *reachable* from
below does not make anything below *apply* it. Unreachability was enforcing the
right rule by accident. The move keeps the invariant and states it at both ends
— `core/shares.py` declares, the caller applies, and a required `workers`
argument with no default is what makes the caller say which it is.

**One of the item's three symptoms does not survive inspection.** It claimed
`decode/quiet.py` and `bench/retention_trace.py` "refer to it in prose *because
they cannot import it*". Neither wants to import it. `quiet.py` cites
concurrency's **argument** as an analogy for why fd-2 redirection belongs to the
process owner; `retention_trace.compare` explains that a single byte figure
would report one point on a curve it is sweeping. Both are rhetorical
citations, and neither becomes an import. The item's *check afterwards* step
("become imports if the move makes them possible") therefore has no work in it.

**What carried the change was symptom 2, and it is enough on its own.**
`detect/detector.py` documents that a caller running beside the interactive
pools passes `DETECTOR_WORKERS`, and could only name it in prose — `sieve.detect`
is below `sieve.gui` in the layer contract. A constant named in a docstring is
one nobody's type checker follows. That docstring now names an import.

**The design question the item flagged: `SENSED`/`WITHOUT_SENSOR` follow the
table**, into `core/shares.py`. They are statements *about the rows*, so they
have to sit with the rows or rule 4's honest gap is a gap declared in neither
file — the sum would read as complete in one place while the missing sensor is
recorded in another. That the *producers* (`PoolMeter`, `gui/resource_probe.py`)
stay up in `gui/` is not a split of the table: it is the arrangement
`bench/budgets.py` already has, where a declaration names its own gap and
something above it closes one.

**Split as built.** `core/shares.py` — the three worker constants, `WorkerSplit`,
`MemoryShare`, `REFERENCE_FRAME_BYTES`, the four shares, `MEMORY_SHARES`,
`UNBOUNDED`, `SENSED`, `WITHOUT_SENSOR`, and every function over the byte column.
`gui/concurrency.py` — `total_workers`, `fits_machine`, `resolve_worker_split`:
which pools an interactive session runs and how they degrade. No re-exports, so
each name keeps one home; six import sites and four test modules updated.

**Stale pointers retargeted**, which was most of the work by volume: eleven
modules and three ARCHITECTURE.md passages named `gui/concurrency.py` as the
home of the table. `decode/quiet.py` was rewritten rather than sed'd, because
the argument it cites is the one this item inverted.

**Not done:** `chain_model.recompute` still takes `workers` required with no
default, and should — that is the enforcement the ARCHITECTURE.md passage calls
"the one part of this rule enforced at the point a violation would be written".
The item lists it as a symptom; it is the fix, not the disease.
