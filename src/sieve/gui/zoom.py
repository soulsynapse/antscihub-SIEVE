"""The magnifier: zoom, a pan centre, and the two rectangles between them.

**Two rectangles, and the difference between them is load-bearing.** The
*fit* is where content lands when it is aspect-fitted into a widget: a
function of the widget size and the content's aspect and nothing else. The
*view rect* is where the content is actually painted, which is the fit
magnified about a pan centre. Every mapping goes through the view rect; the
fit survives as the thing the view rect is clamped against, and that clamp is
the whole zoom-floor rule. Scrolling out can never produce a view rect smaller
than the fit, because at zoom 1.0 the two expressions are not merely close but
the same object — see `view_rect`.

This lives apart from the widget that holds it because the rule outlives any
one of them, and the clamp is the part that costs a day to re-derive. v2 had
two consumers in different units — a frame view mapping to source pixels and a
composite pane mapping to blocks — and what they shared was not a coordinate
system but the rule for producing one. Hence the centre and `at` speak in
**normalized content coordinates** — [0, 1] over the painted rectangle — and
each widget scales that into its own units. A surface with a block grid and no
frame has no pixel dimensions at all, so a shared helper denominated in source
pixels would have had nothing to say to it.

**What a widget scales the normalized point into is the space the value is
denominated in, never the image on screen.** The picture the canvas is handed
is a display proxy whose resolution moves with a preference and between
frames; what a saved region indexes cannot move at all. The extent, and the
argument for it, is `kind_editors.RegionEditor`'s, and this module's refusal
to name any unit is what keeps a proxy-shaped one from leaking in here.

The pan centre is a *request*, never a resolved value: `view_rect` is the only
place that decides what it resolves to, which is why nothing else clamps it.
Near an edge the cursor anchor consequently does not hold, and that is
correct — there is nothing beyond the content edge to slide into view.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF

#: Magnification is bounded below by the fit — the vision's rule, and the reason
#: the floor is 1.0 rather than some pixel scale: 1.0 *is* fit, whatever the
#: widget size happens to be. The ceiling is where a content pixel is large
#: enough to place unambiguously and further zoom buys nothing.
MIN_ZOOM = 1.0
MAX_ZOOM = 16.0
#: Multiplier per wheel detent.
ZOOM_STEP = 1.25


class Magnifier:
    """A zoom level and a pan centre in normalized content coordinates."""

    __slots__ = ("_centre", "zoom")

    def __init__(self) -> None:
        self.zoom = MIN_ZOOM
        #: Pan centre, normalized. Meaningless at zoom 1.0, where the clamp in
        #: `view_rect` overrides it entirely.
        self._centre = QPointF(0.5, 0.5)

    @property
    def magnified(self) -> bool:
        """Whether anything is magnified at all — the fit is not."""
        return self.zoom > MIN_ZOOM

    def reset(self) -> bool:
        """Return to the fitted view. True if the zoom actually moved."""
        self._centre = QPointF(0.5, 0.5)
        if self.zoom == MIN_ZOOM:
            return False
        self.zoom = MIN_ZOOM
        return True

    def view_rect(self, fit: QRectF) -> QRectF:
        """Where the content is painted: `fit` magnified and panned.

        Two properties this has to hold, and both come out of the clamp rather
        than out of a guard the caller has to remember:

        At zoom 1.0 it returns `fit` itself, so a wheel-out storm leaves the
        content *exactly* fitted rather than fitted to within a float epsilon.
        That exactness is what the round-trip mapping tests stand on.

        Above 1.0 the rect is clamped to cover `fit`, so the magnified content
        always fills the letterbox and there is no pan that reveals a gap.
        """
        if self.zoom <= MIN_ZOOM:
            return fit
        width = fit.width() * self.zoom
        height = fit.height() * self.zoom
        x = min(max(fit.center().x() - self._centre.x() * width, fit.right() - width), fit.left())
        y = min(max(fit.center().y() - self._centre.y() * height, fit.bottom() - height), fit.top())
        return QRectF(x, y, width, height)

    def at(self, point: QPointF, fit: QRectF) -> QPointF:
        """Widget point as normalized content coordinates, unrounded.

        The mapping the zoom anchor needs: rounding here would make a wheel
        under a stationary cursor creep, because each step would re-anchor to a
        slightly different content point than the last one landed on.
        """
        view = self.view_rect(fit)
        if view.width() <= 0 or view.height() <= 0:
            return QPointF()
        return QPointF(
            (point.x() - view.x()) / view.width(),
            (point.y() - view.y()) / view.height(),
        )

    def wheel(self, detents: float, anchor: QPointF, fit: QRectF) -> bool:
        """Magnify about widget point `anchor`. True if the zoom moved.

        Anchoring on the cursor rather than the centre is what makes the
        magnifier usable for placement: what the user is looking at stays under
        the pointer while it grows, so they do not have to chase it with a pan
        after every detent.
        """
        target = self.at(anchor, fit)
        zoom = min(max(self.zoom * (ZOOM_STEP**detents), MIN_ZOOM), MAX_ZOOM)
        if zoom == self.zoom:
            return False
        self.zoom = zoom
        self._recentre_on(target, anchor, fit)
        return True

    def _recentre_on(self, target: QPointF, anchor: QPointF, fit: QRectF) -> None:
        """Pan so normalized content point `target` lands at widget `anchor`.

        Inverts `view_rect`'s placement for the centre.
        """
        width = fit.width() * self.zoom
        height = fit.height() * self.zoom
        if width <= 0 or height <= 0:
            return
        self._centre = QPointF(
            (fit.center().x() - anchor.x()) / width + target.x(),
            (fit.center().y() - anchor.y()) / height + target.y(),
        )
