"""Where the main window's two halves sit and how big they start.

Not what fills them: swapping the canvas' contents must not touch this file,
and moving the split must not touch theirs. The canvas and the control side are
one package by decision — a dragged crop box is the active step drawn elsewhere
(`PLAN.md`, Phase 7) — so the fence between them is this module's silence about
their insides, not an import contract.

The scrubber runs the full width under both halves rather than under the canvas
alone. VISION calls it "the bottom area", and it is the one surface whose answer
— where am I, and what stretch am I working on — must not depend on which
position the control track is showing.

**The graph is on the viewing half, under the canvas, and not on the step**
(07.11). It is a second viewport rather than a control: what it shows is the
footage measured, over the same frames the canvas is playing, and a user tuning
a parameter watches the picture and the trace together. On the step position it
would be visible only while the walk stood on that node — which is exactly the
moment a slider is being dragged, and exactly not the moment the pipeline
position is being read. Under the canvas it is a splitter away from being any
size the user wants, including none.

**What is under the canvas is a step, and the graph is inside it** (09.3). The
slot is sized to what its step asks for rather than to a share of the window: a
strip for a step whose surface is a sentence, the plot's own height for one that
draws, and the scalogram pair's room if a step ever asks for two. A fixed split
gives the same height to all three, which is either a plot squeezed or a
sentence with a hand's width of empty under it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QSplitter, QVBoxLayout, QWidget

_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540

#: The most of the viewing column the pinned slot may take, in percent. The
#: footage is the thing being tuned against, so a step asking for more than this
#: gets its own scroll area instead of the canvas' room.
PIN_MAX_SHARE = 60

_FIXED_POLICIES = (QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)


def _require_layout_section(widget: QWidget) -> None:
    """Refuse a widget that would take the splitter's decision away from it.

    Two ways to take it, both checked, because the second is invisible in the
    first's terms: a Fixed or Maximum horizontal policy says so outright, while
    a nominally Preferred widget can fix a numeric minimum that Qt honours
    regardless of policy. A policy is a declaration; a minimum is a fact.
    """
    policy = widget.sizePolicy().horizontalPolicy()
    if policy in _FIXED_POLICIES:
        raise TypeError(
            f"{widget.__class__.__name__} has horizontal size policy {policy.name} — a layout "
            "section must accept the width the splitter assigns it, not fix its own."
        )

    half_width = _WINDOW_WIDTH // 2
    min_width = max(widget.minimumWidth(), widget.minimumSizeHint().width())
    if min_width > half_width:
        raise TypeError(
            f"{widget.__class__.__name__} has a minimum width of {min_width}px, more than its "
            f"{half_width}px share of a {_WINDOW_WIDTH}px window — a layout section must fit "
            "inside the split, not force it wider."
        )


class CanvasSlot(QWidget):
    """The left half, held for the window's lifetime, one widget at a time.

    It exists so that replacing the canvas does not rebuild the control side
    beside it: the control track's own state — which of its three positions is
    current — is view state nothing else holds, and a rebuild would silently
    return the user to the start of the walk.
    """

    def __init__(self, initial: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        _require_layout_section(initial)
        self._current = initial
        self._layout.addWidget(initial)

    def set_content(self, widget: QWidget) -> None:
        _require_layout_section(widget)
        old = self._current
        self._layout.removeWidget(old)
        old.setParent(None)
        old.deleteLater()
        self._current = widget
        self._layout.addWidget(widget)
        # Adding a widget to an already-visible tree does not itself make the
        # widget visible.
        widget.show()


class ViewingColumn(QSplitter):
    """The left half: the canvas over the pinned step, and how tall each is.

    The slot is a splitter pane the window keeps for good, its step swapped
    inside it — so a pin that moves re-fits the split rather than rebuilding the
    column, and the canvas above never flickers for a change that is not about
    it. A drag of the handle is the user's answer and stands until the next pin,
    which is the only thing that re-fits.

    All this module knows about what fills the slot is that it answers
    `natural_height()` — the fence the file's first paragraph draws, kept for a
    pane whose size is this module's business and whose contents are not.
    """

    def __init__(self, canvas: QWidget, pinned: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        _require_layout_section(canvas)
        _require_layout_section(pinned)
        self.addWidget(canvas)
        self.addWidget(pinned)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 0)
        self._pinned = pinned
        # The window's own height rather than this splitter's, which is zero
        # until it is shown — `compose` gives the reason at length.
        self.fit_pin(_WINDOW_HEIGHT)

    @property
    def pinned(self) -> QWidget:
        """The step in the slot."""
        return self._pinned

    def set_pinned(self, widget: QWidget) -> None:
        """Put `widget` in the slot and give it the height it asks for.

        The old one is destroyed, so anything inside it that outlives the pin —
        the one graph panel the tuning loop fills — has to have been taken out
        by the caller that owns it (`app.py`).
        """
        _require_layout_section(widget)
        old = self._pinned
        self.replaceWidget(1, widget)
        self._pinned = widget
        widget.show()
        old.setParent(None)
        old.deleteLater()
        self.fit_pin()

    def pin_height(self, total: int) -> int:
        """How much of `total` the slot takes: what its step asks for, capped."""
        return min(self._pinned.natural_height(), total * PIN_MAX_SHARE // 100)

    def fit_pin(self, total: int | None = None) -> None:
        """Give the slot its height and the canvas the rest of `total`.

        `total` defaults to what the column currently holds, which is the height
        a user's own drag of the handle divided — the fit re-divides it rather
        than reaching for the window's.
        """
        height = sum(self.sizes()) if total is None else total
        wanted = self.pin_height(height)
        self.setSizes([height - wanted, wanted])


def compose(viewing: QWidget, control: QWidget, timeline: QWidget) -> QWidget:
    """The viewing column on the left, the control side on the right, timeline under both.

    The timeline is not a layout section: it fixes its own height by design
    (`timeline/bar.STRIP_HEIGHT`), which is the declaration `_require_layout_section`
    refuses — vertically, though, and the splitter it must not fight is
    horizontal, so it is placed here rather than checked.

    The column's two halves are checked where they enter it rather than here:
    they share the left half's width, so a widget that fixed its own would move
    the main split just as surely from one row down.
    """
    _require_layout_section(control)

    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(viewing)
    split.addWidget(control)
    split.setStretchFactor(0, 1)
    split.setStretchFactor(1, 1)
    # `setSizes` scales its argument against the splitter's *current* width,
    # which is 0 while it is unshown and unparented — so a ratio like [1, 1] is
    # read as literal pixels, collapses to nothing, and first show falls back to
    # sizeHint-driven allocation instead. Real pixel values against the window
    # size this module owns sidestep that.
    split.setSizes([_WINDOW_WIDTH // 2, _WINDOW_WIDTH // 2])

    stacked = QWidget()
    column = QVBoxLayout(stacked)
    column.setContentsMargins(0, 0, 0, 0)
    column.setSpacing(0)
    column.addWidget(split, 1)
    column.addWidget(timeline)
    return stacked


def size_window(window: QMainWindow) -> None:
    # A starting size still matters for a window that opens maximized: it is
    # what un-maximizing restores to.
    window.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
    window.showMaximized()
