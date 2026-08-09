---
title: The library mints a project and the selected card opens its folder
step: "09.5.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k open_location && uv run pytest tests/gui -q -k new_project && uv run pytest tests/unit/test_pipeline_model.py -q -k no_footage"
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

## OPEN LOCATION landed; NEW PROJECT cannot be written (2026-08-09)

Half of this is built. `chrome.chrome_button` is the dress's one home,
`project_select.reveal` opens the document's folder, the pane's third signal
carries which card was pressed, and `MainWindow.reveal_project` turns it into
a path. The folder and not the file, because no file manager can be asked
portably to open with one entry selected, and because a project on disk *is*
its folder (`PROJECT_SUFFIX`'s note: the document sits beside its footage and
above the child folders a run wrote). One consequence the referent could not
show: `projects_in` scans a single directory, so every card in one library
answers with the same folder. That is a fact about a scanned library, not a
defect in a per-card verb — the button says where *this* project lives, and in
a library they live together.

**NEW PROJECT is not built, and the criterion above is green without it.**
`Project.source` is a required `SourceRef` whose `path` validator refuses an
empty string, so "an empty project — no sources, no chain" has no valid
document under schema v1. The item hands that decision to v3; it is a schema
decision and not a widget's, so it stops here rather than riding along with a
GUI step. The three ways out, and why none is a run's judgement call:

- **A document may name no footage** — `source: SourceRef | None`. Honest, and
  the state is real: the mockup's walk is mint, then add sources on the card
  the selection landed on. It changes what a valid document is for every
  reader, which is few sites (`Project.source_path`, `relocated`, `for_video`,
  `app.open_project`, `_holds`, and the three CLI commands that go through
  `source_path` and would each owe a refusal naming the file) but is an ADR's
  ruling, since `Project`'s own docstring calls itself the whole reproducible
  unit.
- **Mint nothing on disk, hold a pending row in the window** — no schema
  change, and "the pane lists it" holds until the app is relaunched, at which
  point the row is gone and the library card's count was never counting it.
- **Ask for footage up front** — a file dialog, which `PLAN.md` Phase 7 defers
  ("does not build one from a folder of videos") and which the no-modal
  argument above leans against for the name.

So: the criterion no longer covers the whole of the item, and the review owes
it either a widening plus a ruling on the first bullet, or a strike that sends
NEW PROJECT out as its own item behind that decision.

## Ruled 2026-08-09 (Kendrick): the first bullet

[adr/a-document-may-name-no-footage.md](../adr/a-document-may-name-no-footage.md):
`Project.source` admits `None`, readers that need frames refuse by name, and
the other two exits are rejected for the reasons the section above gives —
the pending row lies after a relaunch, the dialog is the modal the referent
argues away. The review can widen `done_when` over NEW PROJECT rather than
striking it; the schema decision it was waiting on is made.

## Reviewed and widened, back to open (2026-08-09)

OPEN LOCATION holds. Its three cases were re-run and re-proved: reverting
`project_select.py`, `app.py` and `chrome.py` to the parent of `bfcecb7`
turns all three red, and because two of those reds are a missing name rather
than a wrong answer
([reverting the implementation is no proof when the item created the module](../findings/loop/2026.08.07-reverting-the-implementation-is-no-proof-when-the-item-created-the-module.md)),
the landed code was mutated as well: opening the file instead of the folder
and drawing the button on every card are both killed. The third mutant —
`on_reveal(index)` to `on_reveal(current)` — survives and is equivalent, since
the only site that connects it is inside the `index == current` branch.

`done_when` is now one command per claim rather than one `-k` disjunction over
all of them, because a widened disjunction is green for whatever it names and
does not have
([a -k disjunction is green for the disjunct that names nothing](../findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md)).
The third leg is the schema half ADR 26 ruled: `Project.source` is still a
required `SourceRef` on this tree, so the document a mint would write cannot
be built yet, and the case for it lives beside the model rather than in the
GUI suite. The GUI and the schema stay one item because one commit satisfies
both and neither has a reason to land alone — the admission exists to make the
mint writable, and the mint is the only caller that wants it.
