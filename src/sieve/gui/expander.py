"""The down arrow on a step, and the tool's own guidance under it.

VISION's wizard, reimagined: instead of a screen that explains the pipeline
before the user has one, the explanation sits on the step it is about and stays
shut until it is asked for. So the arrow is the whole interface, and what opens
is the text `ToolSpec.guidance` holds — no per-tool code here, which is
`param_form.py`'s property on the surface next to it
(`adr/gui-knows-kinds-not-tools.md`).

The spec is handed in rather than looked up, for `param_form.py`'s reason: this
module never learns which tool it is showing, and a registry lookup would be the
one import that made a `tool_id` branch possible to write.

The body scrolls and its height is capped, because guidance is as long as the
tool needs and a step position is as tall as the window makes it. A widget that
grew to fit its text would let the wordiest tool on the shelf decide the layout
of every other one.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.core.tool_base import ToolSpec

#: How much of the step the opened body may take. Pixels rather than a fraction
#: of the parent: the expander is placed inside a splitter whose size is the
#: user's, and a fraction would make the text taller the wider they drag it.
_BODY_HEIGHT = 200


class GuidanceExpander(QWidget):
    """One tool's guidance, closed until the arrow is clicked."""

    def __init__(self, spec: ToolSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # The arrow carries no label: the step it sits on already names the tool
        # and shows its summary, and a second copy of either here would be the
        # per-tool text this widget exists to not have.
        self.arrow = QToolButton()
        self.arrow.setCheckable(True)
        self.arrow.setArrowType(Qt.ArrowType.RightArrow)
        self.arrow.toggled.connect(self._show_body)

        self._text = QLabel(spec.guidance)
        self._text.setWordWrap(True)
        # Selectable because a user copying a threshold rule of thumb into their
        # notes is the reading this text is written for.
        self._text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self._text.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._body = QScrollArea()
        self._body.setWidget(self._text)
        # Without this the label keeps its own size hint inside the viewport and
        # word wrap never happens: it scrolls sideways instead.
        self._body.setWidgetResizable(True)
        self._body.setMaximumHeight(_BODY_HEIGHT)
        self._body.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.arrow)
        layout.addWidget(self._body)
        self.setMaximumHeight(self.arrow.sizeHint().height() + _BODY_HEIGHT)

    def text(self) -> str:
        """The guidance this expander was built to show."""
        return self._text.text()

    def body(self) -> QWidget:
        """The label the text is laid out in, whether or not it is showing."""
        return self._text

    def is_expanded(self) -> bool:
        """Whether the guidance is on the step.

        The body rather than `self.arrow.isChecked()`: the arrow is the input to
        the behaviour, so an accessor that reads it makes every assertion about
        opening an assertion about `QToolButton.setCheckable`, and the widget
        shipping open reads as correct
        (`findings/loop/2026.08.08-a-widgets-state-accessor-reads-the-toggle-and-not-the-thing-toggled.md`).
        `isHidden` rather than `isVisible` because a widget whose window has
        never been shown is not visible either way, and most callers here are
        tests that never show one.
        """
        return not self._body.isHidden()

    def _show_body(self, expanded: bool) -> None:
        self._body.setVisible(expanded)
        self.arrow.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
