# The canvas

The canvas is the network editor. Its gestures are Houdini's, named one by one so that each
session builds the same feel instead of inventing one. The canvas reads and writes the document
and nothing else: a canvas rewritten from scratch against `spec/document.md` must open every saved
document. Nodes flow top to bottom: inputs on a node's top edge, output on its bottom, wires
leaving the bottom of one node and entering the top of another.

## Nodes

Assumes: Window shell.

- [x] A node is drawn as one layer above the ground, showing its tool name, one input connector
  per input on its top edge, one output connector on its bottom edge, and the display flag.
  Check: Kendrick looks.
- [x] A connector shows its type on hover, and the colour of a connector is one per product type
  so a `"gray"` output and a `"gray"` input match by eye.
  Check: Kendrick hovers.
- [x] Left-drag on a node moves it, and every selected node with it; the new positions are in the
  document.
  Check: Kendrick drags, saves, reopens.
- [x] Left-click selects one node and deselects the rest; Shift+click adds or removes one;
  Left-drag on empty canvas draws a box and selects what it encloses; click on empty canvas
  deselects all.
  Check: Kendrick does each.
- [x] Delete removes the selected nodes and every wire into or out of them.
  Check: Kendrick deletes a node in the middle of a chain.
- [x] A node that fails to resolve to a tool is drawn with its name and a mark that says so, and
  can be moved, wired and deleted like any other.
  Check: Kendrick opens a document naming a missing tool.
- [x] A node whose input is unfed is marked, and the mark follows the wiring at once.
  Check: Kendrick unwires and rewires.

## Navigation

Assumes: Nodes.

- [x] Middle-drag pans. Space+left-drag also pans.
  Check: Kendrick pans.
- [x] The wheel zooms about the cursor, so the thing under the cursor stays under it.
  Check: Kendrick zooms on a node.
- [x] H frames every node in the view; with a selection, H frames the selection.
  Check: Kendrick presses H.
- [x] Pan and zoom are not in the document.
  Check: a saved file has no view keys.

## Wires

Assumes: Nodes.

- [x] Left-drag from an output connector draws a wire that follows the cursor; releasing on an
  input connector that expects the output's type makes the wire, and the document has it.
  Check: Kendrick wires two dummies.
- [x] While a wire is being dragged, every connector it may land on is lit and every other is
  not; releasing on an unlit connector or on a node body makes nothing.
  Check: Kendrick drags a `"gray"` output over a `"bgr"` input.
- [x] Left-drag from an input connector that already has a wire picks that wire up by its
  source end; releasing on empty canvas removes it.
  Check: Kendrick unplugs a wire.
- [x] Left-drag from an input connector that has no wire draws a wire back toward a source, and
  releasing on a compatible output connects it.
  Check: Kendrick wires from the input end.
- [x] An input accepts one wire; connecting a second replaces the first.
  Check: Kendrick wires a second source into a fed input.
- [x] Y+left-drag draws a cut line, and every wire it crosses is removed on release.
  Check: Kendrick cuts three wires in one stroke.
- [x] Dropping a dragged node onto a wire whose types fit its input and output inserts it in
  that wire.
  Check: Kendrick drops a pass-through dummy onto a wire.
- [x] A wire is drawn in the accent, like the arrow in the rail was, and a wire whose types no
  longer fit after a change upstream is drawn in red and the destination counts as unfed.
  Check: Kendrick repoints a pass-through at another type.
- [x] A wire is an S-curve: it leaves the output connector straight down and enters the input
  connector straight up, with vertical tangents at both ends, whatever the offset between them.
  Check: Kendrick drags a node sideways past its source and watches the wire.

## Tab menu

Assumes: Wires.

- [x] Tab with the cursor over the canvas, or a right-click on empty canvas, opens a menu at the
  cursor listing every tool the registry found; typing filters the list; Enter or a click places
  the chosen tool as a new node at the cursor; Escape closes it with nothing placed. A right-click
  on a node, connector or wire does nothing.
  Check: Kendrick places a node each way.
- [x] Releasing a dragged wire on empty canvas opens the same menu, filtered to tools that expect
  the wire's type; the placed node arrives wired.
  Check: Kendrick drags a wire into space and picks a tool.
- [x] A tool the registry listed but could not import appears in the menu greyed, with its error
  on hover, and cannot be placed.
  Check: Kendrick breaks a dummy's import.

## Non-goals

- Subnetworks, diving into a node, or more than one canvas.
- Alt-drag to duplicate, copy and paste. Wanted later; nothing in the feel work needs them.
- Node colours, comments, stickies, or renaming a node. A node is its tool's name.
- Right-click menus on a node or wire. Every action on one has a gesture or a key; a menu is a
  later convenience. Right-click on empty canvas is the Tab menu, not a context menu.
- Snapping and auto-layout beyond the top-to-bottom layout a list-built document gets.
- Other wire shapes. Straight and Houdini's rounded stubs were considered; the S-curve was chosen
  by Kendrick as the starting point and can be revisited by looking at it.
