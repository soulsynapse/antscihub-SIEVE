---
title: The source badge's state is held and its painting is not
priority: normal
phase: 7
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k badge_painted"
opened: 2026-08-09
---

# The source badge's state is held and its painting is not

`c7b1f8b` gave the viewport the mark the drag item's ruling asked for, and the
three cases it added hold the state and the wiring: `showing_source` rises at
`_paint_viewport`'s fallback, falls on a render that lands, survives a refused
`set_values`, and `badge_text()` agrees with it. Independently swept, all four
of those die — `self._showing_source = False` in `set_values`,
`self._viewport.mark_source()` in `app.py`, and a mark forced back down after
the call.

What no case reads is the surface, which is the half the item exists for. Under
`uv run pytest -q tests/gui`, the mutant that stops the badge being drawn at all
survives:

    uv run python scripts/mutation_sweep.py --file src/sieve/gui/canvas.py \
        --mutant $'badge = self.badge_text()\n        if badge: ==> badge = self.badge_text()\n        if False:' \
        -- uv run pytest -q tests/gui
    SURVIVED  badge = self.badge_text() if badge:

So `canvas.paintEvent` can decline to draw the word and the tuning loop is green
on a viewport that says nothing — the exact state the drag item opened against,
reached by deleting four lines nothing asks about. The mark itself is drawn: a
`VideoCanvas.grab()` either side of `mark_source()` on the same frame gives
different pixels, checked by hand at this review and by nothing in the tree.
That grab is the fixture: pixels with the badge up must differ from the same
frame with it down, which is the shape 07.12's case already uses on this widget
(`window.viewport.frame` compared to an independent render) one layer out.

One line goes with it. `badge_text()`'s `and self._frame is not None` cannot be
false at any reachable call: `mark_source()` is only ever reached through
`_paint_viewport`'s `set_frame` on the line above, `clear()` lowers the flag,
and `_paint` returns before asking when there is no frame. It is the
guard-with-no-caller shape rather than a missing fixture — the case above will
not separate it — so the choice is a comment saying which caller it is for or
its removal, settled with the fixture rather than beside it.

## 2026-08-09: the armed edge lines are the same defect on the timeline strip

09.6 (`65a7c83`) gave `TimelineStrip.paintEvent` a block that draws a 3 px line
down each edge of the window while the HANDLES toggle is down, with a comment
saying why it must exist: "a user who reaches for an edge has to be able to
see, on the thing they are reaching for, whether it will answer." Seven cases
landed for the toggle and all of them read the hit test. Under
`uv run pytest -q tests/gui/test_timeline.py`, replacing that block's
`if self._handles_armed:` with `if False:` survives — the band can arm its
edges and show nothing, and the state the toggle exists to make visible is
carried by no case.

It is this item's shape rather than the expander's: `handles_armed` reads the
strip's own field, not the button's, and every mutant of the hit test dies. The
unheld layer is the one past the accessor, and the fixture is the same one this
item already prescribes — a `grab()` of the strip with the toggle down must
differ in pixels from the same window with it up. Whatever satisfies the badge
half should satisfy this one in the same commit; the criterion above names only
the badge and does not reach it.

## 2026-08-09: the crop fan is the third, and two of its clauses live only in paint

09.8 (`3b22c20`) draws a numbered square per region and holds the run and the
drops describing an unwalked one back to a lower alpha. Seven cases landed and
every one of them reads geometry — `tile_rects`, `fanned_edge`, the hit test —
which is the module's own stated division (`FannedEdge`: "what the picture
claims is geometry, and geometry is the thing a test can read"). Under
`uv run pytest -q tests/gui -k crop_fan`, three mutants of `chain_stack.py`
survive:

    str(index + 1)                        ==> str(index)
    colour = LINE if chosen else unlit    ==> colour = LINE
    QPen(ACCENT if chosen else LINE, 1.6 if chosen else 1.0)
                                          ==> QPen(LINE, 1.0)

So the squares can be numbered from zero, every branch can be drawn at the
walked weight, and the selected square can lose its accent, with the criterion
green. Two of those are the item's own words — "numbered squares" and "the
others are the same chain, unwalked" — and neither has a geometric referent to
assert in place of the paint: the numbering and the dimming *are* the clauses.

The fixture is the one this item already prescribes, one layer in — a `grab()`
of the `RegionFan` with region 1 selected differing in pixels from the same
widget with region 0 selected — except the numbering, which wants the ordinal
read back rather than a pixel diff. The criterion above names only the badge and
reaches neither this nor the armed edges.
