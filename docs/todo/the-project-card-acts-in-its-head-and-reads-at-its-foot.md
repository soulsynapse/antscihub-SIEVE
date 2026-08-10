---
title: The project card acts in its head and reads at its foot
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'when_is_under_what_it_holds or card_arrow_enters'"
opened: 2026-08-09
---

# The project card acts in its head and reads at its foot

The referent's project card was rearranged: last-opened moved out of the head,
where it sat beside the name and took the first place the eye lands, and down
under what the project holds; the head now carries the same `→` and `✕` a step
card does. `project_select._project_card` still draws the old arrangement, so
the built pane and the referent disagree about a surface both claim to be the
same stack. MOCKUP-MAP.md row "Project selector"; `_project_card`,
`_open_project_button`, `_close_project_button`, `Control.close_project` in
`mockup/mockup.py`.

The line the user only ever reads belongs where reading ends and the line they
act on does not compete with it — which is the argument 09.5.1 already made
about OPEN LOCATION being a labelled button at the foot rather than a dim glyph
beside the note. That glyph is why the head can now hold two: they are the
step card's glyphs, in the step card's place, and a user who has walked one
stack has already learnt them.

`→` is the double-click offered to the pointer. Entering a project is ↑/↓ then
→ on the keyboard and a gesture the surface never mentions on the mouse, which
is the same hole `_settings_button` fills on a step card. In v3 it emits
`opened`, the signal that already exists — no new verb, just a second way to
raise it.

**`✕` is not buildable on this tree and the criterion above does not cover
it.** In the referent a library is a Python list, so closing a project deletes
the row and the folder on disk is untouched. In v3 the library *is* a folder
(`project_select.projects_in` scans one directory and the cards are what it
returned), so there is no state in which a project is out of the library and
its file is still in the folder — a `✕` that only redrew would put the card
back on the next scan. The three ways out, none of them a run's judgement call
because each decides what happens to a user's data:

- **Delete the document**, to the trash where the platform has one. Matches the
  word `✕` and matches what the card is a card of, and is the only exit that
  survives a rescan. It is also the one act in the surface that destroys work,
  under a glyph that elsewhere means "drop this step", which is undoable by
  adding one back.
- **Move it out of the library folder** — an archive subfolder, which
  `projects_in` skips because it is not recursive. Reversible, and a scan-shaped
  answer to a scan-shaped library, at the cost of a folder the user did not ask
  for and will find.
- **Drop the `✕` from the referent instead** and leave closing to the file
  manager OPEN LOCATION already reaches. The mockup would lose a button it just
  gained, which is a real answer: the pointer hole `→` fills is a hole, and the
  one `✕` fills may not be.

The referent disables `✕` on the last remaining card, on the source step's
precedent — every card carries the same buttons in the same place, and what
stops this one is that every position past the project pane is drawn about a
project. Whether v3 owes the same guard depends on which exit above is taken:
an empty scanned folder is a state `MainWindow` can already be launched into
(09.5.1's `library=`), so it is not obviously the referent's constraint.

So the criterion is owed a third leg once that is ruled, or the `✕` half is
owed a strike into its own item behind the decision — the shape 09.5.1 was in
when NEW PROJECT stopped on a schema question.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k "when_is_under_what_it_holds or card_arrow_enters"
    181 deselected in 0.65s
    exit: 5

## Folded 2026-08-10: the glyphs this card is to copy are not in the referent's order

"The same `→` and `✕` a step card does" is the argument above, and the step
card it copies from is itself out of order. The referent's head is
`→ ⇄ ◆ ✕` (`mockup.py`, the four `head.addWidget` lines of `_card`);
`chain_stack.ChainStack._build_card` draws `→ ◆ ⇄ ✕`. The swap button landed
last (09.10) and went in beside the remove rather than beside the settings,
which is how the two came apart — and neither side argues an order, so what
is settled is only that they disagree about a surface the map calls the same
one. One commit fixes both: the step card's head is what the project card's
head is defined as a copy of, so putting them in one order is the same edit as
giving this card two of them.

The tests reach these buttons positionally — `findChildren(QToolButton)[2]` is
"the ⇄, which is the third" in `tests/gui/test_swap_box.py`, `[3]` is "the ✕,
which is the last" in `tests/gui/test_reads_past.py` — so reordering moves what
those helpers return and both docstrings state the index they are asserting.
Whichever order wins, the helpers should find their button by its glyph: an
index that silently becomes another button is how a reorder passes a suite it
should have reddened, and this fold is that reorder.

The rest of the referent's buttons were checked at the same time and are not
owed anything here: `⇄ ◆ ✕ →`, the crop `+`/`−`, ADD STEP, the offer buttons,
NEW PROJECT, OPEN LOCATION, ▶ and HANDLES are all built and wired, the source
card's `…` browse is
[the-source-is-a-card-in-the-walk](the-source-is-a-card-in-the-walk.md), and
Run is on the output step's form (`save_screen.py`) where the map puts it.
