"""The video canvas: footage on the stage. Nothing is built here yet.

Inside `canvas/` and not beside it because it is one of the things a canvas
holds and not a second kind of canvas — what the stage does with it is what the
stage does with anything that has a shape, and the parts that are only true of
video are what will land here: which frame is on screen, how a frame is decoded
in time to be, and what the playhead in the bottom pane means for both.

Standing empty on purpose. What it decodes with, and whether the frame it shows
is pulled by the canvas or pushed by whatever is playing, are open — and the
folder exists so that the answer lands in a file whose place was decided before
the question was, rather than the other way round.
"""

from __future__ import annotations

__all__: list[str] = []
