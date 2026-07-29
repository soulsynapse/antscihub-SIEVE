"""The shared frame of the detection plots: axes, handles, and the gesture.

One base class carries everything the scalogram, density, and count plots have
in common, because what they have in common *is* the interaction contract the
graph mockups pinned (`docs/filter-tab-parity-plan.md` § 2, plot contracts):

**One drag gesture, two meanings.** A drag that starts within `GRAB_PX` of a
band handle moves the handle; any other drag scrubs the shared playhead. No
modes, no toolbars — which plot the user is over never changes what a drag is.
The scrub side speaks the timeline strip's three claims (`pressed` /
`scrubbed` / `committed`) so the player can serve the middle one coarse.

**Two event tiers per handle.** `band_changed` fires per mouse-move and drives
only cheap re-derivation; `band_committed` fires on release and is the hook
for anything expensive. The tiers are the coalescer discipline made visible at
the signal boundary — a consumer that treats them identically has opted out of
the budget, not been failed by it.

**Unbounded is a value, not a mode.** Dragging a handle past the plot edge
emits ``±inf`` (`DetectorState`'s own encoding), except where a subclass
clamps (`unbounded = False`, the frequency band — the bank has edges and a
band outside it is a lie the transform would silently correct). An *unset*
band (`clear_band`) is different again: handles park dimmed at the range
edges and the first drag arms them — that is how the count threshold goes
from disarmed to placed without a separate control.

**Plots own no detector state.** Setters in, drags out. The band drawn here is
a rendering of a value the tab owns; nothing in this module survives a
`set_band` it disagrees with. The one exception is mid-drag: the handle being
dragged follows the mouse rather than the last `set_band`, because a drag is
the user speaking and the tab echoing the value back per move would fight the
gesture on a slow recompute.

**Green is a status color.** The gate underpaint (spans floored to 1 px so a
single-frame detection survives any zoom) is the only green thing the base
paints, and it appears only when a gate is set — magnitude surfaces bring
their own sequential ramp, one per plot.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

FloatArray = NDArray[np.floating[Any]]

#: How close (px) a press must land to a handle's line to grab it rather than
#: scrub. The mockup settled 8; a drag starting 9 px away scrubs.
GRAB_PX = 8.0

#: How far (px) past the plot edge a handle drag must travel to mean
#: "unbounded" rather than "the edge value". Small, so the edge itself is
#: still reachable as a value.
_EDGE_PX = 4.0

_MARGIN_L = 48
_MARGIN_R = 66
_MARGIN_T = 24
_MARGIN_B = 8

# The plots' shared palette. Magnitude ramps are per-plot (one sequential ramp
# per surface); these are the structural colors every plot shares.
PANEL = QColor(31, 33, 38)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
#: Solo trace and in-band outlines. Data emphasis, not detection.
ACCENT = QColor(94, 200, 180)
#: Band handles, all three plots. One color for "this is a threshold".
BAND = QColor(240, 110, 100)
#: Detection. Never a data series: green is reserved for status.
DETECT = QColor(96, 210, 120)


def plot_font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    """The plots' one font, at `size` points."""
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


def ramp_lut(stops: tuple[tuple[int, int, int], ...]) -> NDArray[np.uint32]:
    """A 256-entry ARGB32 lookup table interpolating `stops` dark → light.

    The heatmap plots index normalized data through one of these; keeping the
    ramp a table rather than per-pixel arithmetic is what lets a (F, T) or
    (bins, T) image rebuild inside a drag tier.
    """
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, 256)
    channels: list[NDArray[np.float64]] = [
        np.interp(t, positions, [float(s[k]) for s in stops]) for k in range(3)
    ]
    r, g, b = (c.astype(np.uint32) for c in channels)
    return (np.uint32(255) << np.uint32(24)) | (r << np.uint32(16)) | (g << np.uint32(8)) | b


def argb_to_qimage(argb: NDArray[np.uint32]) -> QImage:
    """An owning QImage of an (H, W) ARGB32 array (`.copy()` — the array may go)."""
    height, width = argb.shape
    data = np.ascontiguousarray(argb, dtype=np.uint32)
    return QImage(data.tobytes(), width, height, width * 4, QImage.Format.Format_ARGB32).copy()


class BandPlot(QWidget):
    """The shared frame: title row, grid, playhead, gate underpaint, two handles.

    Subclasses override `_fwd` / `_inv` / `_range` for their value axis,
    `format_value` for the readouts, `unbounded` to clamp instead of emitting
    ``inf``, and `paint_content` for the surface itself.
    """

    #: Per mouse-move while a handle is held. The cheap tier.
    band_changed = Signal(float, float)
    #: On release of a handle. The expensive tier.
    band_committed = Signal(float, float)

    #: Mouse-down off the handles: a committed playhead position.
    pressed = Signal(int)
    #: A drag position: a guess the player may serve coarse.
    scrubbed = Signal(int)
    #: Mouse-up: land here exactly.
    committed = Signal(int)

    title = ""
    #: Whether dragging past the plot edge means ±inf. The frequency band
    #: turns this off: its handles clamp to the bank's edges.
    unbounded = True

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._start = 0
        self._count = 0
        # How much of the span holds data, and how much of *that* is final.
        # `None` means "all of it" — the whole-record case, which is every
        # caller that hands over a finished series and need not know these
        # exist. See `set_filled`.
        self._filled: int | None = None
        self._settled: int | None = None
        self._playhead = 0
        self._band: tuple[float, float] | None = None
        self._gate: NDArray[np.bool_] | None = None
        self._readout = ""
        # "lo" | "hi" | "scrub" | None. Which claim the current drag is making.
        self._drag: str | None = None
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # ---- what it is told -------------------------------------------------

    def set_span(self, start: int, count: int) -> None:
        """The source-frame window the x axis covers: [start, start + count)."""
        self._start = start
        self._count = max(count, 0)
        self.update()

    def set_filled(self, filled: int | None, settled: int | None = None) -> None:
        """How many frames of the span hold data, and how many of those are final.

        The x axis is the *working window* while a render fills it, not the
        frames collected so far — an axis that grew with the data would slide
        every curve leftward on each pass and make a filling graph read as a
        moving one. So the span is set once from the window and the data
        occupies a prefix of it, which `content_rect` is the geometry of.

        `settled` is the frontier past which values are provisional: inside the
        transform's cone of influence at the record's cut, still changing as
        frames arrive. Subclasses fade beyond it. `None` for either means the
        whole span, which is what a finished render sets and what a plot that
        has never heard of a partial pass keeps.
        """
        self._filled = None if filled is None else max(filled, 0)
        self._settled = None if settled is None else max(settled, 0)
        self.update()

    @property
    def filled_frames(self) -> int:
        """Frames of the span that hold data. The whole span unless told otherwise."""
        return self._count if self._filled is None else min(self._filled, self._count)

    @property
    def settled_frames(self) -> int:
        """Frames of the span whose values are final. Never more than `filled_frames`."""
        filled = self.filled_frames
        return filled if self._settled is None else min(self._settled, filled)

    def set_playhead(self, frame: int) -> None:
        """Move the playhead to source frame `frame`."""
        self._playhead = frame
        self.update()

    def set_band(self, lo: float, hi: float) -> None:
        """Show the band `(lo, hi)`; ``±inf`` paints as an unbounded handle.

        Ignored for the handle currently being dragged — mid-drag the mouse is
        the truth (see the module docstring).
        """
        if self._drag == "lo" and self._band is not None:
            self._band = (self._band[0], hi)
        elif self._drag == "hi" and self._band is not None:
            self._band = (lo, self._band[1])
        else:
            self._band = (lo, hi)
        self.update()

    def clear_band(self) -> None:
        """Unset the band: handles park dimmed at the edges, first drag arms."""
        if self._drag is None:
            self._band = None
            self.update()

    def set_gate(self, gate: NDArray[np.bool_] | None) -> None:
        """The detection gate to underpaint, aligned to the span, or None."""
        self._gate = gate
        self.update()

    def set_readout(self, text: str) -> None:
        """The top-right truth line (e.g. the snapped band the transform used)."""
        self._readout = text
        self.update()

    def readout_text(self) -> str:
        """What the top-right truth line says at paint time.

        The setter above is for lines a *caller* knows (the snapped band the
        transform used). A subclass whose truth line is derived from its own
        paint-time state — an axis it computes rather than is told — overrides
        this instead, so the line cannot fall out of step with the frame it
        describes.
        """
        return self._readout

    # ---- the value axis (subclass hooks) ----------------------------------

    def _fwd(self, value: float) -> float:
        """Data value → axis coordinate. Identity here; log in subclasses."""
        return value

    def _inv(self, t: float) -> float:
        """Axis coordinate → data value."""
        return t

    def _range(self) -> tuple[float, float]:
        """The value axis's (bottom, top) in data units."""
        return 0.0, 1.0

    def format_value(self, value: float) -> str:
        """A handle's readout. ``±inf`` reads as unbounded."""
        if math.isinf(value):
            return "inf" if value > 0 else "0"
        return f"{value:.3g}"

    # ---- geometry (exposed because the claims worth testing live here) ----

    def plot_rect(self) -> QRect:
        """Where data is painted; margins hold labels and handle readouts."""
        return self.rect().adjusted(_MARGIN_L, _MARGIN_T, -_MARGIN_R, -_MARGIN_B)

    def x_of(self, frame: int) -> float:
        """Source frame → x pixel across the span."""
        r = self.plot_rect()
        span = max(self._count - 1, 1)
        return r.left() + (frame - self._start) / span * r.width()

    def content_rect(self) -> QRect:
        """The part of `plot_rect` the data actually covers.

        `plot_rect` for a full record; a left-anchored prefix of it while one
        fills. The image plots draw into this rather than into the whole frame,
        because `drawImage` stretches to whatever rectangle it is handed and a
        half-filled window stretched across the full width would be a graph
        that lies about *when* — the one axis this tab cannot afford to be
        wrong about.
        """
        r = self.plot_rect()
        filled = self.filled_frames
        if self._count <= 0 or filled >= self._count:
            return r
        if filled <= 0:
            return QRect(r.left(), r.top(), 0, r.height())
        right = self.x_of(self._start + filled - 1)
        return QRect(r.left(), r.top(), max(round(right - r.left()), 1), r.height())

    def frame_of(self, x: float) -> int:
        """x pixel → source frame, clamped to the span."""
        r = self.plot_rect()
        t = (x - r.left()) / max(r.width(), 1)
        offset = round(t * max(self._count - 1, 0))
        return self._start + min(max(offset, 0), max(self._count - 1, 0))

    def y_of(self, value: float) -> float:
        """Data value → y pixel through the axis transform, clamped to range."""
        lo, hi = self._range()
        r = self.plot_rect()
        value = min(max(value, lo), hi)
        t = (self._fwd(value) - self._fwd(lo)) / max(self._fwd(hi) - self._fwd(lo), 1e-12)
        return r.bottom() - t * r.height()

    def value_of(self, y: float) -> float:
        """y pixel → data value, clamped to the range."""
        lo, hi = self._range()
        r = self.plot_rect()
        t = (r.bottom() - y) / max(r.height(), 1)
        t = min(max(t, 0.0), 1.0)
        return self._inv(self._fwd(lo) + t * (self._fwd(hi) - self._fwd(lo)))

    def handle_y(self, which: str) -> float:
        """Where the `which` ("lo"/"hi") handle line sits right now."""
        lo, hi = self._range()
        if self._band is None:
            value = lo if which == "lo" else hi
        else:
            value = self._band[0] if which == "lo" else self._band[1]
        return self.y_of(min(max(value, lo), hi))

    def gate_rects(self) -> list[QRectF]:
        """The gate spans as paint rectangles, each floored to 1 px wide.

        Exposed because "a single-frame detection survives any zoom" is a
        claim about these rectangles, and a painted pixel is not something a
        test can ask about.
        """
        if self._gate is None or self._count <= 0:
            return []
        r = self.plot_rect()
        edges = np.flatnonzero(np.diff(np.r_[0, self._gate.view(np.int8), 0]))
        rects: list[QRectF] = []
        for lo_idx, hi_idx in zip(edges[::2], edges[1::2], strict=True):
            x0 = self.x_of(self._start + int(lo_idx))
            x1 = self.x_of(self._start + int(hi_idx))
            rects.append(QRectF(x0, r.top(), max(x1 - x0, 1.0), r.height()))
        return rects

    # ---- the gesture -------------------------------------------------------

    def _grabbable(self, pos: QPointF) -> str | None:
        """The handle a press at `pos` grabs, or None for a scrub.

        The grab zone extends into the right margin so the readout dot is a
        target too; vertically it is `GRAB_PX` exactly — at 9 px the press is
        a scrub, and that boundary is a tested claim.
        """
        r = self.plot_rect()
        zone = QRectF(r).adjusted(0.0, -GRAB_PX, float(_MARGIN_R), GRAB_PX)
        if not zone.contains(pos):
            return None
        near = min(("lo", "hi"), key=lambda w: abs(self.handle_y(w) - pos.y()))
        if abs(self.handle_y(near) - pos.y()) <= GRAB_PX:
            return near
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Grab a handle within `GRAB_PX`; otherwise this press is a playhead."""
        if self._count <= 0 or event.button() is not Qt.MouseButton.LeftButton:
            return
        handle = self._grabbable(event.position())
        if handle is not None:
            self._drag = handle
            return
        self._drag = "scrub"
        self.pressed.emit(self.frame_of(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Follow the drag: a handle emits the cheap tier, a scrub a guess."""
        if self._drag in ("lo", "hi"):
            self._drag_handle(event.position().y())
        elif self._drag == "scrub":
            self.scrubbed.emit(self.frame_of(event.position().x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Commit whichever claim the drag was making."""
        if event.button() is not Qt.MouseButton.LeftButton:
            return
        if self._drag in ("lo", "hi") and self._band is not None:
            self.band_committed.emit(self._band[0], self._band[1])
        elif self._drag == "scrub":
            self.committed.emit(self.frame_of(event.position().x()))
        self._drag = None

    def _drag_handle(self, y: float) -> None:
        """Move the held handle to `y`, past-the-edge meaning unbounded.

        Crossing the other handle swaps which one is held, so a drag through
        never inverts the band — the same rule the mockup settled by feel.
        """
        r = self.plot_rect()
        lo, hi = self._band if self._band is not None else (-math.inf, math.inf)
        if self.unbounded and y < r.top() - _EDGE_PX:
            value = math.inf
        elif self.unbounded and y > r.bottom() + _EDGE_PX:
            value = -math.inf
        else:
            value = self.value_of(y)
        if self._drag == "lo":
            lo = value
            if lo > hi:
                lo, hi = hi, lo
                self._drag = "hi"
        else:
            hi = value
            if hi < lo:
                lo, hi = hi, lo
                self._drag = "lo"
        self._band = (lo, hi)
        self.band_changed.emit(lo, hi)
        self.update()

    # ---- painting ----------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Frame, gate underpaint, content, playhead, handles — back to front."""
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), PANEL)
        r = self.plot_rect()

        painter.setPen(DIM)
        painter.setFont(plot_font(8, bold=True, spaced=True))
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, self.title.upper())
        readout = self.readout_text()
        if readout:
            painter.drawText(
                QRect(10, 4, self.width() - 20, 14),
                int(Qt.AlignmentFlag.AlignRight),
                readout,
            )

        grid = QColor(LINE)
        grid.setAlpha(90)
        painter.setPen(QPen(grid, 1.0))
        for k in range(1, 4):
            y = r.top() + k * r.height() / 4
            painter.drawLine(QPointF(float(r.left()), y), QPointF(float(r.right()), y))

        painter.save()
        painter.setClipRect(r)
        fill = QColor(DETECT)
        fill.setAlpha(52)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        for span in self.gate_rects():
            painter.drawRect(span)
        self.paint_content(painter, r)
        painter.restore()

        if self._count > 0:
            x = self.x_of(self._playhead)
            head = QColor(TEXT)
            head.setAlpha(130)
            painter.setPen(QPen(head, 1.0))
            painter.drawLine(QPointF(x, float(r.top())), QPointF(x, float(r.bottom())))

        self._paint_handles(painter, r)
        painter.end()

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        """The surface itself. Subclasses override; the base paints nothing."""

    def _paint_handles(self, painter: QPainter, r: QRect) -> None:
        """Both handle lines with their right-margin readouts.

        An unset band paints dimmed at the edges with no value — present
        enough to grab (that is how arming works), quiet enough to read as
        not yet placed.
        """
        band = self._band
        for which in ("lo", "hi"):
            y = self.handle_y(which)
            color = QColor(BAND)
            value = None if band is None else (band[0] if which == "lo" else band[1])
            if value is None or math.isinf(value):
                color.setAlpha(110)
            painter.setPen(QPen(color, 1.0))
            painter.drawLine(QPointF(float(r.left()), y), QPointF(r.right() + 22.0, y))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(r.right() + 22.0, y), 3.2, 3.2)
            painter.setPen(QPen(color, 1.0))
            painter.setFont(plot_font(8))
            painter.drawText(
                QRectF(r.right() + 28.0, y - 8.0, _MARGIN_R - 30.0, 16.0),
                int(Qt.AlignmentFlag.AlignVCenter),
                "—" if value is None else self.format_value(value),
            )
