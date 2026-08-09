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
