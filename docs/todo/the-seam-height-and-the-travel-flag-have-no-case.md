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
