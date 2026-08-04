"""Secret: how a fixed, ordered set of labeled panes drills in and out —
the Obsidian "sliding panes" look (Andy's mode): exactly one pane is
expanded at a time; every pane before it in the order is not destroyed and
not fully hidden either, it's collapsed to a thin, clickable, label-only
bar. Drilling forward (``set_current`` to a higher index) covers the
current pane with the next one, collapsing the current to a bar behind it;
going back re-expands an existing bar's pane in place — nothing rebuilds
just from moving. A pane past the current index is neither a bar nor
expanded — it's simply not shown yet, not "visited".

Not what a pane's label means or when to move — that's entirely the
caller's (``gui/control/pipeline`` or ``gui/app.py``'s) secret; this module
only ever owns the collapse/expand mechanic and the bar's own look.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    Qt,
    Signal,
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

_BAR_WIDTH = 28
_ANIMATION_MS = 220


class _BreadcrumbBar(QWidget):
    """A collapsed pane's stand-in: a thin strip painting its label
    rotated, clickable to ask for that pane back."""

    clicked = Signal()

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = label
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_label(self, label: str) -> None:
        self._label = label
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: ARG002 - Qt event signature
        self.clicked.emit()

    def paintEvent(self, event) -> None:  # noqa: ARG002 - Qt event signature
        painter = QPainter(self)
        palette = self.palette()
        painter.fillRect(self.rect(), palette.alternateBase())
        painter.setPen(palette.color(palette.ColorRole.WindowText))
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(QRect(0, 0, self.height(), self.width()), Qt.AlignmentFlag.AlignCenter, self._label)


class BreadcrumbStack(QWidget):
    """``labeled_panes`` is fixed at construction — one (label, widget) per
    position, position 0 expanded to start. ``replace_pane`` swaps a
    position's widget (and optionally its label) in place, with no
    animation, whether or not it's the current one — used when content
    changes (a new project picked, a pipeline loaded) as opposed to when
    only the current position changes (``set_current``, the only thing
    that animates)."""

    activated = Signal(int)  # a breadcrumb bar was clicked, naming its position

    def __init__(self, labeled_panes: list[tuple[str, QWidget]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._labels = [label for label, _ in labeled_panes]
        self._panes = [pane for _, pane in labeled_panes]
        for pane in self._panes:
            pane.setParent(self)

        self._bars = [_BreadcrumbBar(label, self) for label in self._labels]
        for i, bar in enumerate(self._bars):
            bar.clicked.connect(lambda index=i: self.activated.emit(index))
            bar.hide()

        self._current = 0
        self._group: QParallelAnimationGroup | None = None

        for i, pane in enumerate(self._panes):
            pane.setGeometry(self._geometry_for(i, 0))
            pane.setVisible(i == 0)

    def current_index(self) -> int:
        return self._current

    def replace_pane(self, index: int, widget: QWidget, label: str | None = None) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        old = self._panes[index]
        widget.setParent(self)
        self._panes[index] = widget
        if label is not None:
            self._labels[index] = label
            self._bars[index].set_label(label)

        if index == self._current:
            widget.setGeometry(self._geometry_for(index, self._current))
            # Same reasoning as everywhere else a widget joins an
            # already-visible tree: reparenting alone doesn't show it.
            widget.show()
        else:
            widget.hide()

        old.hide()
        old.setParent(None)
        old.deleteLater()

    def set_current(self, index: int) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        old_index = self._current
        if index == old_index:
            return
        self._current = index

        # The target's bar (if it had one, going backward) must step aside
        # for the animation — otherwise it fights the pane sliding over it.
        self._bars[index].hide()

        group = QParallelAnimationGroup(self)
        for i in (old_index, index):
            widget = self._panes[i]
            start = widget.geometry() if widget.isVisible() else self._geometry_for(i, old_index)
            widget.show()
            animation = QPropertyAnimation(widget, b"geometry", self)
            animation.setDuration(_ANIMATION_MS)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.setStartValue(start)
            animation.setEndValue(self._geometry_for(i, index))
            group.addAnimation(animation)

        group.finished.connect(lambda: self._settle(index))
        self._group = group
        group.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._group is not None:
            self._group.stop()
        self._settle(self._current)

    def _settle(self, index: int) -> None:
        """The at-rest layout for a given current index: exactly one pane
        expanded and visible, everything before it a visible bar,
        everything after hidden entirely — the state a resize or a
        finished animation must always land back on."""
        for i, pane in enumerate(self._panes):
            if i == index:
                pane.setGeometry(self._geometry_for(i, index))
                pane.show()
            else:
                pane.hide()
        for i, bar in enumerate(self._bars):
            if i < index:
                bar.setGeometry(self._geometry_for(i, index))
                bar.show()
            else:
                bar.hide()

    def _geometry_for(self, index: int, current: int) -> QRect:
        """Where position ``index`` belongs when ``current`` is expanded:
        a bar slot before it, the remaining width if it's the one
        expanded, or an off-screen sliver on the right if it's beyond
        ``current`` — never visited, so it has nowhere "at rest" yet."""
        if index < current:
            return QRect(index * _BAR_WIDTH, 0, _BAR_WIDTH, self.height())
        if index == current:
            x = current * _BAR_WIDTH
            return QRect(x, 0, max(self.width() - x, 0), self.height())
        return QRect(self.width(), 0, 0, self.height())
