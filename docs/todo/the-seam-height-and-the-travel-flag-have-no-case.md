---
title: The seam's height and the strip's travel flag are argued and held by nothing
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run python scripts/mutation_sweep.py --file src/sieve/gui/layout.py --mutant \"_SEAM_HEIGHT = 3 ==> _SEAM_HEIGHT = 30\" -- uv run pytest -q tests/gui/test_timeline.py"
opened: 2026-08-09
---

# The seam's height and the strip's travel flag are argued and held by nothing

Two lines from 09.6 (`65a7c83`) whose reason is written down at length and
whose value no case can see. Both survive mutation under `tests/gui`.

`layout._SEAM_HEIGHT` is 3 because a splitter handle is 3 — `chrome.py`'s
`QSplitter::handle` rules say so, and the seam's whole argument is that the one
divider that cannot be dragged must not be the one that looks different. The
case that landed with it asserts
`seam.maximumHeight() == build_seam().maximumHeight()`, which compares the
composed seam to a freshly built one: the same expression on both sides, green
for any value of the constant. `_SEAM_HEIGHT = 30` survives. What the case has
to assert instead is the agreement the constant exists for — the seam's height
against the handle height the stylesheet declares, so that moving one and not
the other goes red.

`TimelineStrip._travelled` is set in `mouseMoveEvent` and its comment says why:
"did it move" has to be a fact and not a guess made from the release position.
The release then recomputes `self._travelled or frame != self._grab_from`, so
on every path a case drives, the recomputation alone decides. Replacing the
whole move-time assignment with `pass` survives. The case the flag exists for is
the drag that travels and comes back: press at 500, move to 600, release at
500. Under the mutant that is a seek the user did not ask for, in the middle of
a window slide.

The `done_when` above is the seam half, because it is the one with a wrong
assertion rather than a missing one; the travel case is the second half and its
own sweep, `--mutant "self._travelled = self._travelled or self._hover != self._grab_from ==> pass"`
over the same file, is what closes it.

## 09.7's painter has the same two shapes (2026-08-09, review)

Two more lines of Phase 9 GUI, from `173d535`, whose reason is written down at
length and whose value no case under `tests/gui` can see. Same claim, same
remedy, so they are folded here rather than minted beside.

`ChainColumn._paint_edge`'s `painter.drawPolygon(arrowhead(end))` is the line
that puts an arrowhead on the picture at all. `arrowhead()` itself is asserted
as a function — the shoulders are above the point, the apex is the point — and
that case never renders, so `==> pass  # ` survives the whole of
`tests/gui/test_chain_edges.py`: every edge in the stack loses its head and
nothing goes red. What the occlusion case reads at the passed card is the
line's pixels, not the head's. The case this needs is the arrowhead's own
pixels in the gap, a few rows above where the line ends.

`ChainColumn.__init__`'s `tuple(edge for edge in edges if edge[0] < edge[1])` is
the cycle guard, and its comment argues it: a walk that puts a producer below
its reader is a cycle, which `walk.py` still has to draw and which no downward
line describes. `==> tuple(edges)` survives all of `tests/gui` — no fixture
anywhere has an upward edge, so the clause runs only in the branch nothing
takes. The case is a pane whose `reads` name a later position: the guard drops
the edge, and the mutant draws an arrowhead pointing down at the card that
produced it.

Both sweeps are over `src/sieve/gui/chain_stack.py` against
`uv run pytest -q tests/gui/test_chain_edges.py`, and neither is in `done_when`
above, which sweeps `gui/layout.py`: `mutation_sweep.py` takes one `--file`, so
the union of the four is not a single command. Whoever closes this closes all
four and says so — the criterion certifies the seam alone.
