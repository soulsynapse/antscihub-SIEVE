---
title: The GUI skeleton's argued branches have no case
priority: normal
phase: 7
status: open
gated_on: nothing
done_when: "uv run python scripts/mutation_sweep.py --file src/sieve/gui/walk.py --mutant \"if node.node_id not in fed:==>if True:\" --mutant \"for child in children[node.node_id]:==>for child in ():\" --mutant \"return tuple(ordered)==>return tuple(pipeline.nodes)\" -- uv run pytest -q tests/gui"
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
