---
title: The shelf is rebuilt per keystroke and pays for it twice
status: open
gated_on: nothing
priority: high
phase: "9"
done_when: "uv run pytest tests/gui -q -k shelf_redraw"
opened: 2026-08-09
---

# The shelf is rebuilt per keystroke and pays for it twice

09.5 made the project position a card stack whose selection is the window's, and
`MainWindow.select_project` moves it by throwing the whole pane away and building
a new one. Two things fall out of that, measured in
[findings/2026.08.09-the-shelf-reparses-every-project-per-arrow-key.md](../findings/2026.08.09-the-shelf-reparses-every-project-per-arrow-key.md).

**Every arrow key re-reads and re-parses every project document in the library.**
`_build_project_select` calls `listings(self._projects)`, and `listings` opens and
parses each file to derive the two lines a card carries. Over forty projects that
is about 72 ms per keystroke, essentially all of it YAML. Nothing about a card's
text changed when the accent moved, so the whole of that is paid for nothing;
holding Up at the top of the list pays it too, because the rebuild is
unconditional and there is no early return for an index that did not move.
`select_project`'s docstring says the opposite — "a selection that opened a
document would make arrowing down a library the most expensive keystroke in the
app" — and that is what redrawing the shelf already does. Whichever way the code
goes, that sentence goes with it.

**The selection walks off the bottom of the scroll area and nothing follows it.**
A fresh `QScrollArea` starts at the top, so the accent silently leaves the visible
region on the way down and a user who scrolled by hand is snapped back to the top
by the next arrow key. Measured: after ten `go_down`s over a forty-project library
the selected card is index 10 and the scrollbar is at 0 of 1926.

The second half is not the shelf's alone — `chain_stack.PipelinePane` is rebuilt
the same way on every move of the walk and loses its scroll position identically,
which is a longer stack than most libraries. The remedy is one decision about what
a rebuilt stack carries over from the pane it replaces, and it should be taken for
both rather than patched into the shelf.

The first half is the shelf's alone: the pipeline stack rebuilds off an in-memory
graph and touches no disk. The two live in one item because one commit that gives
a rebuilt stack a scroll position and a reason not to re-read what did not change
satisfies both, and splitting them would put the same decision in two files.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k shelf_redraw
    146 deselected in 0.61s
    exit: 5
