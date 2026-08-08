---
title: Transport and timeline port into the skeleton
step: "07.6"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui/test_timeline.py tests/gui/test_player_scrub.py -q"
opened: 2026-08-08
---

# Transport and timeline port into the skeleton

Port-with-care of v2's `gui/transport/` and `gui/timeline/` — the two GUI
contracts that held in v2 — into 07.4's skeleton, under the porting
discipline: the ported v2 tests are the spec, and a test that must change to
pass is a decision written at the bottom of this item, not an adaptation. The
canvas plays and scrubs footage through the decode path, and the timeline is
v2's scrubber at the height VISION gives it. The criterion names whole ported
modules rather than `-k` claims because for a port the module *is* the claim:
it passes as v2 wrote it or the item stops.

This is the pre-pipeline regime's surface (open → first frame, scrub →
repaint, release → exact frame); the numbers are taken through the GUI at
07.11, not here. Canvas and widget-control stay one package — PLAN.md's one
boundary *not* to draw — so nothing in this item minted an import fence
between them.

## Two decisions the port could not avoid, and their tables

### There is no `qtbot`, so the harness is re-derived

Neither v2 test file can be run as written: both are driven by pytest-qt, and
pytest-qt cannot be installed here. Its plugin imports the Qt binding at
`pytest_configure`, before any test runs, and
`tests/bench/test_loop_budget.py::test_the_measurement_ran_with_no_qt_in_the_process`
asserts that no Qt module is resident while Phase 6's headless budget is
measured. Adding the dependency would take that assertion down, which is the
claim the whole phase exists to make.

So `qtbot`'s two services are re-derived in `tests/gui/driving.py`: synthetic
mouse input (v2's `tests/gui/qt_input.py`, with coordinates as plain floats so
the caller needs no `QPointF`) and waiting (`processEvents` against a deadline,
in place of `waitUntil`/`waitSignal`). Every Qt import in it is inside a
function, because `tests/gui/conftest.py` forbids one at module scope for the
same residency reason. `pytest.mark.gui` is also gone — the marker is not
registered and `--strict-markers` is on.

This is a re-spelling of every case in both files. What it does *not* change is
which claims are made, so the tables below are about claims.

### The working window is view state, because schema v1 records no clip

`test_timeline.py` is written against `ReplicateDocument`, whose window was
saved as `Project.clip` and was what narrowed a run. Schema v1 has no such
field: `SourceSpan` appears only on a crop record, and what a run covers is the
`span` node's parameters (`adr/detector-is-a-node.md`). v2's `ClipRange` is
`SourceSpan` field-for-field, so the type ports as a rename; the *ownership*
cannot. The window therefore lives on `TimelineBar` as view state, which is what
it means in v3 — the stretch the transport may reach — and no intent kind was
added for it.

Three consequences, all visible in the table: the undo cases go (there is no
document write to undo), the ten-second default goes (`DEFAULT_WINDOW_SECONDS`
proposed the clip that got saved, and proposing a bound on what the user may
watch is a different act), and the Mark In/Out cases go with the menu bar the
skeleton does not have.

### `test_timeline.py`

| v2 class | v3 |
|---|---|
| `TestTheWindowIsAlwaysThere` (4) | **replaced by** three cases on the bar. "A bound source has a window" survives, over the whole source rather than ten seconds of it; "but has chosen no clip" and the undo-stack half drop with the document; "a source shorter than the default is the window" has no default to be shorter than, and becomes the unbound-source case. |
| `TestTheWindowKeepsItsLength` (11) | **survives** as five, at the bar instead of the document. Move-carries-length, rests-at-full-length, typed-length-keeps-origin, length-that-will-not-fit, clamped-to-source. Dropped: the two `end_window_at` cases (that is the keystroke mark-out, which has no key), `bring_window_to`'s two (folded into `TestTheBarDrivesTheWindow`, which is where v2 also tested them through the strip), and `remarking-records-nothing` (an undo-stack claim). |
| `TestWindowHistory` (7) | **dropped** whole. Undo of a window is not a thing when the window is view state; `tests/unit/test_session.py` holds the stack's own claims. |
| `TestTheStrip` (5) | **survives** verbatim in substance. |
| `TestTheBarDrivesTheWindow` (3) | **survives**, plus a fourth: the strip and the bar show one window, which is v2's "the player is told here and nowhere else" made checkable without a document to undo through. |
| `TestTheWindowBracketIsGrabbable` (8) | **survives**, with `one_drag_is_one_undo_entry` **replaced by** `one_drag_is_one_window_edit`: the same edge, counted one layer earlier at the `window_resized` announcement the undo stack used to be fed. |
| `TestTheHoverBubble` (5) | **survives** verbatim in substance. |
| `TestPlaybackIsBounded` (3) | **survives** verbatim in substance. |
| `TestWindowWiring` (4) | **replaced by** `TestTheSkeletonBindsTheSource` (3). The three mark/clear cases drove menu actions; there is no menu bar. What is left is the wiring they depended on and this item promises: opening a project reaches the decode path, the source's length and rate reach the bar, and a click on the band moves the playhead. |
| `TestTheLengthOutlivesTheSession` (2) | **dropped**. `gui/preferences.py` does not exist in v3, and a remembered length is a preference about a window that is now view state — the decision belongs with the first preference, not with this port. |

### `test_player_scrub.py`

Every class **survives in substance**; the file is re-spelt for the harness and
nothing else. `TestPreferences` keeps its name and its two cases even though
there is no `Preferences` object: both drive `ScrubPolicy.set_allow_degrade` and
`close`, which are the policy's own verbs.

### What the transport port left behind, and why

Each of these is a v2 module or method whose only consumer does not exist in
v3. None is a decision against it; each comes back with the surface that reads
it.

- `render_ring.py`, `set_render_feed`, `set_render_filling`, `pacing.feed_bounds`
  — render-fed playback needs a window render in the GUI. `RENDER_RING_SHARE` is
  already in the ledger and is what it will be sized by.
- `bench/retention_trace.py` and every `_record` call — the trace does not exist
  in v3, and its query half was an experiment item v2 held.
- `gui/preferences.py` and `apply_preferences` — no preferences surface.
- `set_luma`/`set_viewport_luma` and the `ChannelSpec.GRAY` branch in the worker
  — no gray toggle, so the reader is never opened `luma=True` and the branch
  would be unreachable.
- `set_proxy_width` — its only caller was `apply_preferences`; the width stays
  the constant.
- `set_playback_rate` — no rate control.
- `PoolMeter` on the worker — `gui/resource_probe.py` was its only reader.
- `clip_window.default_window`/`effective_window`/`fitted`/`ended_at` (the
  keystroke mark-out) — the first three resolve the absence of a saved clip and
  the fourth is a key that does not exist.

### One thing the port added

`VideoPlayer` stops its decode thread when it is destroyed, not only when
`shutdown` is called. v2 relied on `qtbot` closing every widget; without it, a
`MainWindow` that is simply dropped finalises a running `QThread` and aborts the
process — which is what `tests/gui/test_skeleton.py` did the moment the window
grew a player. `shutdown` stays and is what an orderly exit calls.
