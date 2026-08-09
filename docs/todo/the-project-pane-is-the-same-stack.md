---
title: The project pane is the same stack with projects for cards
step: "09.5"
status: awaiting-review
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
