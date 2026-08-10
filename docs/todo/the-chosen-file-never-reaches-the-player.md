---
title: The file the chooser writes never reaches the player, so a minted project shows nothing until it is reopened
priority: high
phase: "9"
status: open
gated_on: nothing
done_when: 'uv run pytest "tests/gui/test_source_card.py::test_the_chosen_file_reaches_the_player" "tests/gui/test_source_card.py::test_choosing_again_reopens_on_the_new_file" -q'
opened: 2026-08-10
---

# The file the chooser writes never reaches the player, so a minted project shows nothing until it is reopened

VISION's new-project scenario is mint, pick a video, and start tuning. The
first two work and the third does not: the chooser's file lands in the
document and nothing decodes it, so the user picks a clip and the window keeps
showing them the empty stack they picked it from. Closing the project and
opening it again is the only way to get the footage on screen, and nothing on
the surface says so.

The state to verify before starting: `_player.open` has exactly one caller in
`src/`, `app.MainWindow.open_project`, which reads `resolve_source.named_footage`
off the document it has just loaded. The chooser's own path is complete and
stops short of that — `param_form.PathChooser` asks, `ParamForm._edit` issues
`SetParam`, `ParamForm.edited` reaches `app.refill_graph`, and `refill_graph`
returns at `self._timeline.window is None`, which is exactly the state of a
window whose player was never opened. So the one gesture that can give a
project its footage is the one gesture that cannot ask for a decode.

This is not the source card item's leftover.
[the-source-is-a-card-in-the-walk.md](the-source-is-a-card-in-the-walk.md)
built two lines and both are drawn from the document — what `path` holds and
what the window resolved it to — and neither is a claim about the player; its
review paragraph lists what it did not reach and this is not on the list,
because at minting time the card did not exist to expose it. `high` inside
phase 9 rather than a step: every other row of that phase reshapes a surface
over footage that is already open, and this is what puts footage there at all
for a project the user made rather than one that arrived with a path in it.

Three questions the work answers rather than assumes.

**Which edit is a new source.** A path parameter changing is not it — a
checkpoint read-back is an ordinary root holding a path
([crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)),
and a graph can hold a second source root that has nothing to do with the
project's footage
([a-second-source-root-is-drawn-over-the-first-roots-footage.md](a-second-source-root-is-drawn-over-the-first-roots-footage.md)).
What the player is opened on is whatever `named_footage` answers, so the
predicate is a change to *that* answer, and re-asking it is cheap enough that
comparing the answer beats deciding which node ids may move it.

**What survives a swap.** The playhead, the bar's working window and the
region selection are all indices into the clip that is leaving.
`open_project` resets the first two by opening a player; an edit arriving
under a session that already has footage has no such reset, and carrying a
window from a 40 000-frame clip onto a 900-frame one is the same class of
wrongness as the magnification that
[a-magnification-is-a-view-of-this-footage.md](a-magnification-is-a-view-of-this-footage.md)
carries across a project. That item names "a new source" as the seam its
`reset_zoom` and its solo-drop hang off and says the two must be dropped in
one call; this item is what makes that seam exist, so whichever lands second
wires into the first rather than opening a second seam beside it.

**A folder is a legal answer.** `named_footage` reports the spelling as
written, and a source may name a directory — handing one to the decode thread
is what `_on_failed` is for, and `open_project` already does exactly that
today for a project saved with a folder in it. Matching that behaviour is the
answer here; narrowing or picking a member is
[a-folders-resolution-is-unnarrowed-and-lexicographic.md](a-folders-resolution-is-unnarrowed-and-lexicographic.md)'s
and must not be settled in passing.

`done_when` at minting, red because nothing matches:

    $ uv run pytest "tests/gui/test_source_card.py::test_the_chosen_file_reaches_the_player" "tests/gui/test_source_card.py::test_choosing_again_reopens_on_the_new_file" -q
    ERROR: not found: .../test_source_card.py::test_the_chosen_file_reaches_the_player
    (no match in any of [<Module test_source_card.py>])
    ERROR: not found: .../test_source_card.py::test_choosing_again_reopens_on_the_new_file
    no tests ran in 0.14s
    exit: 4

The second node id is the other half of VISION line 96 — pick a video, change
your mind — and it is named separately because a first open and a re-open are
different code even where they end in the same call: the first has no player
state to end and the second does.
