# The window

The frame stays on the left and the transport across the bottom. The right column, the cards, the
rail, and the open-one-tool mode with Save and Cancel are gone; in their place the right side is
the canvas with the parameter pane beneath it. The design language in `sieve_player/theme.py` and
`mock-up/design-language` still governs every surface: ground, one step per layer, the accent for
flow and for what is viewed. Read `sieve_player/window.py` for what the transport, the decoder,
the worker and the frame view expect of their host.

## Window shell

Assumes: Graph runtime, Dummy tools.

- [ ] The window opens with the frame left, the canvas top-right, the parameter pane bottom-right,
  and the transport along the bottom, with a splitter between frame and right side and another
  between canvas and pane.
  Check: Kendrick opens it.
- [ ] Decoder, worker, memo and timeline behave as before: load starts playback looping in the
  window, the display reads the memo and never waits on the decoder.
  Check: `smoke.py` passes.
- [ ] The video is a node on the canvas; its pane shows the path picker that Inputs used to hold,
  and a path that will not open is reported there and leaves what was open alone.
  Check: Kendrick picks a bad path, then a good one.
- [ ] Opening with a list of tools and opening with a document path both work; `play` accepts
  either.
  Check: `main.py` and a saved document both open.
- [ ] Save and Open of the document are reachable from the window and from Ctrl+S and Ctrl+O,
  and a saved document reopened shows the same nodes in the same places with the same params.
  Check: Kendrick saves, reopens, compares.
- [ ] A dummy still runs alone with `play([self])`, as a tool's `__main__` block does today.
  Check: Kendrick launches one.

## Seams

Assumes: Window shell.

- [ ] The document, the runtime, the canvas, the pane and the window are each a module or
  package under `sieve_player`, and imports run one way: the document imports none of the others;
  the runtime imports the document; the canvas and the pane import the document and the theme
  and neither imports the runtime, the window, or each other; the window imports all of them.
  Check: a test in `tests/` walks each module's imports and fails on any edge not listed.
- [ ] The canvas and the pane learn about a change in the graph through the document, and the
  window carries the change to the runtime; neither widget holds a reference to the runtime.
  Check: the same import test, and a grep of the canvas and pane for the runtime's name finds
  nothing.

## Parameter pane

Assumes: Window shell.

- [ ] The pane shows the selected node's settings widget, the one its tool's `settings()` returns,
  and nothing when nothing is selected. Selection, not the display flag, drives the pane, so a
  node upstream can be tuned while a node downstream is on the frame.
  Check: Kendrick selects a node other than the flagged one.
- [ ] A change in the pane reaches the runtime at once, as a knob did in the card.
  Check: Kendrick drags a dummy's control with the frame on that node.
- [ ] A series node's pane shows its trace, with the shared cursor and playhead as the card did.
  Check: Kendrick hovers the trace and the strip.
- [ ] A node whose tool exports shows its export target and button in the pane, as Outputs did.
  Check: Kendrick exports from the exporting dummy.
- [ ] An unresolved node's pane says which tool name was not found and shows its stored params
  read-only.
  Check: Kendrick opens a document naming a missing tool.

## Display flag

Assumes: Window shell.

- [ ] Exactly one node, or none, carries the display flag; the frame shows that node's output, and
  the flag is drawn in the accent on the node.
  Check: Kendrick clicks flags.
- [ ] Clicking a node's flag moves the flag there. Clicking a node's body selects it and does not
  move the flag.
  Check: Kendrick does both.
- [ ] A flagged node that the video does not reach blanks the frame and says why on it, as
  "no input" did; the flag stays where it was put.
  Check: Kendrick unwires upstream of the flagged node.
- [ ] Deleting the flagged node leaves no flag, and the frame is empty ground.
  Check: Kendrick deletes it.

## Non-goals

- A second viewport, or comparing two nodes side by side.
- Undo. It is wanted; it is a deliverable of its own once the document is the single source of
  truth, because undo is then a stack of documents.
- Any layout other than this one. Canvas across the bottom was considered and declined.
