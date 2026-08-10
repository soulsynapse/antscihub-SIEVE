---
title: The shelf is rebuilt per keystroke and pays for it twice
status: done
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

**Folded 2026-08-09 (review of 09.9): the referent now answers the second
half.** `ff1456f` added `_StackPane` to `mockup/mockup.py` — a rebuilt pane
carries the outgoing one's scroll offset, and `reveal_current` aligns a card
too tall to fit to its head rather than centring it, moves nothing for a card
already in view, and leaves a margin so a revealed card never sits flush with
the viewport. That is the one decision this item says should be taken for both
stacks, and ADR 30 makes the referent binding on how it looks and responds, so
what is left here is re-homing it into `gui/` rather than deciding it. The
first half — `listings` re-parsing every document per arrow key — the referent
still says nothing about, because its data is inline.

**Folded 2026-08-09 (review of the folder-source item): `_reread_graph` is the
second unconditional disk read on the interactive path, and it can block rather
than cost.** `8d5a300` gave `_reread_graph` a fifth fact,
`resolve_source.resolved_sources`, which stats and lists every folder the
document's source params name. Its three callers are a project opening, a step
leaving the chain, and the window regaining activation — so every graph edit and
every alt-tab now walks the filesystem on the GUI thread, where the other four
facts are folds over memory. The cost is small for a local folder and it is the
same shape as `listings` above: work redone unconditionally because the thing
that invalidates it was not distinguished from the things that do not. A step
leaving the chain cannot have changed what a folder holds.

It is worse than a cost in one case the other half of this item does not have.
`resolved_sources` catches `OSError` for "a folder that is not mounted", which
is the exception; an unresponsive network mount does not raise, it stalls, and
`Path.is_dir` on one takes as long as the platform's timeout with the window
frozen behind it. Whichever way the first half goes — an early return, or the
read moved off the paint path — the same decision covers this, which is why it
is here rather than in a third file.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k shelf_redraw
    146 deselected in 0.61s
    exit: 5
