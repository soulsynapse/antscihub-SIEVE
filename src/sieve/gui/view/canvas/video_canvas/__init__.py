"""The video canvas: footage on the stage. Nothing is built here yet.

Inside `canvas/` and not beside it because it is one of the things a canvas
holds and not a second kind of canvas — what the stage does with it is what the
stage does with anything that has a shape, and the parts that are only true of
video are what will land here: which frame is on screen, how a frame is decoded
in time to be, and what the playhead in the bottom pane means for both.

Both questions it was left open on are answered now, and the folder is where the
answers landed. What it decodes with is nothing: a canvas that reached for a
route would be pulling on the thread that draws. The frame is **pushed** — what
is on screen is decided where the ladder and the transport are
(`sieve.session`), and this is handed the result.

What is here is the part that is only true of video: which frame is up, whether
it is the one that was asked for or a stand-in shown while the true one arrives,
and how an array reaches the screen without the window stopping to think. That
last one is the freeze finding's rule made structural — no size hints, every
policy Ignored, and the scale done once per frame rather than once per paint.
"""

from __future__ import annotations

from sieve.gui.view.canvas.video_canvas.view import VideoCanvas

__all__ = ["VideoCanvas"]
