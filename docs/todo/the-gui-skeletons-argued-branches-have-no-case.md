---
title: The GUI skeleton's argued branches have no case
priority: normal
phase: 7
status: done
gated_on: nothing
done_when: "uv run pytest -q tests/gui/test_app.py -k dropped"
opened: 2026-08-08
---

# The GUI skeleton's argued branches have no case

07.4 landed eight modules under one test. That is the shape the item asked for
— a skeleton is one capability — but three places in it argue a behaviour at
length and are held by nothing, and one of them is the reason a module exists.

`gui/walk.py` is written instead of `pipeline/dag.py`'s `linear_order`
precisely because a window must draw a document that branches, that is
disconnected, or that will not run. The only fixture is a three-node chain
whose document order *is* its walk order, so every one of those cases is
absent. Under `tests/gui`, all three of the mutants in `done_when` survive:
the roots-first pass, the recursive descent, and the accumulated order itself
— replacing the whole return with `tuple(pipeline.nodes)` is green. The branch
a module is written *for* has to be among the fixtures or the module is
unfalsifiable
(`findings/loop/2026.08.08-a-per-subject-revert-is-green-when-the-two-expressions-agree-on-every-fixture.md`,
2026-08-08 amendment). A branching graph, a two-root graph, and a cycle are
the three fixtures; schema v1 refuses two edges into one node, so a branch is
one node feeding two and a cycle is what `Pipeline` permits and `dag.py`
refuses at execution.

Two more, on the same sweep and not covered by the criterion above.
`layout._require_layout_section` raises on a Fixed or Maximum horizontal
policy and on a minimum wider than half the window; both branches survive
deletion, and no production caller can reach either — the canvas takes a
`QLabel` and the control side declares `Expanding`. It is the guard shape
already recorded for `_value_components`
(`the-arity-guard-accepts-a-union-nothing-asked-it-about.md`): the refusal
cases have to be written against widgets the tree does not otherwise hold.
(07.6 has since replaced the `QLabel` with `canvas.VideoCanvas`, which declares
`Expanding` on both axes, so the guard is still unreachable and for the same
reason — the sentence above is corrected, not the finding.)
And `control.show_graph` carries the rail's visibility across a rebuild rather
than deciding it, so that a walk moved from the project position does not put
a rail on a screen with no graph on it; `setVisible(True)` in its place
survives, because nothing moves the walk while the project position is
current.

## The same shape three modules later, from 07.6's review (2026-08-08)

The transport-and-timeline port added `gui/canvas.py`, `gui/timeline/geometry.py`
and `gui/timeline/window.py`, and two of the three carry the same gap for the
same reason: the ported tests are v2's claims, and the modules v3 wrote fresh to
serve the port get no case of their own.

`gui/canvas.py` is held by nothing at all.
`uv run python scripts/mutation_sweep.py --file src/sieve/gui/canvas.py --mutant "self._frame = image ==> pass  # " -- uv run pytest -q`
is green across the whole 868-test suite: the viewport can drop every frame the
transport hands it and no case moves, including
`test_timeline.py::TestTheSkeletonBindsTheSource::test_the_first_frame_reaches_the_canvas`,
which is named for the canvas and asserts on the strip's `window_rect`. The
same sweep survives `min(..., 1.0) ==> 1.0` in `frame_rect` — the never-upscale
rule the module docstring argues from the proxy width — and `self._frame = None
==> pass` in `clear`. `frame_rect`'s own docstring says it is exposed *because*
"the footage is not stretched" is a claim about this rectangle; nothing asks it.
The item's headline promise, that the canvas plays and scrubs footage through
the decode path, is carried by the player's tests up to the signal and by
nothing past it.
(07.12 has since landed a case that reads `window.viewport.frame` and compares
its pixels to an independent render, so `self._frame = image ==> pass` now dies
under `tests/gui tests/bench/test_gui_loop_budget.py`. `frame_rect`'s two —
the never-upscale clamp and `clear` — are untouched by it and stand. The
paragraph above is corrected, not withdrawn; the section below is what the same
commit left open.)

`gui/timeline/geometry.py` loses its two argued numbers to one fixture choice.
Under `uv run pytest -q tests/gui`, `MIN_BAND_PIXELS = 2.0 ==> 0.0` survives and
`index = int(x / self.width * self.frame_count) ==> int(x / (self.width - 1) *
...)` survives — the second being the exact off-by-one the `frame_at` docstring
spends four lines refusing. Both survive because `test_timeline.py` resizes the
strip to `STRIP_WIDTH = 1000` over `SOURCE_FRAMES = 1000` so that "every frame
owns exactly one column", which is a readability decision that also makes
`width` and `width - 1` agree everywhere a case looks, and makes every window
wider than the floor. The fixtures the two need are a band wider than the asset
is long (the ordinary case the docstring names: a short source in a maximised
window) and a one-frame window in a long source. `centre_of_frame`'s `+ 0.5`
does die, so the module is not uncovered — these two are.

`window.py`'s `length = min(window.frame_count, frame_count)` in `moved_to` also
survives; that clamp only bites for a window longer than its source, which the
bar cannot currently produce, so it is the guard-with-no-caller shape rather
than a missing fixture and is the least of the four.

## The graph panel's whole value axis, from 07.7's review (2026-08-08)

`gui/graph_panel.py` landed with five tests that hold its trace, its stale mark
and its two refusals — the criterion's two kill the `start_index` offset, the
stale flag and the y mapping — and with `value_range` held by nothing at all.
Under `uv run pytest -q tests/gui`, all four of these survive:
`low = min(float(finite.min()), 0.0) ==> low = float(finite.min())`,
`_HEADROOM = 1.06 ==> _HEADROOM = 1.0`,
`return (low, top) if top > low else (low, low + 1.0) ==> return (low, top)`,
and `return 0.0, 1.0 ==> return 0.0, 2.0`.

The first is the module's headline decision — "Zero is the floor of the value
axis", argued from there being no tick labels — and the fixture is
`series([0.0, 1.0, 2.0, 3.0])`, whose minimum *is* zero, so the clamp and its
absence agree. The test comment above that assertion says the floor is what puts
the first point on the bottom edge; a floor at the series minimum puts it there
too. What separates them is a series that never reaches zero, which no fixture
holds. The degenerate-span fallback needs a constant series (without it `y_of`
divides by zero), and the empty range needs a case that asks a panel with no
series for its axis rather than for its trace, which
`test_a_panel_with_nothing_to_draw_says_so` stops one call short of.

`_one_value_per_frame`, `status_text`, the non-finite break and the
`start_index` offset all die, so this module is not uncovered either — the value
axis is.

## The expander is open by default and nothing says so, from 07.10's review (2026-08-08)

`gui/expander.py` landed with two tests, and the one named for the arrow holds
none of the arrow. Under `uv run pytest -q tests/gui/test_expander.py`, five of
seven mutants survive: `self._body.setVisible(False) ==> setVisible(True)`,
`self.arrow.toggled.connect(self._show_body) ==> pass`,
`self._body.setVisible(expanded) ==> pass`,
`self._body.setMaximumHeight(_BODY_HEIGHT) ==> pass`, and
`setWidgetResizable(True) ==> setWidgetResizable(False)`. Only the label's text
and the widget's own `setMaximumHeight` die, and the widget cap is what the
criterion's sibling asserts.

The first three are one defect: `is_expanded()` returns
`self.arrow.isChecked()`, so every assertion about opening and closing is an
assertion about `QToolButton.setCheckable`, and the module's headline claim —
"stays shut until it is asked for", the sentence that makes this the wizard
reimagined rather than the wizard — survives the widget shipping open. The fix
is one of two: `is_expanded()` reading the body's visibility, or the test
asserting `expander.findChild(QScrollArea).isVisible()` beside the checked
state. The other two are the ordinary guard-with-no-fixture shape — the body
cap is masked by the widget cap above it, and word wrap is a rendering property
no case reads.

Written up as a vacuity shape in
`findings/loop/2026.08.08-a-widgets-state-accessor-reads-the-toggle-and-not-the-thing-toggled.md`.

## Two of the tuning loop's accessors have no reader at all, from 07.11's review (2026-08-08)

The assembly cut is the first Phase 7 module that is fully driven — every
branch in `gui/tuning.py` that the parity file and the GUI budget file walk is
held by a real gesture — with two exceptions, and they are past the
guard-with-no-caller shape above rather than an instance of it.
`TuningLoop.refill_now` is a whole second entry point ("`request_refill` without
the deferral, for a caller with no event loop") and `TuningLoop.is_open` is a
one-line state read; neither is called from `src/` or from `tests/`, so deleting
either is green everywhere and nothing states what they are for. A method
written for a caller that does not exist is not covered by a fixture that could
be added — the question is whether the caller is coming.

The same section's other half is a count. `test_gui_loop_budget`'s scrub case is
docstringed "over the same twelve stops the headless pass took", where `SCRUBS`
two screens above it is `SCRUB_STOPS` filtered to the working window and holds
nine — the constant's own comment says so and the docstring contradicts it. The
assertion is `0 < len(...) <= len(SCRUBS)`, so nothing goes red for the
sentence; what it costs is a reader comparing this file's median to the headless
one on the belief that the two passes took the same stops.

## The viewport's own refusal, from 07.12's review (2026-08-08)

07.12 fed the canvas the watched node's render, and the two decisions the item
had flagged as unsettled were answered in `gui/app.py` and `gui/canvas.py`. One
of the two is held and the other is not. Under
`uv run pytest -q tests/gui tests/bench/test_gui_loop_budget.py`:

- `if spec.element is not ElementKind.FRAME: ==> if True:` and
  `if values is None or not self._viewport.set_values(index, values): ==> if
  values is None:` both die, so the climb past a `FRAME` node and the
  fall-back-to-source path are real.
- `and node.node_id in source_fed_nodes(pipeline) ==> and False` survives.
  That clause *is* the second answer — a source-fed node carrying a `region`
  parameter keeps the source on the canvas, so a `RegionEditor`'s box is not
  drawn over a rectangle the value does not index. Every case walks to the
  detector, so nothing ever stands on `crop` with an editor bound and the
  refusal is unfalsifiable. The fixture is a walk that stops on the source-fed
  node and asks `viewport_node`.
- `scaled = np.zeros_like(array) if spread <= 0.0 else (array - low) / spread
  ==> scaled = (array - low) / spread` survives in `canvas.image_of`. The
  constant-frame branch is argued in a comment ("a constant frame is flat rather
  than saturated") and no fixture holds a frame whose values do not vary; the
  mutant divides by zero and the suite is green. Same shape as `value_range`'s
  degenerate span two sections above, on the other surface.

`image_of`'s two `None` returns — a non-2-D array and one with no finite value
in it — are the guard-with-no-case shape rather than a missing fixture: the only
producer of a non-picture on this graph is `detect`, and `frame_bearing` climbs
past it before `image_of` is ever asked.

## The combo's signal is the wrong one, from the commit-on-intent review (2026-08-08)

`gui/param_form.py` gained three commit rules and three cases, and four of the
five mutants the worker swept die. The fifth,
`combo.activated.connect ==> combo.currentIndexChanged.connect`, was reported as
an equivalent mutant and is not: opening the popup and selecting the entry the
combo already shows emits `activated` and not `currentIndexChanged`, so it is
the ordinary missing-fixture shape — and the surviving side is the wrong one.
`ParamForm._edit` issues a `SetParam` unconditionally and `Session.commit`
appends unconditionally, so that one click costs a re-plan, a render and an undo
entry for a value nobody changed, which is the exact thing `_enum`'s docstring
argues the signal was chosen to prevent. Measured in
`findings/2026.08.08-the-combos-two-signals-disagree-on-reselecting-the-shown-choice.md`;
the fixture is a popup Return on the current entry, and the fix is a choice
between the narrow signal swap and a no-op guard that would also cover a spin
box arrowed back to where it started.

Two smaller ones on the same module, neither swept. `_CommittedSpin.wheelEvent`
ignores the event so that the enclosing `QScrollArea` scrolls instead — the
justification for dropping v2's `_scrollable_ancestor` walk, and true of
`step_pane.py` today — but no case reads the scroll area's position, so
"declined" and "declined and handed on" are the same green. And
`_keep_focus_off_the_wheel` rewrites only the exact `WheelFocus` default; the
branch where a control already carries some other policy is never taken,
because nothing in the generator sets one.

## The walk has its three documents, and the criterion rotates (2026-08-08)

`tests/gui/test_walk.py` landed and the criterion this item opened with —
`walk.py`'s roots-first pass, its recursive descent and its accumulated return —
is killed. Re-run independently: three killed, none survived, and each mutant is
killed by exactly one named case with the other two green, so the trio is
attributable rather than a lucky aggregate. That criterion is retired, not kept:
its three are green from here on and a criterion nothing can turn red certifies
nothing.

**The item's `done_when` now names one module at a time, and this is the second
of at least six.** Six reviews folded into this file without widening the
criterion, which is the fold rule working as written; what it left is an item
whose body holds every Phase 7 module's uncovered claim and whose criterion held
one file's. `done_when` cannot cover them in one string — `mutation_sweep` takes
one `--file` — so it rotates, and the item is `open` until the last section
below is spent. Swept today under `uv run pytest -q tests/gui
tests/bench/test_gui_loop_budget.py` (107 passed, baseline green immediately
before), fifteen of the sixteen mutants the sections above name still survive:
`canvas.frame_rect`'s clamp, `geometry`'s two, `window.moved_to`'s clamp,
`graph_panel.value_range`'s four, `expander`'s five (the current criterion),
`app.py`'s `source_fed_nodes` clause, and `param_form`'s combo signal.
`canvas.clear`'s `self._frame = None ==> pass` is the one that has since died —
07.12's pixel-reading case reaches it — so the 07.6 section's sentence naming it
is corrected here rather than above.

Two residues the walk work leaves, both about a sentence rather than a branch.
`test_walk.py`'s own docstring says every case's document order is chosen to
disagree with its walk order, and the cycle case's does not: saved
`root tail loop back`, walked `root tail loop back`, so
`return tuple(ordered) ==> return tuple(pipeline.nodes)` survives that case
alone. It earns its place on a different mutant — deleting the second,
unreached-node loop is killed by the cycle case and by neither of the other two
— but the file states the disqualifying shape and then ships one, and saving it
`loop back root tail` would satisfy the sentence and kill the return mutant too.
And `walk.py`'s docstring says ties "break on the document's own order", which is
true of the roots and not of sibling branches: `children` is built from
`pipeline.edges` order, so nodes `root left right` with edges `root>right
root>left` walk `root right left`. Both orders are persisted, so the stability
the sentence is argued from holds either way — the sentence is what is wrong, and
the fixture that would pin it is edges saved against node order.

## The expander is held, and the criterion rotates a second time (2026-08-08)

`f32e74d` answered the expander section: `is_expanded()` reads
`not self._body.isHidden()` rather than the arrow's checked state, and the body
cap and the horizontal-scroll axis got cases of their own. Re-run
independently, all five of that criterion's mutants die — the three that were
one defect and the two missing-fixture ones — so the section above is spent and
not withdrawn.

Two things about how it landed, neither of which changes the verdict. The
worker narrowed the criterion's oracle from `tests/gui
tests/bench/test_gui_loop_budget.py` to `tests/gui/test_expander.py`, which is
the review's string to write; on the merits the narrowing is a strengthening —
the narrow oracle is a subset, so a kill under it is a kill under the wide one,
and a mutant only a distant test kills is the gap the sweep exists to expose —
so it stands, and rotates from there. And the item was left `open` rather than
`awaiting-review`, so `--next` served it to a work run that found the criterion
already green and had nothing to do
(`findings/loop/2026.08.07-a-worker-on-a-reopened-item-leaves-the-status-the-review-set.md`,
2026-08-08 amendment).

**Third of at least six.** The criterion now names `graph_panel.value_range`'s
four, verified red at 0 killed / 4 survived under
`uv run pytest -q tests/gui/test_graph_panel.py` — the zero floor, the
headroom, the degenerate-span fallback and the empty range, all four argued in
the section above. The oracle is the file that holds the module, following the
expander's narrowing. Ten of the mutants the sections name are still unheld;
the item is `open` until the last section is spent.

## The value axis is held, and the criterion rotates a third time (2026-08-08)

`32128c7` answered the graph panel section with four cases and touched nothing
else. Re-run independently: all four of that criterion's mutants die, and the
same sweep run against each new case alone kills exactly one apiece — floor,
headroom, degenerate span, empty range — so the four are attributable and not a
lucky aggregate. The pre-commit file swept under the same four is 0 killed / 4
survived, so the red is the commit's own and not the previous review's word for
it. `tests/gui` is 106 passed.

One residue on the function the section just closed, and it is a new mutant
rather than one of the four. `value_range`'s docstring argues both halves of the
clamp — zero is the floor, and "the floor drops below zero only for a series that
goes there, [because] a negative value drawn on the bottom edge would read as the
same nothing a zero does". The four cases hold the first half; the second is
unheld, and `low = min(float(finite.min()), 0.0) ==> low = 0.0` survives
`uv run pytest -q tests/gui`. No fixture carries a negative value, so a panel
that clipped a below-zero series onto the floor would draw the same graph. The
fixture is a series with a value under zero, asserting the floor is that value
and that its point is on the bottom edge. It is not in the rotation below — it
belongs to this section and a later rotation returns to this file for it.

Two smaller things about how the four landed, neither changing the verdict. The
constant-series docstring says "a constant series has a peak equal to its floor",
which is true of the all-zero series it then builds and not of a constant series
generally: `series([3.0, 3.0, 3.0])` clamps `low` to zero and gets a span of
3.18, so the degenerate branch is reachable only for a constant at or below zero.
The sentence names a wider class than the branch it is testing. And the floor
case's second assertion computes its expected `y` from the `top` the panel just
returned, so that half is a consistency check between `value_range` and `y_of`
rather than an independent claim about either; it kills the mutant on `low`
regardless, and `low == 0.0` above it is the independent assertion.

**Fourth of at least six, and it is `gui/canvas.py`.** The criterion now names
the two the 07.6 and 07.12 sections left on that module — `frame_rect`'s
never-upscale clamp and `image_of`'s constant-frame branch — verified red at
0 killed / 2 survived under `uv run pytest -q tests/gui`. The two are one
rotation because `mutation_sweep` takes one `--file` and both are in it, not
because they are one claim. The oracle is the whole `tests/gui` directory rather
than one file, because there is no `tests/gui/test_canvas.py` — the module is
reached from the timeline and app cases, which is the 07.6 section's original
complaint. Beyond the two in the criterion, six mutants across five files are
still unheld — `graph_panel`'s negative floor, `geometry`'s two,
`window.moved_to`'s clamp, `app.py`'s `source_fed_nodes` clause and
`param_form`'s combo signal — and the item is `open` until the last is spent.

## The canvas is held, and the criterion rotates a fourth time (2026-08-08)

`fa1a86d` answered the canvas section with `tests/gui/test_canvas.py`, the
module's first file of its own, and touched nothing else in `src/`. Re-run
independently: both of that criterion's mutants die, and the same sweep against
each case alone — `-k own_size`, `-k spread` — is 1 killed / 1 survived apiece,
the killed one being the other's survivor, so the two are attributable and not a
lucky aggregate. The same sweep with `--deselect tests/gui/test_canvas.py` is
0 killed / 2 survived, so the red is this commit's own rather than the previous
review's word for it. `tests/gui` is 108 passed.

The guard's case asserts the absence of the division rather than the colour, and
that is the right call rather than a shortcut: measured in
`findings/2026.08.08-the-constant-frame-guard-is-output-equivalent-to-the-division-it-refuses.md`,
and re-derived here. It is the counterpart to the failure
`findings/loop/2026.08.08-an-equivalent-mutant-is-a-claim-about-every-reachable-state.md`
records — a run that finds two expressions agreeing on every reachable input and
goes looking for the oracle that separates them, instead of reporting the
survivor as equivalent. The 07.12 section's description of this mutant as the
ordinary missing-fixture shape is corrected by that finding, not withdrawn: the
fixture the section asked for would have gone green under the mutant.

**One residue, and it is prose in `canvas.py` rather than a mutant.** The comment
over the guard argues two things — "dividing by the spread would be a division by
zero, and either extreme of the ramp would be a brightness the frame did not
earn" — and the second is false of the code as written, in a way the run's own
finding states and its commit did not act on. `np.zeros_like` *is* the low
extreme of the ramp; so is what `nan_to_num` gives the mutant. The clause names a
consequence the branch does not avoid and in fact produces. The correction is one
sentence, deleting the second clause or replacing it with what the branch
actually buys (no invalid floating-point operation, which is what the new case
asserts). Recorded as a third occurrence in
`findings/loop/2026.08.08-the-proof-of-red-corrects-the-item-and-leaves-the-comment-it-was-written-from.md`;
it is folded here rather than minted because it is one line in a module this item
already owns four sections about.

**Fifth of at least six, and it is `gui/timeline/geometry.py`.** The criterion now
names the two the 07.6 section left on that module — `MIN_BAND_PIXELS`'s floor
and `frame_at`'s denominator, the off-by-one its docstring spends four lines
refusing — verified red at 0 killed / 2 survived under `uv run pytest -q
tests/gui`. Both survive for one fixture reason, `STRIP_WIDTH == SOURCE_FRAMES`,
so one file's fixtures answer both.

**One residue on the sentence the second of those is written from, found in
pinning it.** `frame_at`'s docstring charges the off-by-one denominator with two
consequences — it "reaches the last frame a pixel early and never reaches it at
all when the band is wider than the asset is long" — and the criterion's mutant
has the first and not the second. Over ten frames in a 1000-px band, dividing by
`width - 1` reaches frame 9 from x = 899.1 rather than from 900, which is the
pixel-early half; it still reaches it, everywhere from there to the right edge.
The clause that follows describes a different off-by-one, `x / width *
(frame_count - 1)`, which puts frame 9's boundary at x = 1000 and so never names
the last frame for any click inside the band. Two variants, one sentence, and
the test written against the criterion's mutant can only hold the half that is
its. The correction is to split the sentence or to drop the clause; the second
variant is not currently swept.

The oracle stays the whole `tests/gui`
directory: `test_timeline.py` holds the module and a second file may not be what
the fixtures want. Four mutants across four files are still unheld after this
one — `graph_panel`'s negative floor, `window.moved_to`'s clamp, `app.py`'s
`source_fed_nodes` clause and `param_form`'s combo signal — plus the comment
above, and the item is `open` until the last is spent.

## Geometry is held, and the criterion rotates a fifth time (2026-08-08)

`597f156` answered the geometry section with `tests/gui/test_geometry.py`, the
module's first file of its own, and touched nothing in `src/`. Re-run
independently: both of that criterion's mutants die, and the same sweep against
each case alone is 1 killed / 1 survived apiece, each case killing the other's
survivor — the floor case takes `MIN_BAND_PIXELS` and the boundary case takes
the denominator — so the two are attributable and not a lucky aggregate. The
same sweep with `--ignore=tests/gui/test_geometry.py` is 0 killed / 2 survived,
so the red is this commit's own rather than the run's word for it. `tests/gui`
is 110 passed.

The fixture premise the whole section argues from holds as stated:
`test_timeline.py` is `SOURCE_FRAMES == STRIP_WIDTH == 1000`, which is why
`width` and `width - 1` agree everywhere it looks and why every band it paints
clears the floor. The new file's two proportions — 108 000 frames under 1000 px,
and 10 frames under the same band — are what separate them, and a second file
rather than a second fixture in the first one is the right call for that reason.

The residue the run folded above is correct on its arithmetic, re-derived here:
under `width - 1` the last frame's boundary is 899.1 and every x from there to
the right edge still names it, so the mutant is pixel-early and not
unreachable; the "never reaches it at all" clause is true only of
`x / width * (frame_count - 1)`, whose boundary is 1000 and so falls outside the
band. Two variants in one sentence, and the criterion swept one.

One thing the floor case asserts beyond its mutant, and it earns its place:
`left == x_of_frame(start)` cannot fail under either mutant in the criterion,
which is close to the shape of a case comparing a run's output to itself. It is
not one — it holds `span`'s *rightward* widening, which a symmetric round-up
would break and which nothing else in the tree covers.

**Sixth rotation, and it returns to `graph_panel` for the negative floor** the
third rotation's review named as belonging to a later pass rather than to its
own four. `low = min(float(finite.min()), 0.0) ==> low = 0.0` is verified red at
0 killed / 1 survived under `uv run pytest -q tests/gui` on the tree this review
closes; no fixture carries a value below zero, so a panel that clipped a
below-zero series onto the floor draws the same graph. Three mutants across
three files are unheld after this one — `window.moved_to`'s clamp, `app.py`'s
`source_fed_nodes` clause and `param_form`'s combo signal — plus the two prose
corrections the fourth and fifth sections leave standing, and the item is `open`
until the last is spent.

## The negative floor is held, and the criterion rotates a sixth time (2026-08-08)

`073c4ef` answered the negative floor with one case in the file that already
holds the module, and touched nothing in `src/`. Re-run independently: the
criterion's mutant dies; the same sweep with
`--deselect ...::test_the_floor_follows_a_series_that_goes_below_zero` is
0 killed / 1 survived and the sweep restricted to `-k below_zero` is
1 killed / 0 survived, so the kill is that case's own and not an aggregate of
the eight that were already there. `tests/gui` is 111 passed.

Three of the case's four assertions kill the mutant independently — the floor
itself, the first point on the bottom edge, and zero drawn above it — which is
what makes it a case about the docstring's second half rather than about one
returned number. The fourth is the one worth naming: `top == -2.0 + 5.0 * 1.06`
is the first assertion in the file to pin `_HEADROOM` numerically at all
(`test_the_peak_is_drawn_below_the_top_edge` only asks `top > 4.0`), and it
pins it as a literal rather than by importing the constant, which is the
direction
`findings/loop/2026.08.08-a-literal-pin-replaced-by-the-constant-it-now-reads-stops-being-a-pin.md`
argues for. It also pins the thing the mutant does not reach: that the headroom
is measured over the whole span from the negative floor rather than from zero.

**Seventh rotation, and it is `gui/app.py`'s `source_fed_nodes` clause** — the
one the 07.12 section left, and the first rotation whose subject is a behaviour
the tree can get wrong rather than a number no fixture separates.
`and node.node_id in source_fed_nodes(pipeline) ==> and False` is verified red
at 0 killed / 1 survived under `uv run pytest -q tests/gui
tests/bench/test_gui_loop_budget.py` on the tree this review closes. The oracle
stays wide because `app.py` is walked by both files. The fixture the section
already names is a walk that stops on the source-fed node and asks
`viewport_node`.

`param_form`'s combo signal is deliberately not next: the item's own section
says the surviving side is the wrong one, so it is a behaviour change with a
choice in it — the narrow signal swap or a no-op guard — and a rotation that
handed it to a worker as a fixture task would have it settle that choice on the
way past. `window.moved_to`'s clamp is the guard-with-no-caller shape the item
calls the least of the four, and it goes last. Two mutants and the two prose
corrections stand after this one, and the item is `open` until the last is
spent.

## The viewport's refusal is held, and the criterion rotates a seventh time (2026-08-08)

`2843e4e` answered the `source_fed_nodes` clause with `tests/gui/test_app.py`,
the module's first file of its own, and touched nothing in `src/`. Re-run
independently: the criterion's mutant dies, and the same sweep with
`--ignore=tests/gui/test_app.py` is 0 killed / 1 survived, so the kill is the
new file's own rather than the run's word for it. `tests/gui` is 112 passed
(was 111). The status the worker left was `awaiting-review` and `done_when` is
untouched.

The kill is what establishes the shelf resolved `crop`, and the case's own
second half does not — which is the residue. Its docstring says standing on the
node below is what separates "the window has no picture to show" from "the
window declines to show one", because a case asserting only the `None` "would
pass on a shelf that had never resolved `crop` at all". Half true: with
`crop`'s spec absent, `viewport_node` at the root falls past the region clause
into `frame_bearing`, which returns `None` on the missing spec — and one node
down `frame_bearing` resolves `downsample` and returns `_BELOW` regardless. So
the added assertion rules out a shelf that resolved *nothing*, not a shelf that
resolved everything but the subject. What separates them at case level is an
assertion about `crop`'s own spec — the same node walked where it is not
source-fed, whose `viewport_node` is then `crop` itself. The mutant covers this
today; the sentence names a guarantee the assertions do not carry.

**Eighth rotation, and it is `window.moved_to`'s clamp** — the last of the four
the 07.6 section named. `length = min(window.frame_count, frame_count) ==>
length = window.frame_count` is verified red at 0 killed / 1 survived under
`uv run pytest -q tests/gui` on the tree this review closes. The oracle narrows
to `tests/gui` because `window.py` is not walked by the budget file.

This one is the guard-with-no-caller shape and the criterion cannot see the
difference: the clamp only bites for a window longer than its source, which the
bar cannot currently produce, so a case that calls `moved_to` directly will kill
the mutant whether or not anything in the tree can reach it
(`findings/loop/2026.08.08-a-case-that-calls-the-guard-directly-cannot-see-the-caller-that-pre-empts-it.md`).
A direct call is not thereby wrong here — `moved_to` is a module-level function
of the timeline's geometry surface and `test_geometry.py` already holds its
neighbour that way — but the rotation owes the second question with it: whether
any gesture the bar offers can hand `moved_to` a window longer than the source.
If the answer is no, deleting the clamp is a source change with a choice in it
and comes back to review rather than being settled on the way past.

`param_form`'s combo signal stays where the seventh rotation left it, for the
reason given there. After this one the mutants are spent and what remains on the
item is that choice and the two prose corrections — `canvas.py`'s guard comment
and `frame_at`'s two-variant sentence — so the item is `open` until they are.

## The window algebra is held, and the criterion leaves mutation (2026-08-08)

`6ef3e37` answered the clamp with `tests/gui/test_window.py`, the module's first
file of its own, and touched nothing in `src/`. Re-run independently: the
criterion's mutant dies, and the same sweep with
`--ignore=tests/gui/test_window.py` is 0 killed / 1 survived, so the kill is the
new file's own rather than the run's word for it. `tests/gui` is 113 passed (was
112). The status the worker left was `awaiting-review` and `done_when` is
untouched.

The second question the seventh rotation attached to this one — whether any
gesture can reach the clamp — was answered no and measured rather than read,
which is what the rotation owed
(`findings/2026.08.08-no-gesture-hands-the-window-algebra-a-span-longer-than-its-source.md`).
**The source decision it deferred is taken here: the clamp stays.** `moved_to`
is a module-level function whose docstring states a total contract — a window
starting at `origin`, clamped to the source — and the clamp is what makes that
sentence true of an argument the type permits. Deleting it would trade a guard
for a `SourceSpan` refusal raised out of a function whose job is to return a
drawable window, and it would do so on the strength of today's caller set, which
`TimelineBar.set_window` is public precisely to let move. The finding is closed
on that ruling.

One residue the finding leaves, corrected here. Its first open question names
`Strip._window_from_x`; the tree holds `TimelineStrip._dragged_to`, and the span
in question is `bar.py:435`. Swept independently, `end=max(self._frame_count, 1)
==> end=self._frame_count` survives `uv run pytest -q tests/gui` — but it is
unreachable rather than unfixtured, and by the same argument as the clamp one
degree further on: `_dragged_to` takes that branch only when `self._window is
None`, `whole_of` returns `None` only at zero frames, and `_on_source_changed`
disables the strip there. A case would have to call `_dragged_to` directly on a
disabled widget, which asserts the tree's arithmetic rather than any behaviour.
It is recorded, not rotated.

**The mutants are spent, and the criterion is now the two prose corrections** —
`canvas.py`'s guard comment, whose second clause names a consequence
(`np.zeros_like` is the low extreme of the ramp) that the branch produces rather
than avoids, and `frame_at`'s docstring, which charges one denominator with two
off-by-ones only one of which is its. The criterion checks that each false
clause is gone and that the true half beside it has survived, so it is a
replacement and not a deletion; it is red on the tree this review closes.

After that the item holds one thing and it is not a rotation: `param_form`'s
combo signal, where the surviving side is the wrong one and the fix is a choice
between the narrow signal swap and a no-op guard that would also cover a spin
box arrowed back to where it started. That is Kendrick's to settle, not a
worker's on the way past, and the item closes when it is settled.

## The prose is corrected, and the item is deferred on the choice (2026-08-08)

`64b2bca` answered both prose corrections and touched no branch. Re-run
independently: the criterion is `exit=0`, `tests/gui` is 113 passed, and the
`src/` half of the diff is comment and docstring lines only, so "prose only"
holds by inspection rather than by the count. `frame_at`'s two variants are
re-derived here and both numbers are the code's: under `x / (width - 1) *
frame_count`, ten frames in a 1000-px band put frame 9's boundary at 899.1 and
every x from there to the right edge still names it; under `x / width *
(frame_count - 1)` the boundary is 1000, which is outside the band. `done_when`
was untouched and the status the worker left was `awaiting-review`.

One residue, and it is the same sentence one degree on. The replacement comment
in `image_of` says the guard "is not visible in the pixels" without the clause
the finding it cites carries — that verdict is scoped to a constant frame *that
carries no positive infinity*, and the finding's sole open question is whether
the graph can produce one. Measured again here: `np.array([[5, 5, inf]])`
guarded draws `0 0 0` and unguarded draws `0 0 255`. A reader who took the
unqualified sentence at face value would read the branch as pure arithmetic
hygiene and could delete it for pixels that would then move. Shape recorded in
`findings/loop/2026.08.08-a-correction-inherits-the-findings-citation-and-drops-its-scope-clause.md`;
the one-sentence fix is queued rather than folded, because of what follows.

**The item is `deferred_for: decision` rather than `done` or `open`.** Its
criterion is green and its mutants are spent, but its body still holds
`param_form`'s combo signal, which the seventh rotation and the one above both
refuse to hand a worker: the surviving side is the wrong one and the fix is a
choice between the narrow `activated` → `currentIndexChanged` swap and a no-op
guard in `_edit`/`Session.commit`. `done` would certify that as settled; `open`
would serve a green criterion to a worker with nothing to do, which is the
failure `findings/loop/2026.08.07-a-worker-on-a-reopened-item-leaves-the-status-the-review-set.md`
records. Deferred on a decision is what the third `DEFER_REASONS` case is for,
and it takes the item out of the queue until Kendrick clears it.

The criterion is rewritten with it, because the prose one is spent and a spent
criterion is green from here on. The new one is deliberately fix-agnostic —
both candidate fixes make the same behaviour true — and it is red today at
`exit=5`, no case matching. What the case must assert, which the selector
cannot: opening the popup and re-selecting the entry the combo already shows
appends no `SetParam` and no undo entry. A review closing this item checks that
assertion and not only the exit code
(`findings/loop/2026.08.07-a-k-selector-and-the-prose-name-beside-it-are-two-criteria.md`).

## The guard comment carries the finding's scope clause (2026-08-08)

The residue the section above leaves is closed: `image_of`'s guard comment now
scopes its verdict the way the finding it cites does — not visible in the pixels
*on a constant frame carrying no positive infinity* — and names the exception in
the comment rather than leaving it a click away, so a reader deciding whether the
branch can go sees the one input on which it moves them. Prose only: no branch
moved, and `tests/gui` is 113 passed either side. The item's status,
`deferred_for` and `done_when` are untouched; what it is deferred on is still
`param_form`'s combo signal and still Kendrick's.

## Ruled 2026-08-09: the no-op guard lives in Session.commit

Kendrick's ruling, from the three shapes the rotations laid out: the document's
only writer drops a commit whose value equals the one it already holds —
nothing appended, no undo entry, no re-plan. `activated` stays, so
commit-on-intent stands; the same rule covers the spin box arrowed back to its
start and every future editor by construction, because 07.3 left exactly one
writer for it to live in. The equality test is part of what being the writer
means — a write is a change, a non-change is not a write — and is stated so
where it lands, rather than as an exception to session's computing-nothing
line. A live drag is untouched: its stream is distinct values, all real; only
exact no-ops die. The criterion below is already fix-agnostic and red, and is
unchanged by this ruling.

One residue the work run leaves, folded here rather than minted because it is
the same gesture one layer up. The guard is in `Session.commit` as ruled and the
document half of the ruling holds — nothing appended, no undo entry — but the
*re-plan* half does not, because the refill is not driven by the document.
`ParamForm._edit` emits `edited` after `issue` returns and `app.py` connects
that to `refill_graph` unconditionally, so a re-selected entry still marks the
graph stale and renders a window whose pipeline has not moved. The keys are
identical, so nothing recomputes and the store serves it; what the user sees is
the stale mark flashing for an edit that was dropped. The same is true of
`kind_editors.py`'s `edited`. Closing that means the widgets learning whether
the write took — which is a second question about what `issue` returns, not a
per-editor guard — and it is deliberately not done here: the criterion does not
reach it and the ruling put the refusal in one place on purpose.

## The writer holds, and the criterion rotates onto the notification (2026-08-09)

`a5054b8` answered the ruling in `Session.commit` and nowhere else. Re-run
independently: the criterion is `1 passed, 7 deselected`, the suite is 1020
passed, `ruff format --check` and `ruff check` are clean, and the case is red
for the right reason — with the two guard lines removed byte for byte from the
committed file it fails at `assert session.project is chosen`, printing two
equal documents. The identity assertion is what makes that red possible;
equality would have passed on the unguarded tree. `done_when` was untouched and
the status the worker left was `awaiting-review`.

The early return also skips `self._future.clear()`, which the diff does not
mention and is right: a value equal to the present one is not a divergence, so
a redo branch survives a no-op the way it survives no write at all.

**The residue folded above is the criterion now, and the item stays open for
it.** Read against the tree: `ParamForm._edit` emits `edited` after `issue`
returns, `app.py:425` and `:476` connect that to `refill_graph`,
`refill_graph` calls `TuningLoop.request_refill`, and that calls
`GraphPanel.mark_stale` before arming its timer. So the gesture the commit just
made document-invisible still puts `_STALE_NOTICE` over the plot and schedules
a render, for an edit that was dropped. The ruling's own third clause — "no
re-plan" — and `commit`'s docstring line about "no new value for anything
downstream to re-plan from" are both true of the *value* and false of what the
user sees, because the refill is driven by a signal rather than by the
document.

The new criterion is fix-agnostic between the two shapes the residue names —
the widgets learning from `issue`'s return whether the write took, or the
notification being derived from the document rather than emitted beside it —
because it asserts the panel and not the signal. It is red today at `exit=5`,
no case matching. What the case must assert, which the selector cannot: driving
the shown entry of a generated combo through a real `MainWindow` leaves the
graph panel carrying no stale notice, while an actual change to the same combo
does. Both halves, or the case passes on a window whose panel was never marked
stale by anything.

## The notification is held, and the item is done (2026-08-09)

`e97c2f2` closed the last thing on this item. Re-run independently: the
criterion is `1 passed, 1 deselected`, `exit=0`; the suite is 1021 passed,
`ruff format --check` and `ruff check` clean, `lint-imports` 8 kept / 0 broken.
The case asserts what the criterion could not say — the shown entry re-selected
through a real `MainWindow` leaves `graph.is_stale` false with `can_undo()`
false, and a real change to the same combo two gestures later sets it — so both
halves are there and the prose half of the criterion is met as well as the exit
code. `done_when` was untouched and the status the worker left was
`awaiting-review`.

The red is this commit's own and not the run's word for it: with the four
`src/` files restored to `e97c2f2^` byte for byte, the case fails at
`assert not window.graph.is_stale`, and restoring them turns it green. That
also disposes of the one vacuity risk the first half carries on its own — a
PageDown-and-Return that reached nothing would leave the panel unmarked and
pass — because under the unfixed tree that same gesture *does* mark the panel,
which it can only do by reaching the combo.

**The scope call the run flagged stands.** `issue` returning `bool` rather than
the present `Project` is the mechanism of the shape the criterion was
fix-agnostic between, not work beside it: the only readers are
`save_screen._checkoff`, which ignores it, and four cases in
`test_intents.py`, which ignore it too, and a function returning a value every
caller can read off `session.project` is what made the drop unobservable. The
choice of that shape over deriving the notification from the document is the
worker's and is argued — the writer has already computed the equality — and it
keeps the ruling's one-writer property: `Session.commit` still decides, and the
surfaces only ask.

One thing about where the rule is written, not a defect. It is stated three
times — `Session.commit`, `issue`, `_Editor._commit` — and not at all in
`ParamForm._edit`, which is the emitter the residue named first. That is the
right density rather than an omission: the `if` is legible and the reason is a
click away in the function it calls. The `edited` comments on both surfaces
still read "the document has just been written to", which was approximately
true before and is exactly true now.

The item closes with every rotation spent, both prose corrections landed, and
the combo signal settled by Kendrick's ruling above rather than by a worker on
the way past.
