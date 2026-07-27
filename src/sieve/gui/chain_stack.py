"""The operation stack: the live chain as cards under fixed stage headers.

One presentation over `gui/chain_model.py` — the view draws what the model
grades and emits what the user asked for; it holds no chain state of its own.
`rebuild` takes the steps, their grades, their captions, and the body widgets
the tab owns, and reconstructs the column; everything else is signals out
(`remove_requested`, `swap_requested`, `insert_requested`, `reset_clicked`)
for the tab to apply to the model and echo back through the next `rebuild`.

**Body widgets are borrowed, never owned.** The knobs and the embedded graphs
are the tab's long-lived widgets (the graphs are expensive and the knobs hold
focus); a rebuild detaches every borrowed widget *before* tearing its host
card down, because a parentless PySide widget dies with its Python reference
and takes its children with it — the parent-death trap the mockup cycle hit
(parity plan learning 6, applied inside one host).

**Conflict is permit-then-repair** (plan § 2). A conflicted card gets the red
edge, the expects/receiving message the grade carries, and inline Swap/Remove
— the chain is allowed to be broken and the repair is offered where the break
is. Everything after the first conflict paints dimmed as unreached.

**Seams are visible affordances and deliberate no-ops.** A hovered seam grows
a hairline and a plus, and clicking one emits `insert_requested` — which the
tab answers with a status line until item 7 builds the wizard that opens
here. The affordance ships first so the gesture is discoverable the day the
wizard lands.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.band_plot import DIM, LINE, PANEL, TEXT, plot_font
from sieve.gui.chain_model import STAGE_CHIPS, ChainStep, Stage, Status, StepGrade

#: Conflict red — the card edge, the message, and the repair buttons.
CONFLICT = QColor(235, 110, 100)

#: A hovered card's fill, one step lighter than the panel.
_PANEL_HOT = QColor(38, 41, 47)

#: Painted header height; the conflict row extends it.
_HEADER_H = 40
_CONFLICT_EXTRA = 30

_HOVER_CSS = (
    "QPushButton {background: transparent; color: #8b8e98; border: 1px solid"
    " transparent; border-radius: 4px; padding: 1px 8px; font-size: 8pt;}"
    "QPushButton:hover {color: #e6e7eb; border-color: #55583f;}"
)
_REPAIR_CSS = (
    "QPushButton {background: #3a2c2c; color: #eb6e64; border: 1px solid #7a4640;"
    " border-radius: 4px; padding: 2px 10px; font-size: 8pt;}"
    "QPushButton:hover {background: #4a3432;}"
)


class SeamStrip(QWidget):
    """One seam between cards: invisible until hovered, then hairline + plus."""

    clicked = Signal(int)

    def __init__(self, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.seam_index = index
        self._hot = False
        self.setFixedHeight(12)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event: object) -> None:
        del event
        self._hot = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        del event
        self._hot = False
        self.update()

    def mousePressEvent(self, event: object) -> None:
        del event
        self.clicked.emit(self.seam_index)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        if not self._hot:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        y = self.height() / 2.0
        painter.setPen(QPen(DIM, 1.0))
        painter.drawLine(QPointF(4.0, y), QPointF(self.width() - 26.0, y))
        cx = self.width() - 16.0
        painter.drawEllipse(QPointF(cx, y), 6.0, 6.0)
        painter.drawLine(QPointF(cx - 3.0, y), QPointF(cx + 3.0, y))
        painter.drawLine(QPointF(cx, y - 3.0), QPointF(cx, y + 3.0))
        painter.end()


class StageHeader(QWidget):
    """A fixed stage title with its `in → out` type chip."""

    def __init__(self, stage: Stage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        chip_text = dict(STAGE_CHIPS)[stage]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 8, 2, 3)
        title = QLabel(stage.upper())
        title.setFont(plot_font(8, bold=True, spaced=True))
        title.setStyleSheet(f"color: {DIM.name()};")
        layout.addWidget(title)
        layout.addStretch(1)
        chip = QLabel(chip_text.replace("->", "→"))
        chip.setFont(plot_font(8))
        chip.setStyleSheet(f"color: {DIM.name()};")
        layout.addWidget(chip)


class StepCard(QWidget):
    """One step: painted header (title, caption, status) over borrowed bodies.

    Emits and never applies: `swap_clicked` / `remove_clicked` carry the
    step id, and the card's own appearance changes only when the next
    `rebuild` hands it new inputs.
    """

    swap_clicked = Signal(str)
    remove_clicked = Signal(str)

    def __init__(
        self,
        step: ChainStep,
        grade: StepGrade,
        caption: str,
        parent: QWidget | None = None,
        *,
        provisional: bool = False,
    ) -> None:
        super().__init__(parent)
        self.step = step
        self.grade = grade
        self.caption = caption
        self.provisional = provisional
        self._hot = False

        conflicted = grade.status is Status.CONFLICT
        header = _HEADER_H + (_CONFLICT_EXTRA if conflicted else 0)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, header, 14, 10)
        self.body.setSpacing(6)

        self._swap_hover = QPushButton("swap", self)
        self._remove_hover = QPushButton("x", self)
        for button in (self._swap_hover, self._remove_hover):
            button.setVisible(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(_HOVER_CSS)
        self._swap_hover.setToolTip("Replace this step")
        self._remove_hover.setToolTip("Remove this step")

        # The permit-then-repair pair: always visible on a conflicted card.
        self._swap_repair = QPushButton("Swap…", self)
        self._remove_repair = QPushButton("Remove", self)
        for button in (self._swap_repair, self._remove_repair):
            button.setVisible(conflicted)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(_REPAIR_CSS)

        for button in (self._swap_hover, self._swap_repair):
            button.clicked.connect(lambda _=False: self.swap_clicked.emit(self.step.step_id))
        for button in (self._remove_hover, self._remove_repair):
            button.clicked.connect(lambda _=False: self.remove_clicked.emit(self.step.step_id))

    def removal_buttons(self) -> tuple[QPushButton, ...]:
        """The remove affordances, for tests that drive the gesture."""
        return (self._remove_hover, self._remove_repair)

    def resizeEvent(self, event: object) -> None:
        del event
        x = self.width() - 10 - self._remove_hover.sizeHint().width()
        self._remove_hover.move(x, 4)
        x -= 4 + self._swap_hover.sizeHint().width()
        self._swap_hover.move(x, 4)
        if self.grade.status is Status.CONFLICT:
            x = self.width() - 14 - self._remove_repair.sizeHint().width()
            self._remove_repair.move(x, _HEADER_H + 2)
            x -= 8 + self._swap_repair.sizeHint().width()
            self._swap_repair.move(x, _HEADER_H + 2)

    def enterEvent(self, event: object) -> None:
        del event
        self._hot = True
        if self.grade.status is not Status.CONFLICT:
            # Removal is always visible on hover (plan § 2); the conflicted
            # card already shows the louder repair pair instead.
            self._swap_hover.setVisible(True)
            self._remove_hover.setVisible(True)
        self.update()

    def leaveEvent(self, event: object) -> None:
        del event
        self._hot = False
        self._swap_hover.setVisible(False)
        self._remove_hover.setVisible(False)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        conflicted = self.grade.status is Status.CONFLICT
        unreached = self.grade.status is Status.UNREACHED

        painter.setBrush(_PANEL_HOT if (self._hot and not unreached) else PANEL)
        edge = QPen(CONFLICT if conflicted else LINE, 1.0)
        if self.provisional:
            # The dashed card: in the chain for real — rendered, graded,
            # graphed — but not yet committed. The wizard's Add solidifies it.
            edge = QPen(DIM, 1.0, Qt.PenStyle.DashLine)
        painter.setPen(edge)
        painter.drawRoundedRect(rect, 6, 6)
        if conflicted:
            painter.setBrush(CONFLICT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 3.5, rect.height()), 2, 2)

        text = QColor(TEXT)
        dim = QColor(DIM)
        if unreached:
            text.setAlpha(110)
            dim.setAlpha(90)
        painter.setPen(text)
        painter.setFont(plot_font(10, bold=True))
        painter.drawText(QRectF(18, 6, rect.width() - 140, 18), 0, self.step.title)
        painter.setPen(dim)
        painter.setFont(plot_font(8))
        painter.drawText(QRectF(18, 24, rect.width() - 140, 15), 0, self.caption)
        if unreached or self.provisional:
            painter.drawText(
                QRectF(rect.width() - 130, 24, 118, 15),
                int(Qt.AlignmentFlag.AlignRight),
                "unreached" if unreached else "provisional",
            )
        if conflicted:
            painter.setPen(CONFLICT)
            painter.drawText(
                QRectF(18, _HEADER_H + 4, rect.width() - 200, 16),
                0,
                self.grade.message,
            )
        painter.end()


class ChainStackView(QWidget):
    """The right column: Reset above the scrolling column of seams and cards."""

    reset_clicked = Signal()
    remove_requested = Signal(str)
    swap_requested = Signal(str)
    insert_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[StepCard] = []
        self._borrowed: list[QWidget] = []

        head = QHBoxLayout()
        title = QLabel("LIVE CHAIN")
        title.setFont(plot_font(8, bold=True, spaced=True))
        title.setStyleSheet(f"color: {DIM.name()};")
        head.addWidget(title)
        head.addStretch(1)
        self._reset = QPushButton("Reset")
        self._reset.setToolTip("Parameters, bands, and D back to defaults; the chain stays")
        self._reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset.clicked.connect(self.reset_clicked)
        head.addWidget(self._reset)

        self._host = QWidget()
        self._column = QVBoxLayout(self._host)
        self._column.setContentsMargins(0, 0, 6, 0)
        self._column.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self._host)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(head)
        layout.addWidget(scroll, 1)

    def cards(self) -> list[StepCard]:
        """The current cards, in chain order."""
        return list(self._cards)

    def card_for(self, step_id: str) -> StepCard | None:
        """The card presenting `step_id`, or None after its removal."""
        return next((card for card in self._cards if card.step.step_id == step_id), None)

    def rebuild(
        self,
        steps: Sequence[ChainStep],
        grades: Sequence[StepGrade],
        captions: Sequence[str],
        bodies: Mapping[str, Sequence[QWidget]],
        provisional: str | None = None,
    ) -> None:
        """Reconstruct the column for `steps`, borrowing `bodies` into cards.

        `provisional` names the one step the wizard is still configuring; its
        card draws dashed and says so. Everything else about it is ordinary —
        it grades, it renders, its body embeds — because the provisional step
        being *really in the chain* is what makes the preview honest.

        `bodies` maps step ids to the tab's persistent widgets, embedded in
        chain order into each card's body. Widgets borrowed by the previous
        rebuild are detached first — before any card is deleted — so they
        survive their old host (see the module docstring). A body for an
        unreached or conflicted step is left detached and hidden: no reachable
        step, no graph.
        """
        for widget in self._borrowed:
            widget.setParent(None)
            widget.hide()
        self._borrowed = []

        while self._column.count():
            item = self._column.takeAt(0)
            widget = None if item is None else item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._cards = []

        seen_stages: set[Stage] = set()
        for index, (step, grade, caption) in enumerate(zip(steps, grades, captions, strict=True)):
            seam = SeamStrip(index)
            seam.clicked.connect(self.insert_requested)
            self._column.addWidget(seam)
            if step.stage not in seen_stages:
                seen_stages.add(step.stage)
                self._column.addWidget(StageHeader(step.stage))
            card = StepCard(step, grade, caption, provisional=step.step_id == provisional)
            card.swap_clicked.connect(self.swap_requested)
            card.remove_clicked.connect(self.remove_requested)
            if grade.status is Status.OK:
                for widget in bodies.get(step.step_id, ()):
                    card.body.addWidget(widget)
                    widget.show()
                    self._borrowed.append(widget)
            self._column.addWidget(card)
            self._cards.append(card)
        tail = SeamStrip(len(steps))
        tail.clicked.connect(self.insert_requested)
        self._column.addWidget(tail)
        self._column.addStretch(1)

    def update_captions(self, captions: Mapping[str, str]) -> None:
        """Refresh caption text in place — a knob wiggle is not a rebuild."""
        for card in self._cards:
            text = captions.get(card.step.step_id)
            if text is not None and text != card.caption:
                card.caption = text
                card.update()
