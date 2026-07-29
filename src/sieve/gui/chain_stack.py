


































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


CONFLICT = QColor(235, 110, 100)


_PANEL_HOT = QColor(38, 41, 47)


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


            edge = QPen(DIM, 1.0, Qt.PenStyle.DashLine)
        painter.setPen(edge)
        painter.drawRoundedRect(rect, 6, 6)
        if self.selected and not conflicted:



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

        return self._state

    def buttons(self) -> tuple[QPushButton, QPushButton, QPushButton]:

        return (self._materialize, self._cancel, self._discard)

    @property
    def detail(self) -> str:

        return self._detail.text()

    def set_state(self, state: CropState, *, subject: str, detail: str) -> None:






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

        if self._state is not CropState.WRITING:
            return
        self._progress.setMaximum(max(total, 1))
        self._progress.setValue(written)

    def paintEvent(self, event: QPaintEvent) -> None:







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

        return self._source

    def cards(self) -> list[StepCard]:

        return list(self._cards)

    def card_for(self, step_id: str) -> StepCard | None:

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

        for card in self._cards:
            wanted = card.step.step_id == step_id
            if card.selected != wanted:
                card.selected = wanted
                card.update()

    def update_captions(self, captions: Mapping[str, str]) -> None:

        for card in self._cards:
            text = captions.get(card.step.step_id)
            if text is not None and text != card.caption:
                card.caption = text
                card.update()
