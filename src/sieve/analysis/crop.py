"""What a crop is, what may be done to one, and where a drawn one lands.

A crop is four integers in source pixels — which is `frame.form.Form.rect`'s
spelling and not a coincidence: a step's form is the crop plus a sampling and a
pixel format, so a crop that measured itself any other way would need converting
at every use.

Pure. No Qt, no widgets, no canvas. What arrives here is a rectangle and the
rectangle the picture was placed in; what leaves is a rectangle in source pixels
that is legal, and legality is three things at once:

**On the frame**, because a crop is a selection of source pixels and there are
no others.

**At least `MINIMUM` on a side.** A box with no area has no aspect, and every
downstream fit divides by it — and `frame.form.build` on a form with no area
returns an empty array without complaining, so a crop that lost its area would
turn up much later as a picture that is not there.

**Even on every edge**, which is the one that is not obvious. 4:2:0 stores chroma
at half resolution in each direction, so an odd offset or an odd width puts a
crop's edge in the middle of a chroma sample: the encoder rounds it, and a
stored chunk comes back a pixel adrift from the frame it was cut from. The
explorers snap to even with the comment `yuv420 wants even` and this is that,
with the reason written down.

**The order the three are applied in matters**, and the order here is the
explorers'. What this module adds to them is not a better clamp — it is the
same one, out of a GUI method and into somewhere it can be called and checked,
with the mapping from a drawn rectangle beside it. Idempotence is asserted
because a clamp that moves a value it has already approved is one whose editor
oscillates: push, corrected, push, corrected.
"""

from __future__ import annotations

#: The shortest side a crop may have, in source pixels. Carried across from the
#: explorers, where it is the floor a rubber band is allowed to leave. A cut
#: rather than a measurement, and even, so that the even-alignment below never
#: has to choose between two of the three rules.
MINIMUM = 64

Rect = tuple[int, int, int, int]


def _even(value: int) -> int:
    """Down to the nearest even number. Down and never nearest.

    Rounding to nearest would sometimes round *up*, and up is the direction
    that can push an edge off the frame after it has already been clamped onto
    it. Down can only ever make a crop smaller, which is a thing the minimum
    already guards.
    """
    return value - (value % 2)


def clamp(rect: Rect, frame_width: int, frame_height: int,
          minimum: int = MINIMUM) -> Rect:
    """The nearest legal crop to `rect`: on the frame, big enough, even.

    This is `tool-explorer.py`'s `_crop_drawn`, lifted out of a GUI method so
    that it can be called and checked. The five lines are the settled ones and
    the order is theirs: the offsets are clamped against the *minimum*, then
    the extents against what is left, then everything is snapped down to even.

    Idempotent, and correct because `MINIMUM` is even — snapping an extent down
    by one from an even floor is what would break it, and cannot. A version
    that reordered these to make the invariant hold for an odd floor too is
    gone, along with the branch it needed: it was machinery for an input that
    does not exist.

    **A frame smaller than `minimum` is out of scope, and deliberately not
    handled.** A recording is not sixty-four pixels wide. An earlier version of
    this module invented that case, returned an arealess rect for it, then
    raised for it, and the checking of it was the only place either behaviour
    was ever exercised — the explorers, which have drawn thousands of crops,
    simply never had the problem. Code that answers a question nothing asks is
    code somebody later has to understand.
    """
    x, y, width, height = (int(round(v)) for v in rect)
    x = max(0, min(x, frame_width - minimum))
    y = max(0, min(y, frame_height - minimum))
    width = max(minimum, min(width, frame_width - x))
    height = max(minimum, min(height, frame_height - y))
    return tuple(_even(v) for v in (x, y, width, height))


def to_source(drawn: Rect, placed: Rect, frame_width: int,
              frame_height: int, minimum: int = MINIMUM) -> Rect:
    """A rectangle drawn over a placed picture, as source pixels.

    `placed` is where the picture actually is in the drawer's own coordinates —
    the stage rect, which `gui.view.canvas` emits precisely so that every layer
    reads the same rectangle instead of each working it out and agreeing by
    luck. Passed in rather than reached for: this module knows nothing about
    what drew it, and a version that asked a canvas could only ever be used by
    that canvas.

    The result is clamped, so a drag that started off the picture or ran
    backwards produces a legal crop rather than an error.
    """
    px, py, pw, ph = placed
    if pw <= 0 or ph <= 0:
        return clamp((0, 0, frame_width, frame_height), frame_width,
                     frame_height, minimum)
    scale_x = frame_width / pw
    scale_y = frame_height / ph
    dx, dy, dw, dh = _forwards(drawn)
    return clamp(
        (round((dx - px) * scale_x), round((dy - py) * scale_y),
         round(dw * scale_x), round(dh * scale_y)),
        frame_width, frame_height, minimum)


def to_placed(rect: Rect, placed: Rect, frame_width: int,
              frame_height: int) -> Rect:
    """A source-pixel crop, back in the coordinates the picture was placed in.

    The other direction, for drawing the box that was typed rather than dragged.
    It lives beside `to_source` because the two are one mapping read both ways,
    and a second implementation of the arithmetic somewhere else is how a box
    comes to sit a little off the crop it claims to be.
    """
    px, py, pw, ph = placed
    if frame_width <= 0 or frame_height <= 0:
        return placed
    scale_x = pw / frame_width
    scale_y = ph / frame_height
    x, y, width, height = rect
    return (round(px + x * scale_x), round(py + y * scale_y),
            max(1, round(width * scale_x)), max(1, round(height * scale_y)))


def _forwards(rect: Rect) -> Rect:
    """A rectangle with positive extents, whichever corner it was started from.

    Not called `normalised`, though Qt's own method for this is: a normalised
    crop is a different thing this tree deliberately does not have, and a
    helper wearing the name would make a reader think it did.

    A drag runs in whatever direction a hand moves, and the width of a
    right-to-left one is negative. Handled here rather than by whoever is
    dragging, because every dragger would otherwise handle it and one would
    forget.
    """
    x, y, width, height = rect
    if width < 0:
        x, width = x + width, -width
    if height < 0:
        y, height = y + height, -height
    return x, y, width, height


def whole(frame_width: int, frame_height: int,
          minimum: int = MINIMUM) -> Rect:
    """The whole frame as a crop, legal.

    What a recording that nobody has drawn on is about. Not a claim that this
    is the right thing to open with — that is undecided, and both explorers
    hardcode a rect chosen for one recording — but it is the one answer that is
    true of every recording rather than of a particular one.
    """
    return clamp((0, 0, frame_width, frame_height), frame_width, frame_height,
                 minimum)

