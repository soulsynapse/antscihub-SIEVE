"""One editor per composite kind, on the surface the value is about.

The other half of `param_form.py`. A scalar is typed into a control the panel
holds; a region and a span are gestures on something already on screen — the
viewport for a rectangle in a frame, the band for a stretch of frames — so the
editor is an overlay on that surface rather than a row in the form. What it
produces is only a param value: a drawn box and a typed number are one
`SetParam` at one address, which is what `adr/gui-knows-kinds-not-tools.md`
binds an overlay to a param field for, and what `session/intents.py` refuses a
`DrawRegion` kind in order to keep.

Per kind and never per tool, which is the generator's asymmetry one surface out:
`_EDITORS` is the whole of this module's tool knowledge, and a tool arriving
with a region gets the viewport without a line here. Unlike the generator's map
this one is partial by design — a kind with no entry is typed into the panel,
which is the ordinary case and not a defect.

**`BAND` is one entry over three pictures**, which is what makes it the kind that
tested whether "per kind" survives contact. A band names the `DisplaySurface` its
handles are grabbed on and `surface_panel.py` draws all three, so what varies
between `detect`'s three bands is the axis the same gesture is read on rather
than the gesture — one editor, handed a different panel per parameter. The
generator's rule holds unchanged: nothing here learns that the tool is `detect`,
only that a parameter is a band and which kind of picture the spec says it cuts.

The third of the three is refused, and by the panel rather than here
(`surface_panel.takes_handles`): a scalogram's rows are the Morlet bank's and
`freq_band` is in Hz, so a cut on it has no value to commit. That is
`RegionEditor`'s refusal exactly — an editor is offered only where the gesture's
coordinates are the ones the value is denominated in — and it is why `BAND`
comes off `tool_base.STEREOTYPES_WITHOUT_EDITOR` with two of three bands
editable: the list is about a kind having an editor at all, and the per-surface
refusal is a placement, not a missing one
(`adr/an-unconsumed-member-is-named-in-a-list.md`).

**A drag paints from a draft and announces itself once, on release.** The
strip's two-tier rule (`timeline/bar.py`), and the reason is sharper for a
parameter than for the working window: every value passed through on the way is
a re-plan, a new cache key, a render, and an entry on the undo stack — for a
region the user is still choosing.

**An overlay is transparent to gestures it does not own.** The band already
scrubs and carries the working window; an editor that swallowed every press
would take those away for as long as a span node is on screen. So a press
outside this editor's handles is handed to the host, at the same coordinates,
because overlay and host are the same rectangle by construction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any, NamedTuple

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from sieve.core.pipeline_model import SourceSpan
from sieve.core.tool_base import DisplaySurface, ParamStereotype, ToolSpec
from sieve.core.types import ROI
from sieve.gui.canvas import VideoCanvas
from sieve.gui.surface_panel import SurfacePanel
from sieve.gui.timeline.bar import EDGE_GRAB, Grab, TimelineStrip
from sieve.gui.timeline.window import ended_at, started_at
from sieve.session.intents import SetParam, issue
from sieve.session.session import Session

#: Amber, where the working window is blue. A span parameter and the working
#: window are painted on the same strip and mean different things — what a run
#: keeps, and what the transport may reach — so the one thing they must never
#: be is the same colour.
_MARK = QColor(255, 190, 90)
_FILL = QColor(255, 190, 90, 70)


class _Editor(QWidget):
    """An overlay covering the surface a composite kind's gesture is made on.

    A child of the host rather than a widget in a layout: the value is about
    what the host is showing, so the two have to be the same rectangle, and
    following the host's own size is the only way to stay that way through a
    resize the splitter decides.
    """

    #: The document has just been written to. `ParamForm.edited`, on the other
    #: half of the same surface and for the same listener: a drawn box and a
    #: typed number are one edit, so they say so the same way.
    edited = Signal()

    def __init__(
        self,
        host: QWidget,
        session: Session,
        node_id: str,
        param: str,
        *,
        replicate_id: str | None = None,
    ) -> None:
        super().__init__(host)
        self._host = host
        self._session = session
        self._node_id = node_id
        self._param = param
        # The tail of the address, for `ParamForm`'s reason and to the same
        # effect: the box drawn on the canvas is the selected region's own, and
        # a drag with no region selected moves the baseline. Keyword-only
        # because it is an id threaded past a value and an extent, and a
        # mis-slotted one would write a real edit at a wrong address.
        self._replicate_id = replicate_id
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Without this the overlay hears a move only while a button is down,
        # which is every move a drag makes but none of the ones the host needs
        # to answer for.
        self.setMouseTracking(True)
        self.setGeometry(self._host.rect())
        self._host.installEventFilter(self)
        self.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Follow the host's size. Nothing else lays this widget out.

        The type is tested before the sender, so nothing this overlay holds is
        read for the events it has no interest in — which is all of them but
        one, and includes the ones a host sends while it is taking its children
        down with it.
        """
        if event.type() == QEvent.Type.Resize and watched is self._host:
            self.setGeometry(self._host.rect())
        return False

    def _commit(self, value: Any) -> None:
        """The gesture's whole output: one parameter, through the command layer.

        Announced only if it landed. A gesture that ends where the value already
        was is dropped by the writer (`session/session.py`), and `edited` is what
        the window re-plans and re-renders from — emitting it regardless would
        put the graph's stale mark up for a document that has not moved.
        """
        if issue(
            self._session,
            SetParam(
                node_id=self._node_id,
                param=self._param,
                value=value,
                replicate_id=self._replicate_id,
            ),
        ):
            self.edited.emit()


class RegionEditor(_Editor):
    """A rectangle dragged on the viewport, in the pixels of the space it names.

    **Which space that is, is declared rather than read off the screen** (07.11).
    `crop.py` says a region indexes the frame its own node is handed; the canvas
    is fed a display proxy of the source, resampled whenever the footage is wider
    than `transport/decode_worker.PROXY_WIDTH`. So the image on screen and the
    space the value is denominated in are two different rectangles, and on 4K
    footage they differ by a factor of three — silently, and only on large
    footage, which is the worst shape a unit error can take. `extent` is the one
    the value is in, and everything here scales through it.

    Placing the editor is therefore also the decision *not* to offer it: the
    extent of a node's input is a fact about what its upstream produces, so
    `bind_editors` is handed one only where the caller knows it, and a node
    reading a rescaled or cropped frame gets no editor and keeps the form's
    read-only restatement of the value. Better a parameter the user must type
    than a box that draws in the wrong units.

    Clamped to the extent and not to the widget. The canvas centres the frame and
    never enlarges it, so there is always a margin, and clamping to the widget
    would scale that overshoot into coordinates the frame does not have.

    Outline only, no fill: the region is drawn over the footage it is being
    judged against, and a wash over it would hide the thing the user is aiming.
    """

    def __init__(
        self,
        host: VideoCanvas,
        session: Session,
        node_id: str,
        param: str,
        value: Mapping[str, int] | None,
        extent: tuple[int, int],
        *,
        replicate_id: str | None = None,
    ) -> None:
        """Edit `param` of `node_id`, in the pixels of an `extent`-sized frame."""
        super().__init__(host, session, node_id, param, replicate_id=replicate_id)
        self._canvas = host
        self._extent = extent
        self._region = None if value is None else ROI(**dict(value))
        self._anchor: QPointF | None = None
        self._draft: QRectF | None = None
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ---- geometry --------------------------------------------------------

    def region_rect(self) -> QRectF:
        """Where the committed region sits on screen, empty when there is none."""
        box = self._canvas.frame_rect()
        scale = self._scale()
        region = self._region
        if region is None or scale <= 0.0:
            return QRectF()
        return QRectF(
            box.left() + region.x * scale,
            box.top() + region.y * scale,
            region.width * scale,
            region.height * scale,
        )

    def shown_rect(self) -> QRectF:
        """The rectangle on screen: the draft while a drag is held, else the value's.

        Everything that reads the rectangle goes through here, for the reason
        the strip's `shown_window` exists — a drag cannot be visible in the paint
        and absent from what a test can ask about.
        """
        return self._draft if self._draft is not None else self.region_rect()

    def _scale(self) -> float:
        """Screen pixels per *extent* pixel, zero when there is no frame.

        The painted rectangle over the extent, not over the image inside it: the
        two agree only when the canvas is showing the space at its own
        resolution, and the whole point of the extent is that it need not be.
        """
        box = self._canvas.frame_rect()
        width = self._extent[0]
        if box.isEmpty() or width <= 0:
            return 0.0
        return box.width() / width

    def _image_point(self, point: QPointF) -> QPointF | None:
        """`point` in the extent's pixels, or None when nothing is shown."""
        scale = self._scale()
        if scale <= 0.0:
            return None
        box = self._canvas.frame_rect()
        return QPointF(
            min(max((point.x() - box.left()) / scale, 0.0), float(self._extent[0])),
            min(max((point.y() - box.top()) / scale, 0.0), float(self._extent[1])),
        )

    def _drawn(self, start: QPointF, end: QPointF) -> ROI | None:
        """The region these two corners enclose, or None if they enclose nothing.

        A click is how a half-started rectangle is abandoned, and `ROI` refuses a
        zero extent outright — so the alternative to ignoring it is a refusal the
        user gets for having clicked.
        """
        first, last = self._image_point(start), self._image_point(end)
        if first is None or last is None:
            return None
        corners = (round(first.x()), round(first.y()), round(last.x()), round(last.y()))
        if corners[0] == corners[2] or corners[1] == corners[3]:
            return None
        return ROI.from_corners(*corners)

    # ---- the gesture -----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is not Qt.MouseButton.LeftButton or self._scale() <= 0.0:
            return
        self._anchor = event.position()
        self._draft = QRectF(self._anchor, self._anchor)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._anchor is None:
            return
        self._draft = QRectF(self._anchor, event.position()).normalized()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._anchor is None or event.button() is not Qt.MouseButton.LeftButton:
            return
        start, self._anchor, self._draft = self._anchor, None, None
        region = self._drawn(start, event.position())
        self.update()
        if region is None:
            return
        # Held so the box stays on screen after the drag that drew it. Not a
        # read of the document — a new value still arrives by rebuilding this
        # editor, which is the rule the form runs on.
        self._region = region
        self._commit(asdict(region))

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        box = self.shown_rect()
        if box.isEmpty():
            return
        painter = QPainter(self)
        painter.setPen(QPen(_MARK, 2.0 if self._draft is not None else 1.0))
        painter.drawRect(box)
        painter.end()


class SpanEditor(_Editor):
    """Two handles on the band, dragged to the frames a span keeps.

    Two handles and nothing between them. Every press that is not one of them is
    handed to the strip, whose own reading of that pixel — a seek, or the
    working window's body — is not this editor's to second-guess: an editor
    owning the middle would take both away for as long as a span node is on
    screen, and a span has no body gesture of its own. Moving one whole is a
    reinterpretation nobody asked for, where the working window's is the
    "keep the ten seconds, move them" `timeline/window.py` argues for.

    The edge rules are that module's, and are not restated here. A handle moves
    one edge and pins the other, and stops at a floor rather than going dead
    under the cursor: a span is the same shape as the working window and its
    edges have to behave the same way under a hand, even though the two mean
    different things.
    """

    def __init__(
        self,
        host: TimelineStrip,
        session: Session,
        node_id: str,
        param: str,
        value: tuple[int, int] | list[int] | None,
        *,
        replicate_id: str | None = None,
    ) -> None:
        super().__init__(host, session, node_id, param, replicate_id=replicate_id)
        self._strip = host
        self._span = None if value is None else SourceSpan(start=value[0], end=value[1])
        self._draft: SourceSpan | None = None
        self._grab: Grab | None = None

    # ---- geometry --------------------------------------------------------

    @property
    def shown_span(self) -> SourceSpan | None:
        """The span on screen: the draft while a handle is held, else the value's."""
        return self._draft if self._draft is not None else self._span

    def band_rect(self) -> QRectF:
        """Where the span is painted, empty when there is none."""
        geometry = self._strip.geometry_now()
        span = self.shown_span
        if span is None or geometry.is_empty:
            return QRectF()
        left, right = geometry.span(span.start, span.end)
        return QRectF(left, 0.0, right - left, float(self.height()))

    def grab_at(self, position: QPointF) -> Grab | None:
        """Which handle a press takes hold of, or None for a gesture that is the host's."""
        band = self.band_rect()
        if band.isEmpty():
            return None
        x = position.x()
        if abs(x - band.left()) <= EDGE_GRAB:
            return Grab.START
        if abs(x - band.right()) <= EDGE_GRAB:
            return Grab.END
        return None

    def _dragged_to(self, span: SourceSpan, x: float) -> SourceSpan:
        """Where `span` has been dragged to. Never written; only painted, until release."""
        geometry = self._strip.geometry_now()
        frame = geometry.frame_at(x)
        floor = self._strip.floor_frames
        if self._grab is Grab.START:
            return started_at(span, frame, geometry.frame_count, floor)
        return ended_at(span, frame, geometry.frame_count, floor)

    # ---- the gesture -----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Classify, and hand the press on if it is not a handle's.

        Classified once and held for the gesture, for the strip's reason: the
        span it is testing against moves under a drag that re-classified as it
        travelled.
        """
        grab = None
        if event.button() is Qt.MouseButton.LeftButton:
            grab = self.grab_at(event.position())
        if grab is None:
            self._strip.mousePressEvent(event)
            return
        # Not None: a handle is an edge of the painted band, and there is no
        # band to grab an edge of unless there is a span.
        self._grab, self._draft = grab, self.shown_span
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # The draft exists only between a press on a handle and its release,
        # so its absence is what says this gesture is the strip's.
        if self._draft is None:
            self._strip.mouseMoveEvent(event)
            return
        self._draft = self._dragged_to(self._draft, event.position().x())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._draft is None:
            self._strip.mouseReleaseEvent(event)
            return
        span = self._dragged_to(self._draft, event.position().x())
        self._grab, self._draft, self._span = None, None, span
        self.update()
        self._commit((span.start, span.end))

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        band = self.band_rect()
        if band.isEmpty():
            return
        painter = QPainter(self)
        painter.fillRect(band, _FILL)
        painter.setPen(QPen(_MARK, 2.0 if self._grab is not None else 1.0))
        painter.drawRect(band.adjusted(0.5, 0.5, -0.5, -0.5))
        painter.end()


class BandEditor(_Editor):
    """Two horizontal cuts on the picture the band is declared against.

    `SpanEditor` turned ninety degrees, and deliberately the same shape: two
    handles, nothing between them, every other press handed to the host. What is
    not the same is where the numbers come from — a span is in frames and the
    strip owns that axis, while a band is in whatever the surface's vertical axis
    is denominated in and `SurfacePanel.value_at` is the only thing that knows.
    So this class holds the gesture and none of the arithmetic.

    **An unplaced band takes no gesture.** `count_frac` is `None` when the
    detector is disarmed, and that is "nothing is claimed" rather than a pair at
    the edges of the axis — so there is no band to grab an edge of, and arming it
    is the form's. A drag that invented the first pair would arm a detector by
    brushing a picture.

    **An infinite edge paints at the edge of the axis and drags to a number.**
    `value_band` opens at ±inf, which is a real value meaning "no cut on this
    side"; the handle is where the axis ends, and moving it is the user asking
    for a finite bound. Only the edge that moves is written, so pulling the top
    down does not quietly close the bottom.
    """

    def __init__(
        self,
        host: SurfacePanel,
        session: Session,
        node_id: str,
        param: str,
        value: tuple[float, float] | list[float] | None,
        *,
        replicate_id: str | None = None,
    ) -> None:
        super().__init__(host, session, node_id, param, replicate_id=replicate_id)
        self._panel = host
        self._band = None if value is None else (float(value[0]), float(value[1]))
        self._draft: tuple[float, float] | None = None
        self._grab: Grab | None = None
        self.setCursor(Qt.CursorShape.SplitVCursor)

    # ---- geometry --------------------------------------------------------

    @property
    def shown_band(self) -> tuple[float, float] | None:
        """The pair on screen: the draft while a handle is held, else the value's."""
        return self._draft if self._draft is not None else self._band

    def cut_positions(self) -> tuple[float, float] | None:
        """Where the two cuts are painted, or None when the band is unplaced.

        Clamped to the widget, which is what places an infinite edge: `y_of` of
        an infinity is an infinity, and a line drawn there is a line nothing can
        grab.
        """
        band = self.shown_band
        if band is None:
            return None
        height = float(self.height())
        return tuple(  # type: ignore[return-value]
            min(max(self._panel.y_of(edge), 0.0), height) for edge in band
        )

    def grab_at(self, position: QPointF) -> Grab | None:
        """Which cut a press takes hold of, or None for a gesture that is not ours.

        `Grab.START` is the *low* edge, which is the bottom of the plot — the
        strip's naming, kept because the pair is ordered the same way and a second
        vocabulary for "the first of two handles" would be one too many.
        """
        cuts = self.cut_positions()
        if cuts is None:
            return None
        y = position.y()
        low, high = cuts
        if abs(y - low) <= EDGE_GRAB and abs(y - low) <= abs(y - high):
            return Grab.START
        if abs(y - high) <= EDGE_GRAB:
            return Grab.END
        return None

    def _dragged_to(self, band: tuple[float, float], y: float) -> tuple[float, float]:
        """Where `band` has been dragged to. Never written; only painted, until release.

        The edge that is not moving is kept exactly, infinity included, and the
        one that is stops at the other rather than crossing it: a band whose
        edges swapped would be an ordered pair the document refuses, reported to
        the user as a validation error for a drag they made in one direction.
        """
        value = self._panel.value_at(y)
        low, high = band
        if self._grab is Grab.START:
            return (min(value, high), high)
        return (low, max(value, low))

    # ---- the gesture -----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        grab = None
        if event.button() is Qt.MouseButton.LeftButton:
            grab = self.grab_at(event.position())
        if grab is None:
            event.ignore()
            return
        self._grab, self._draft = grab, self.shown_band
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._draft is None:
            event.ignore()
            return
        self._draft = self._dragged_to(self._draft, event.position().y())
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._draft is None:
            event.ignore()
            return
        band = self._dragged_to(self._draft, event.position().y())
        self._grab, self._draft, self._band = None, None, band
        self.update()
        self._commit(list(band))

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        cuts = self.cut_positions()
        if cuts is None:
            return
        low, high = cuts
        painter = QPainter(self)
        painter.fillRect(QRectF(0.0, high, float(self.width()), low - high), _FILL)
        painter.setPen(QPen(_MARK, 2.0 if self._grab is not None else 1.0))
        for y in cuts:
            painter.drawLine(QPointF(0.0, y), QPointF(float(self.width()), y))
        painter.end()


class _Surfaces(NamedTuple):
    """What an editor may be hung on, and what its value would be denominated in."""

    canvas: VideoCanvas
    timeline: TimelineStrip
    #: The size of the frame this node is handed, or None when the caller cannot
    #: say. `RegionEditor` explains why that is a refusal and not a default.
    region_extent: tuple[int, int] | None
    #: The panel drawing each display surface the node declares. Empty where the
    #: caller has drawn none, which is a band with no picture to grab handles on
    #: and therefore no editor — the same shape `region_extent` is a refusal in.
    bands: Mapping[DisplaySurface, SurfacePanel] = {}


def _on_the_canvas(
    surfaces: _Surfaces, spec: ToolSpec, *bound: Any, replicate_id: str | None = None
) -> _Editor | None:
    del spec
    if surfaces.region_extent is None:
        return None
    return RegionEditor(surfaces.canvas, *bound, surfaces.region_extent, replicate_id=replicate_id)


def _on_the_band(
    surfaces: _Surfaces, spec: ToolSpec, *bound: Any, replicate_id: str | None = None
) -> _Editor:
    del spec
    return SpanEditor(surfaces.timeline, *bound, replicate_id=replicate_id)


def _on_the_surface(
    surfaces: _Surfaces, spec: ToolSpec, *bound: Any, replicate_id: str | None = None
) -> _Editor | None:
    """The panel this parameter's declared surface is drawn on, or no editor.

    Three ways to be offered nothing, and none of them is a defect: the caller
    drew no panel for this surface, or drew one whose axis is not the parameter's
    (`SurfacePanel.takes_handles`). The spec is read for `param_surfaces` and for
    nothing else — which surface a band names is the one tool fact this module is
    allowed, and it is a kind.
    """
    _session, _node_id, param = bound[0], bound[1], bound[2]
    del _session, _node_id
    panel = surfaces.bands.get(spec.param_surfaces[param])
    if panel is None or not panel.takes_handles:
        return None
    return BandEditor(panel, *bound, replicate_id=replicate_id)


#: Kind to editor, and the whole of this module's tool knowledge. Partial over
#: `ParamStereotype` where the generator's map is total, and the difference is
#: the point: a kind with no entry here is typed into the panel, where a kind
#: with no entry there is a parameter no panel can show.
_EDITORS = {
    ParamStereotype.REGION: _on_the_canvas,
    ParamStereotype.SPAN: _on_the_band,
    ParamStereotype.BAND: _on_the_surface,
}


def bind_editors(
    session: Session,
    node_id: str,
    spec: ToolSpec,
    values: Mapping[str, Any],
    *,
    canvas: VideoCanvas,
    timeline: TimelineStrip,
    region_extent: tuple[int, int] | None,
    bands: Mapping[DisplaySurface, SurfacePanel] | None = None,
    replicate_id: str | None = None,
) -> dict[str, _Editor]:
    """An editor over every parameter of `node_id` whose kind is edited by gesture.

    The spec is handed in rather than looked up, for `ParamForm`'s reason: this
    module never learns which tool it is drawing, and a registry lookup here is
    the one import that would make a `tool_id` branch possible to write.

    `values` are the node's parameters as the document holds them — the same
    mapping the form is built from, so the panel and the overlays cannot show
    two different answers, and a parameter the document is silent about arrives
    as `None` rather than as a default invented here.

    `region_extent` is the size of the frame this node is handed, and `None`
    says the caller does not know it — which is a region parameter with no
    editor rather than one editing in whatever units the canvas happens to be
    showing. See `RegionEditor`.

    `bands` is the panel drawing each display surface this node declares, and
    what is absent from it is a band with no picture: the same refusal one
    argument up, for the same reason. The caller draws the panels because it is
    the one that knows where they hang and what fed them.

    `replicate_id` is which region the gesture is about, and `None` is the
    baseline. It has to agree with what `values` was read for or the overlay
    would open on one region's box and commit to another's — which is why both
    are the caller's single answer rather than two lookups made here.
    """
    editors: dict[str, _Editor] = {}
    surfaces = _Surfaces(canvas, timeline, region_extent, dict(bands or {}))
    for name, kind in spec.param_stereotypes.items():
        build = _EDITORS.get(kind)
        if build is None:
            continue
        editor = build(
            surfaces, spec, session, node_id, name, values.get(name), replicate_id=replicate_id
        )
        if editor is not None:
            editors[name] = editor
    return editors
