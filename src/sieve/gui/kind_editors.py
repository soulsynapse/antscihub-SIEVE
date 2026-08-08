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
which is the ordinary case and not a defect. `BAND` is the kind that is neither:
it is a gesture with no axis to be made on
(`todo/a-bands-axis-has-no-vocabulary-and-no-plot.md`), so it has no entry here
and a read-only restatement in the form.

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
from typing import Any

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from sieve.core.pipeline_model import SourceSpan
from sieve.core.tool_base import ParamStereotype, ToolSpec
from sieve.core.types import ROI
from sieve.gui.canvas import VideoCanvas
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

    def __init__(self, host: QWidget, session: Session, node_id: str, param: str) -> None:
        super().__init__(host)
        self._host = host
        self._session = session
        self._node_id = node_id
        self._param = param
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
        """The gesture's whole output: one parameter, through the command layer."""
        issue(self._session, SetParam(node_id=self._node_id, param=self._param, value=value))


class RegionEditor(_Editor):
    """A rectangle dragged on the viewport, in the pixels of the frame it is drawn on.

    *Which* pixels those are is the surface's answer and not this module's. The
    value is denominated in the image the canvas is showing, and whether that
    image is the node's own input — `crop.py` says a region indexes the frame
    its node is handed, while the viewport is fed a display proxy of the source
    (`transport/decode_worker.PROXY_WIDTH`) — is a question about what gets fed
    to the canvas, which belongs where the editors are placed
    (`todo/the-first-cut-meets-its-gate.md`).

    Clamped to the image and not to the widget. The canvas centres the frame and
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
    ) -> None:
        super().__init__(host, session, node_id, param)
        self._canvas = host
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
        """Screen pixels per image pixel, zero when there is no frame."""
        image = self._canvas.frame
        box = self._canvas.frame_rect()
        if image is None or box.isEmpty():
            return 0.0
        return box.width() / image.width()

    def _image_point(self, point: QPointF) -> QPointF | None:
        """`point` in the shown image's pixels, or None when nothing is shown."""
        image = self._canvas.frame
        scale = self._scale()
        if image is None or scale <= 0.0:
            return None
        box = self._canvas.frame_rect()
        return QPointF(
            min(max((point.x() - box.left()) / scale, 0.0), float(image.width())),
            min(max((point.y() - box.top()) / scale, 0.0), float(image.height())),
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

    Two handles and nothing between them. The strip means "seek here" everywhere
    it is not a handle, so the body of the band is left to it: an editor owning
    the middle would take scrubbing away for as long as a span node is on screen,
    and a span has no body gesture of its own — moving one whole is a
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
    ) -> None:
        super().__init__(host, session, node_id, param)
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


def _on_the_canvas(canvas: VideoCanvas, band: TimelineStrip, *bound: Any) -> _Editor:
    del band
    return RegionEditor(canvas, *bound)


def _on_the_band(canvas: VideoCanvas, band: TimelineStrip, *bound: Any) -> _Editor:
    del canvas
    return SpanEditor(band, *bound)


#: Kind to editor, and the whole of this module's tool knowledge. Partial over
#: `ParamStereotype` where the generator's map is total, and the difference is
#: the point: a kind with no entry here is typed into the panel, where a kind
#: with no entry there is a parameter no panel can show.
_EDITORS = {
    ParamStereotype.REGION: _on_the_canvas,
    ParamStereotype.SPAN: _on_the_band,
}


def bind_editors(
    session: Session,
    node_id: str,
    spec: ToolSpec,
    values: Mapping[str, Any],
    *,
    canvas: VideoCanvas,
    timeline: TimelineStrip,
) -> dict[str, _Editor]:
    """An editor over every parameter of `node_id` whose kind is edited by gesture.

    The spec is handed in rather than looked up, for `ParamForm`'s reason: this
    module never learns which tool it is drawing, and a registry lookup here is
    the one import that would make a `tool_id` branch possible to write.

    `values` are the node's parameters as the document holds them — the same
    mapping the form is built from, so the panel and the overlays cannot show
    two different answers, and a parameter the document is silent about arrives
    as `None` rather than as a default invented here.
    """
    editors: dict[str, _Editor] = {}
    for name, kind in spec.param_stereotypes.items():
        build = _EDITORS.get(kind)
        if build is not None:
            editors[name] = build(canvas, timeline, session, node_id, name, values.get(name))
    return editors
