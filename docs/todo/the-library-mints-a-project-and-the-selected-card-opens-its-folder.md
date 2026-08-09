---
title: The library mints a project and the selected card opens its folder
step: "09.5.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k \"new_project or open_location\""
opened: 2026-08-09
---

# The library mints a project and the selected card opens its folder

Two buttons on the project position, both wearing the timeline button's dress
(the HANDLES/▶ chrome — `_chrome_button` in the referent), because the pane's
stylesheet has no QPushButton rule and the affordance should not differ by
pane.

**NEW PROJECT** sits on the library card, not at the foot of the list: a new
project is added to the library, the way another region is added on the crop
card and not in the fan that shows them. Minting creates an empty project —
no sources, no chain — in the directory the pane lists, and the selection
lands on it without entering the pipeline position: the chain pane would show
a chain the project does not have, and the next act is adding sources, which
is a knob on the card the selection just landed on. The referent takes no
name up front — the name is a knob like any other, and a modal asking for it
would be the one form in the surface that blocks the walk. What "an empty
project" is on disk is v3's to decide here; the claim that binds is that the
pane lists it afterwards, which the referent cannot state because it has no
disk.

**OPEN LOCATION** sits bottom right of the *selected* project card alone —
it acts on the selection, and the pane is rebuilt when that moves, so the
button travels with the highlight. It reveals the project's folder in the
system file manager. It was a dim glyph beside the last-opened note first,
and read as nothing; the labelled button at the card's foot is the shape
that survived being looked at.

Referent: `_chrome_button`, `add_project`, `Control.new_project`,
`_reveal_project`, `_project_card` in `mockup/mockup.py`; MOCKUP-MAP.md row
"Project selector". The 09.5 review's ruling stands unchanged: in v3 the
accent is a second selection that opens nothing, and NEW PROJECT moves that
selection, not the open session.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k "new_project or open_location"
    169 deselected in 0.67s
    exit: 5
