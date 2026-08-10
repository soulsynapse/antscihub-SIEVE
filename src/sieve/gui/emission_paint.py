"""What a node's output looks like, dispatched on what one of its values *is*.

`adr/an-outputs-kind-is-the-picture-it-makes.md` rules that the picture follows
`ElementKind` and nothing else — not the tool, which is why nothing here names
one. A table with an entry per kind is that ruling as code: `PIXEL` is a frame
and paints as one, `BLOCK` is a grid and paints as cells over the footage it was
measured from, and `FRAME` has no entry at all. That absence is its answer: one
value describing a whole frame is not a picture, and the viewport's fallback
already exists for a node that has none (`canvas.mark_source`). An undeclarable
node — `node_element` returning `None` — is the same answer arrived at
differently: nothing can say what one of its values is a value of, so nothing
here can say what it looks like.

This is separate from `canvas.py` because that widget paints one image and
decides nothing, and separate from `kind_editors.py` because those are widgets
that emit an intent where an overlay emits none. The canvas is *handed* the kind
and never looks one up, which is what keeps the registry out of a widget.

**The two entries disagree about their value range, and the disagreement is the
point.** `image_of` stretches each frame between its own extremes: a picture has
no axis, and a fixed range blacks every tool whose units are not already 0..1 —
what it costs is that brightness is not comparable across frames, which is why
nothing it produces is offered as a measurement. A cell has the opposite
requirement. The field exists to say which block is loud, and a colour that
re-normalized every frame would say only which block is loudest *now*; so a
`BLOCK` field takes a range fixed over the working window, which is the same
question `graph_panel.value_range` answers for the trace and is read from there
rather than answered twice.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QImage, QPainter

from sieve.core.tool_base import ElementKind

#: The heat ramp's stops, cold to hot — v1's colormap over the footage, which is
#: what the eye was taught to read a block field with. Cold-to-hot rather than a
#: single-hue ramp because this layer sits over footage: a grey field would be
#: indistinguishable from the frame under it wherever the frame is grey.
HEAT_STOPS: tuple[tuple[int, int, int], ...] = (
    (48, 18, 59),
    (69, 91, 205),
    (62, 155, 254),
    (24, 214, 203),
    (72, 248, 130),
    (164, 252, 60),
    (226, 220, 56),
    (254, 163, 49),
    (239, 89, 17),
    (194, 36, 3),
    (122, 4, 3),
)


def _ramp_lut(stops: tuple[tuple[int, int, int], ...]) -> NDArray[np.uint32]:
    """`stops` interpolated into a 256-entry opaque ARGB32 table."""
    positions = np.linspace(0.0, 1.0, len(stops))
    at = np.linspace(0.0, 1.0, 256)
    red, green, blue = (
        np.interp(at, positions, [float(stop[channel]) for stop in stops]).astype(np.uint32)
        for channel in range(3)
    )
    return (
        (np.uint32(255) << np.uint32(24)) | (red << np.uint32(16)) | (green << np.uint32(8)) | blue
    )


#: The ramp as a table, built once at import. The field is the unconditional
#: layer — every cell is coloured on every repaint — so its cost is the block
#: count times whatever one cell costs, and v2 measured per-cell colour
#: arithmetic at the reference block count as a repaint slower than the frame it
#: draws over.
_HEAT_LUT = _ramp_lut(HEAT_STOPS)

#: The smallest range a field is coloured against. A window whose values do not
#: vary has no spread to divide by, and a paint event is the wrong place to
#: raise: the guard costs a comparison and the alternative is a stack trace over
#: a viewport. Every value then lands on the ramp's cold end, which is what a
#: field with nothing to distinguish should look like.
_MIN_SPREAD = 1e-12


def image_of(values: NDArray[np.float32]) -> QImage | None:
    """`values` as a greyscale image, or `None` if there is no picture in them.

    `None` for anything that is not a two-dimensional array with a finite value
    in it: a caller showing a node's output cannot know in advance that the node
    has one, and an image invented for a frame that has none would be a viewport
    asserting something about the graph.

    The buffer is copied because `QImage` does not own the one it is
    constructed over, and the array it would otherwise point into is local.
    """
    array = np.asarray(values, np.float32)
    if array.ndim != 2 or array.size == 0:
        return None
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return None
    low, high = float(finite.min()), float(finite.max())
    spread = high - low
    # A constant frame has no spread, so dividing by it is a division by zero.
    # On a constant frame carrying no positive infinity the guard is not visible
    # in the pixels — `nan_to_num` below maps the 0/0 it refuses onto the same
    # zero it writes — so what it buys is the absence of the invalid operation,
    # which is what the case over it asserts. One `inf` among the constants is
    # the exception the finding leaves open: there the guard blacks the frame
    # and the division whites that cell
    # (`findings/2026.08.08-the-constant-frame-guard-is-output-equivalent-to-the-division-it-refuses.md`).
    scaled = np.zeros_like(array) if spread <= 0.0 else (array - low) / spread
    # Every finite value is already inside 0..1 by construction — `low` and
    # `high` are this frame's own — so the only thing left to place is the
    # non-finite one, which `image_of`'s caller has no better answer for either.
    grey = np.ascontiguousarray(
        np.nan_to_num(scaled, nan=0.0, posinf=1.0, neginf=0.0) * 255.0
    ).astype(np.uint8)
    height, width = grey.shape
    return QImage(grey.data, width, height, width, QImage.Format.Format_Grayscale8).copy()


def grid_edges(rect: QRectF, ny: int, nx: int) -> tuple[list[int], list[int]]:
    """The integer pixel columns and rows an `(ny, nx)` grid over `rect` falls on.

    `(xs, ys)`, each one longer than its count: cell `(row, col)` owns the pixels
    `xs[col] .. xs[col + 1] - 1` across and `ys[row] .. ys[row + 1] - 1` down.

    Rounding the *line* rather than each cell's own origin and extent is what
    closes the seam: neighbouring cells cannot round apart when they read the
    same number, whereas `left + i * w` and `left + (i - 1) * w + w` are the same
    real and need not be the same float, and one ULP either side of a half-pixel
    is a row of unblended footage across the field.

    Exposed rather than private because a hit test over the field has to read the
    same edges the colours landed on, or the cell under the pointer is not the
    cell the pointer is over.
    """
    xs = [round(rect.left() + index * rect.width() / nx) for index in range(nx + 1)]
    ys = [round(rect.top() + index * rect.height() / ny) for index in range(ny + 1)]
    return xs, ys


def _cell_span(edges: list[int], low: int, high: int, count: int) -> tuple[int, int]:
    """The inclusive range of cells whose pixels intersect `low..high`."""
    first = min(max(bisect_right(edges, low) - 1, 0), count - 1)
    last = min(max(bisect_right(edges, high) - 1, 0), count - 1)
    return first, last


@dataclass(frozen=True, slots=True)
class BlockField:
    """An `(ny, nx)` grid of values, and the range they are coloured against.

    Held rather than turned into an image when it arrives, because the pixels a
    cell covers are a function of where the canvas is painting *now* — the
    magnifier moves them and a resize moves them — while the values are a
    function of the render.
    """

    values: NDArray[np.float32]
    #: The value the ramp's cold end means, and the value its hot end means.
    #: `graph_panel.value_range`'s answer, which is fixed over the working
    #: window rather than over this frame.
    low: float
    high: float

    def draw(self, painter: QPainter, view: QRectF, box: QRectF) -> None:
        """Paint the cells over `view`, building only what `box` can show.

        One ARGB image rather than a filled rect per cell, and its pixels are the
        ones the per-cell loop would have drawn: cell colours expand by
        `np.repeat` over the *same* `grid_edges` widths a hit test reads, so
        colour and cell boundary cannot land on different pixels. The
        cheaper-looking alternative — a cell-resolution image scaled up by Qt —
        re-rounds every edge under a rule of Qt's own and drifts a pixel wherever
        that disagrees, which on a field is a seam of bare footage.

        Magnified, the grid runs far outside the widget and the letterbox the
        caller paints through throws that away anyway, so the array is bounded by
        the box rather than by the zoom.
        """
        ny, nx = self.values.shape
        xs, ys = grid_edges(view, ny, nx)
        bounds = box.toAlignedRect()
        col0, col1 = _cell_span(xs, bounds.left(), bounds.right(), nx)
        row0, row1 = _cell_span(ys, bounds.top(), bounds.bottom(), ny)
        widths = np.diff(np.asarray(xs[col0 : col1 + 2], np.intp))
        heights = np.diff(np.asarray(ys[row0 : row1 + 2], np.intp))
        if widths.sum() <= 0 or heights.sum() <= 0:
            return
        # A non-finite value would index the table out of bounds, which is a
        # crash inside a paint event rather than a wrong colour. It goes to the
        # cold end, where a block that measured nothing belongs.
        shown = np.nan_to_num(
            self.values[row0 : row1 + 1, col0 : col1 + 1],
            nan=self.low,
            posinf=self.high,
            neginf=self.low,
        )
        level = np.clip((shown - self.low) / max(self.high - self.low, _MIN_SPREAD), 0.0, 1.0)
        cells = _HEAT_LUT[np.rint(level * 255.0).astype(np.intp)]
        pixels = np.ascontiguousarray(np.repeat(np.repeat(cells, heights, 0), widths, 1))
        height, width = pixels.shape
        # `QImage` does not own the buffer it is constructed over and `pixels` is
        # local, so the image is copied before it outlives this call.
        painter.drawImage(
            QPoint(xs[col0], ys[row0]),
            QImage(pixels.tobytes(), width, height, width * 4, QImage.Format.Format_ARGB32).copy(),
        )


def _pixel_picture(values: NDArray[np.float32], span: tuple[float, float]) -> QImage | None:
    """`PIXEL`'s entry: the frame's own extremes, which is what `span` is not."""
    del span
    return image_of(values)


def _block_picture(values: NDArray[np.float32], span: tuple[float, float]) -> BlockField | None:
    """`BLOCK`'s entry: a field of cells, coloured against the window's range."""
    array = np.asarray(values, np.float32)
    if array.ndim != 2 or array.size == 0:
        return None
    return BlockField(array, span[0], span[1])


_PICTURES: Mapping[ElementKind, Callable[[NDArray[np.float32], tuple[float, float]], Any]] = {
    ElementKind.PIXEL: _pixel_picture,
    ElementKind.BLOCK: _block_picture,
}


def picture_of(
    kind: ElementKind | None, values: NDArray[np.float32], span: tuple[float, float]
) -> QImage | BlockField | None:
    """What `values` look like for a node whose elements are `kind`.

    `None` where the kind has no entry, and where the entry it has finds no
    picture in the values — one refusal rather than two, because the caller's
    move is the same for both: show the frame the pipeline was run over and say
    so (`canvas.mark_source`).
    """
    make = None if kind is None else _PICTURES.get(kind)
    return None if make is None else make(values, span)
