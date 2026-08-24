"""The canvas: what the work is looked at on, and what is drawn over it.

The word the panes refused (`panes.py`) — a pane could not be called the canvas
because that would be a claim about its occupant, and this is the occupant that
would have made the claim true. Naming it here rather than there is what keeps
it movable: the canvas is a view, so it houses in any pane (ADR-0001), and the
left pane holding it is the window's answer and not this folder's.

What a canvas is, is a thing held at its own shape and something drawn on top of
it — footage under a crop box, a plot under a cursor. The shape is the whole of
what it enforces: a canvas that let its content be stretched to the pane would
be a canvas that lied about what the user is measuring against, and every
overlay pinned to it would be wrong by the same amount.

`video_canvas/` is the first of the things it will hold. There will be others —
what a canvas is stays the same whether frames or a still or a rendered
composite is under the overlays — which is why the medium sits in a folder
inside and not in this one.

`overlay.py` is the first of the things drawn over it, and it is a file here
rather than something the canvas or the video does for a reason each of those
would have got wrong. A canvas that made one would be a canvas that knows what
a crop is, and the thing it is a stage for is not always footage; a video canvas
that drew one would be copying a full frame every tick to paint four lines, into
an array a store may have admitted. So it is a sibling of the content, handed
the same stage rect, and `over()` is the wiring in one place.
"""

from __future__ import annotations

from sieve.gui.view.canvas.overlay import CropOverlay, over
from sieve.gui.view.canvas.view import Canvas

__all__ = ["Canvas", "CropOverlay", "over"]
