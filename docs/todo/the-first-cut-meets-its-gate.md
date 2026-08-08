---
title: The first cut meets its gate — parity, both regimes, the list still empty
step: "07.11"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui/test_gui_cli_parity.py -q && uv run pytest tests/bench/test_gui_loop_budget.py -q"
opened: 2026-08-08
---

# The first cut meets its gate — parity, both regimes, the list still empty

Phase 7's gate as a step, so closing the phase is work a review checks rather
than a sentence in PLAN.md. Three claims:

GUI/CLI parity at the executor level on the stirred clip — the fixture left
the GUI test in 05.5 precisely so the oracle could run first, and now the GUI
answers to the same fixture from the other side.

Both budget regimes measured through the GUI, against the same
`bench/budgets.py` keys 06.3 measured headless — which is the attribution
Phase 6 existed to buy: a number that regresses here is the GUI's, and
nothing else's. Scoped to the keys whose producers this cut builds:
`density_rebuild` has none — the band-power density strip is a later cut,
since it drags band-power caching behind it — so it stays declared in
`budgets.WITHOUT_PRODUCER` rather than measured through a surface that does
not exist. A miss inside the scope is a defect or a declared debt in
`budgets.IN_DEBT` with the item that repays it, never a widened ceiling
(VISION.md's scope clause).

And the `gui-computes-nothing` exception list is as empty as Phase 0 left it,
now that there is a GUI for it to be empty about.

## The graph panel is built and placed nowhere (2026-08-08, from 07.7)

07.7 landed `gui/graph_panel.py` as a view with two verbs — a completed refill
in, a stale mark for the interval before the next one — and stopped there,
because its criterion is about what the panel draws and nothing in the tree yet
drives a refill from a param edit. So `MainWindow` does not build one, no layout
holds one, and `SeriesCollector`'s only caller is still `tests/bench/`.

That lands here rather than in 07.8, whose subject is the band editor and not
where the surface it sits on lives: measuring `slider_to_graph` through the GUI
is what forces a panel that a param edit actually refills, and the two calls it
needs are already the ones a `SeriesCollector.refill()` block brackets.

## And so are the two kind editors, which is where a region's space is decided (2026-08-08, from 07.8)

07.8 landed `gui/kind_editors.py` on the same terms and for the same reason:
`bind_editors` is called by its own test and by nothing else, because what a
`MainWindow` would hand it — the node the walk is on, its spec, its params, and
the two surfaces — is assembled nowhere yet.

Placing them settles a question the editors cannot. A `RegionEditor` produces a
rectangle in the pixels of the image the canvas is showing, which is the only
space it can see; `crop.py` says a region parameter indexes the frame *its own
node* is handed; and what the viewport is fed today is a display proxy of the
source, resampled to `transport/decode_worker.PROXY_WIDTH` whenever the footage
is wider than that. So a box drawn on a 4K clip today would name proxy pixels
and `crop` would read them as source pixels — a factor of three, silently, and
only on large footage. The three ways out are all on this side of the seam:
feed the canvas full-resolution frames for the node being edited, hand the
editor the extent of the space its value is denominated in, or declare the
proxy's scale where the frame is handed over. Which one is this item's to pick,
along with the harder half `crop.py` states and 07.8 did not touch — that a
crop below a `rescale` is denominated in a frame nothing on screen is showing.

## And the save screen, which is where the walk would have to gain a fourth position (2026-08-08, from 07.9)

07.9 landed `gui/save_screen.py` on the same terms: its criterion is what the
checkoff writes and what the run button issues, and both are asked of the screen
directly. `MainWindow` builds none, and `control.py`'s track is three panes wide
by construction — project, pipeline, step, VISION's walk — so placing this one is
not a layout choice but a decision about what the walk *is*. VISION puts the
screen after the pipeline ("checks off the outputs they want persisted, and
selects 'process'"), which reads as a fourth position rather than a dialog, and
the rail, the slide and `POSITION_NAMES` all count three today.

That decision belongs here, with the two panels above, because this item is the
one that has to render a whole GUI a user can walk end to end.

Wherever it is placed, Run needs the guard the screen already has the accessor
for (07.9 review): `SaveScreen.run()` calls `QProcess.start` unconditionally, so
a second click while a run is in flight re-saves the document, clears the
message the first run will write into, and emits `run_issued` for a process Qt
declines to start. `running()` is the state that should gate the button, and
nothing gates it today.

## And the guidance expander, which is the fourth thing on the step (2026-08-08, from 07.10)

07.10 landed `gui/expander.py` on the same terms: its criterion is that the
widget's text is the tool's own declaration, which is asked of the expander
directly, so `MainWindow` builds none and the step position still holds a
`NodeBox` and nothing else. Placing it is this item's, with the panel and the
editors above.

What placing it decides that the widget cannot: the step position now has four
things wanting to be on it — the node's caption, the generated param form, the
kind editors' handoffs, and an arrow that opens onto a page of prose. The
expander caps its own body height so a wordy tool cannot set the layout for
every other one, but which of the four is above which, and whether opening the
guidance pushes the controls off the pane or scrolls beside them, is a question
about the step and not about any one widget on it.

## 06.3's headless claim now rests on collection order (2026-08-08, from 07.4)

`tests/bench/test_loop_budget.py::test_the_measurement_ran_with_no_qt_in_the_process`
reads `sys.modules` at assertion time, which was the whole of the claim while
nothing in the tree imported Qt. 07.4 gave the tree a `tests/gui/`, and pytest
imports every test module during collection — before the first test runs — so
one top-level `from sieve.gui.app import ...` makes Qt resident for the entire
session and that assertion goes red no matter which directory it sits in.

07.4 held the claim exactly as written by keeping `tests/gui/` free of
module-scope Qt imports (the rule, with the reason, is in
`tests/gui/conftest.py`): collection stays Qt-free and `tests/bench` runs
before `tests/gui` in the order pytest walks `testpaths`. That is discipline
plus an ordering, not a mechanism, and this item is where both stop being
tenable — it measures the same keys *through* the GUI, in a session where a
`QApplication` exists by construction. So the residency assertion has to be
restated here rather than carried: what the headless numbers need is that
*they* were taken with no Qt loaded, which is a claim about one measurement's
process and not about the suite's. Whether that means a subprocess, a separate
invocation, or retiring the runtime check in favour of `headless`'s static
guarantee is this item's to decide.
