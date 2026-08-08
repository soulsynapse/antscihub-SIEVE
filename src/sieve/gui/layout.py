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
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSizePolicy, QSplitter, QVBoxLayout, QWidget

_WINDOW_WIDTH = 960
_WINDOW_HEIGHT = 540

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


def compose(canvas: QWidget, control: QWidget, timeline: QWidget) -> QWidget:
    """The canvas and the control side split evenly, the timeline under both.

    The timeline is not a layout section: it fixes its own height by design
    (`timeline/bar.STRIP_HEIGHT`), which is the declaration `_require_layout_section`
    refuses — vertically, though, and the splitter it must not fight is
    horizontal, so it is placed here rather than checked.
    """
    _require_layout_section(canvas)
    _require_layout_section(control)

    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(canvas)
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
