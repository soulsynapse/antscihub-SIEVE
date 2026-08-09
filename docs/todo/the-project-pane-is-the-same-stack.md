---
title: The project pane is the same stack with projects for cards
step: "09.5"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k project_cards"
opened: 2026-08-09
---

# The project pane is the same stack with projects for cards

The project position shows the library card above a stack of project cards —
name, what the project holds, when it was last opened — selected the way a
step is: the accent edge is "current", ↑/↓ move the selection, a single click
selects and a double click enters the pipeline position. No platform list
widget; the first thing a user sees should not be the one surface that does
not look like SIEVE. MOCKUP-MAP.md row "Project selector" —
`build_project_pane`, `_project_card`, `Control.open_project` in the
referent. The pipeline stack's fixed header names the selected project, so
moving the selection moves what that header says.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k project_cards
    119 deselected in 0.65s
    exit: 5

## Ruled 2026-08-09 at this item's review: the last sentence above is wrong

"The pipeline stack's fixed header names the selected project, so moving the
selection moves what that header says" holds in the referent because selecting
*is* opening there. It does not hold in v3, where the pipeline position shows
the open session's chain and the accent is a second selection that opens
nothing — a header that renamed itself on an arrow key while its cards stayed
the previous project's would state something false. The work named the open
project in that header and left the accent alone, and that is the behaviour
this review ratifies. The sentence is the part that is wrong, and it is
recorded here rather than edited out because the item is the record of what was
asked for.
