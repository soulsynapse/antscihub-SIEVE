---
title: The scrubber window slides whole, and its handles answer only when armed
step: "09.6"
status: done
gated_on: nothing
done_when: "uv run pytest -q tests/gui/test_timeline.py::TestTheHandlesToggle tests/gui/test_timeline.py::TestTheWindowBodySlidesItWhole tests/gui/test_timeline.py::TestTheSeamUnderThePanes"
opened: 2026-08-09
---

# The scrubber window slides whole, and its handles answer only when armed

Dragging the working window's body slides the whole window along the strip;
the edge handles resize it only while a HANDLES toggle beside the scrubber is
pressed, and are inert otherwise. The divider band above the timeline is a
seam, not a grab surface. MOCKUP-MAP.md row "The scrubber" — `MockStrip`,
`build_seam` and `build_timeline` in the referent, whose behaviour landed as
Kendrick's own orchestrator instruction (2026-08-09) and is the newest
settled surface in the file. The armed/disarmed state is view state; the
window's value stays wherever the tree already keeps it — the toggle changes
only which gestures may write it, never where it lives.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k handles_toggle
    119 deselected in 0.68s
    exit: 5

## 2026-08-09: the criterion is widened to the item's other two claims

The minted `-k handles_toggle` selects `TestTheHandlesToggle` and nothing else,
so the body-drag sentence and the seam sentence — two of the item's three —
were outside it. Widened at the closing review to the three classes as node
ids rather than as a `-k` disjunction, because a disjunct naming nothing is
green and a node id naming nothing exits 4
(`findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md`,
whose open question this answers). All three classes existed when the widening
landed, so this covers work already done rather than certifying work nobody
did.
