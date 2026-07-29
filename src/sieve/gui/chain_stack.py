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
and takes its children with it. Parenting cards to a temporary host can
therefore destroy them during a rebuild.

**Conflict is permit-then-repair** (plan § 2). A conflicted card gets the red
edge, the expects/receiving message the grade carries, and inline Swap/Remove
— the chain is allowed to be broken and the repair is offered where the break
is. Everything after the first conflict paints dimmed as unreached.

**Seams are visible affordances and deliberate no-ops.** A hovered seam grows
a hairline and a plus, and clicking one emits `insert_requested` — which the
tab answers with a status line until item 7 builds the wizard that opens
here. The affordance ships first so the gesture is discoverable the day the
wizard lands.

**The source card stands above the stack and does not scroll with it.** It is
not a step: it is what the chain *consumes* — this replicate's crop of the
source — and it is where that boundary's state at rest lives. It sits outside
the scrolling column because a `rebuild` tears that column down on every
structural edit, and the one thing on this tab that can be mid-write must not
be rebuilt underneath a running write pass.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.band_plot import ACCENT, DIM, LINE, PANEL, TEXT, plot_font
from sieve.gui.chain_model import STAGE_CHIPS, ChainStep, Stage, Status, StepGrade
from sieve.gui.crop_binding import CropState

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
    select_clicked = Signal(str)

    def __init__(
        self,
        step: ChainStep,
        grade: StepGrade,
        caption: str,
        parent: QWidget | None = None,
        *,
        provisional: bool = False,
        selected: bool = False,
    ) -> None:
        super().__init__(parent)
        self.step = step
        self.grade = grade
        self.caption = caption
        self.provisional = provisional
        self.selected = selected
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

    def mousePressEvent(self, event: object) -> None:
        """A click anywhere a child did not take selects this step.

        Emits and never applies, like every other card gesture: the tab sets
        the selection on the model and the next `set_selected` (or `rebuild`)
        is what moves the marker — a card that painted its own click would
        disagree with the composite for a frame every time.
        """
        del event
        self.select_clicked.emit(self.step.step_id)

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
        if self.selected and not conflicted:
            # The selection marker: the composite is showing this step. The
            # conflict bar wins the same spot — a broken step's problem
            # outranks its being watched.
            painter.setBrush(ACCENT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 3.5, rect.height()), 2, 2)
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


#: What the offer costs, stated on the affordance itself rather than in a
#: tooltip or a preferences page. The numbers are the reference clip's: 46 s of luma
#: decode to write 77 seconds, and 0.09 ms/frame to read it back against the
#: parent's 9.93. A control whose price is a surprise is a control the user
#: presses once.
#:
#: The cut is over the whole source rather than the working window, so the
#: write scales with the *video*, not with what is on the timeline — and the
#: sentence says so, because "one render" would now understate it on any
#: footage longer than a window. What it buys is that moving the window is free
#: afterwards; a window-shaped cut re-encodes every time the user scrolls.
MATERIALIZE_PRICE = (
    "one decode of the whole video to write · roughly 100x cheaper to read at any window after"
)

_OFFER_CSS = (
    "QPushButton {background: #2f3a33; color: #cfe6d6; border: 1px solid #4d6a57;"
    " border-radius: 4px; padding: 3px 12px; font-size: 8pt;}"
    "QPushButton:hover {background: #3a4a40;}"
)
_QUIET_CSS = (
    "QPushButton {background: transparent; color: #8b8e98; border: 1px solid #40434b;"
    " border-radius: 4px; padding: 2px 10px; font-size: 8pt;}"
    "QPushButton:hover {color: #e6e7eb; border-color: #6a6e78;}"
)


class SourceCard(QWidget):
    """What the chain consumes, and whether it is at rest.

    Four states, one input: `set_state` takes the `CropState` and the sentences
    that go with it, and the widget decides nothing. That is deliberate — the
    reading of which state a replicate is in is `gui/crop_binding.py`'s and the
    document's, and a card that re-derived any clause of it would be the second
    answer rule 6's absent-versus-unexamined distinction exists to prevent.

    **At rest is quieter than an offer, and stale is not absent.** The goal
    state paints flat with a dim stamp and one recessive discard; the offer
    carries the accent and the price; staleness names the clause that missed and
    offers both ways out. An artifact that was cut and then orphaned is a
    different claim from one that was never cut, and the two must not render
    alike — the user who cannot tell them apart re-cuts a file they already have.
    """

    materialize_requested = Signal()
    cancel_requested = Signal()
    discard_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = CropState.ABSENT

        self._title = QLabel("SOURCE")
        self._title.setFont(plot_font(8, bold=True, spaced=True))
        self._title.setStyleSheet(f"color: {DIM.name()};")
        self._subject = QLabel()
        self._subject.setFont(plot_font(9))
        self._subject.setStyleSheet(f"color: {TEXT.name()};")
        self._detail = QLabel()
        self._detail.setFont(plot_font(8))
        self._detail.setWordWrap(True)
        self._detail.setStyleSheet(f"color: {DIM.name()};")

        self._progress = QProgressBar()
        self._progress.setTextVisible(True)
        self._progress.setFixedHeight(14)

        self._materialize = QPushButton("Materialize…")
        self._materialize.setStyleSheet(_OFFER_CSS)
        self._materialize.setCursor(Qt.CursorShape.PointingHandCursor)
        self._materialize.clicked.connect(lambda _=False: self.materialize_requested.emit())
        self._cancel = QPushButton("Cancel")
        self._cancel.setStyleSheet(_QUIET_CSS)
        self._cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel.clicked.connect(lambda _=False: self.cancel_requested.emit())
        self._discard = QPushButton("Discard")
        self._discard.setStyleSheet(_QUIET_CSS)
        self._discard.setCursor(Qt.CursorShape.PointingHandCursor)
        self._discard.clicked.connect(lambda _=False: self.discard_requested.emit())

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self._title)
        head.addStretch(1)
        head.addWidget(self._subject)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self._progress, 1)
        buttons.addStretch(1)
        buttons.addWidget(self._discard)
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._materialize)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)
        layout.addLayout(head)
        layout.addWidget(self._detail)
        layout.addLayout(buttons)

        self.set_state(CropState.ABSENT, subject="", detail="")

    @property
    def state(self) -> CropState:
        """Which of the four states is on screen. A test's observable."""
        return self._state

    def buttons(self) -> tuple[QPushButton, QPushButton, QPushButton]:
        """Materialize, Cancel, Discard — for the tests that drive the gestures."""
        return (self._materialize, self._cancel, self._discard)

    @property
    def detail(self) -> str:
        """The sentence under the title, verbatim. What a stale card must not hide."""
        return self._detail.text()

    def set_state(self, state: CropState, *, subject: str, detail: str) -> None:
        """Render `state` for `subject`, with `detail` as its one sentence.

        `detail` is passed through unaltered — for `STALE` it is the clause that
        missed, which `crop_binding` phrased and which nothing here may
        summarise away.
        """
        self._state = state
        self._subject.setText(subject)
        self._detail.setText(detail)
        self._materialize.setVisible(state in (CropState.ABSENT, CropState.STALE))
        self._materialize.setText("Re-materialize…" if state is CropState.STALE else "Materialize…")
        self._cancel.setVisible(state is CropState.WRITING)
        self._discard.setVisible(state in (CropState.AT_REST, CropState.STALE))
        self._progress.setVisible(state is CropState.WRITING)
        if state is not CropState.WRITING:
            self._progress.reset()
        self.update()

    def set_progress(self, written: int, total: int) -> None:
        """Advance the write. Ignored unless a write is what is on screen."""
        if self._state is not CropState.WRITING:
            return
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(written)

    def paintEvent(self, event: QPaintEvent) -> None:
        """The card's edge, which is the whole of its loudness.

        Accent while there is a decision to take, flat while there is not. The
        at-rest card is the only one that draws no coloured edge at all: it is
        the goal state, and a goal state that keeps announcing itself is an
        alert.
        """
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setBrush(PANEL)
        painter.setPen(QPen(CONFLICT if self._state is CropState.STALE else LINE, 1.0))
        painter.drawRoundedRect(rect, 6, 6)
        if self._state in (CropState.ABSENT, CropState.WRITING):
            painter.setBrush(ACCENT if self._state is CropState.WRITING else DIM)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 3.5, rect.height()), 2, 2)
        painter.end()


class ChainStackView(QWidget):
    """The right column: Reset above the scrolling column of seams and cards."""

    reset_clicked = Signal()
    remove_requested = Signal(str)
    swap_requested = Signal(str)
    insert_requested = Signal(int)
    select_requested = Signal(str)

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

        self._source = SourceCard()

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
        layout.addWidget(self._source)
        layout.addWidget(scroll, 1)

    @property
    def source_card(self) -> SourceCard:
        """The boundary card above the stages. The tab drives it and it alone."""
        return self._source

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
        selected: str | None = None,
    ) -> None:
        """Reconstruct the column for `steps`, borrowing `bodies` into cards.

        `provisional` names the one step the wizard is still configuring; its
        card draws dashed and says so. Everything else about it is ordinary —
        it grades, it renders, its body embeds — because the provisional step
        being *really in the chain* is what makes the preview honest.

        `selected` names the step whose composite the video pane is showing;
        its card carries the accent marker.

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
            card = StepCard(
                step,
                grade,
                caption,
                provisional=step.step_id == provisional,
                selected=step.step_id == selected,
            )
            card.swap_clicked.connect(self.swap_requested)
            card.remove_clicked.connect(self.remove_requested)
            card.select_clicked.connect(self.select_requested)
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

    def set_selected(self, step_id: str | None) -> None:
        """Move the selection marker in place — a click is not a rebuild."""
        for card in self._cards:
            wanted = card.step.step_id == step_id
            if card.selected != wanted:
                card.selected = wanted
                card.update()

    def update_captions(self, captions: Mapping[str, str]) -> None:
        """Refresh caption text in place — a knob wiggle is not a rebuild."""
        for card in self._cards:
            text = captions.get(card.step.step_id)
            if text is not None and text != card.caption:
                card.caption = text
                card.update()
