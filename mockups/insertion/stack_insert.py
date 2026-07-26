"""Where an operation goes in, and what happens to the one below it.

The stack panel proposed in docs/filter-tab-parity-plan.md fixes the stage
order and lets the user compose within a stage. That leaves two interaction
questions this mockup exists to answer with a mouse rather than an argument:

1. **The insertion affordance.** Seams between steps are invisible until
   hovered; a hovered seam grows a hairline and a plus. Clicking it opens a
   small "Common here" list — a curated handful for that seam — with
   "See all operations" opening the full catalogue: search, type chips, and
   the filter's guidance text beside the list.

2. **The repair question.** An inserted operation can invalidate the step
   below it: insert an extraction above `normalize` and `normalize` now
   receives a per-block series instead of an image. Two treatments, behind
   ``--variant``:

   strict — the picker does not offer operations that would break the step
            below; the catalogue shows them disabled, with the reason and the
            way out (replace the step below first) in the guidance pane.
   repair — the picker offers them with a warning badge; inserting one puts
            the step below into a visible conflict state with Swap / Remove
            inline, and the stack footer says it will not run.

Everything is fake: the registry, the costs, the captions. The palette is
deliberately not the app's. What is being decided is the interaction — the
seam affordance, the two-tier picker, and which repair treatment feels right.

Run:
    uv run python mockups/insertion/stack_insert.py --variant repair
    uv run python mockups/insertion/stack_insert.py --variant strict --shot catalog --png out.png
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# ---- palette (not the app's — the skin is not the decision) -----------------

BG = QColor(21, 22, 25)
PANEL = QColor(31, 33, 38)
PANEL_HI = QColor(40, 43, 49)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
ACCENT = QColor(94, 200, 180)
CONFLICT = QColor(235, 110, 100)
WARN = QColor(224, 176, 96)
RUNS = QColor(120, 200, 130)

# ---- the fake registry ------------------------------------------------------

IMAGE = "image"
SERIES = "per-block series"
EVENTS = "events"

STAGE_TITLES = {
    "spatial": "SPATIAL PREP",
    "extraction": "SIGNAL EXTRACTION",
    "temporal": "TEMPORAL FILTER",
    "detection": "DETECTION",
}


@dataclass(frozen=True)
class Op:
    name: str
    blurb: str
    accepts: str
    emits: str
    category: str
    cost_ms: float
    when: str
    avoid: str
    common: bool = False


REGISTRY: tuple[Op, ...] = (
    Op(
        "rescale",
        "Shrink frames by a linear scale factor before anything else looks at them.",
        IMAGE,
        IMAGE,
        "spatial",
        0.4,
        "Almost always, and almost always first: signal work rarely needs full resolution.",
        "Does not move the block grid — that is held in source pixels regardless of scale.",
    ),
    Op(
        "normalize",
        "Per-frame contrast normalization (z-score to a fixed mean and spread).",
        IMAGE,
        IMAGE,
        "spatial",
        0.6,
        "When exposure or lighting drifts over the recording and the signal should not.",
        "Does not correct spatial vignetting; it is one statistic for the whole frame.",
        common=True,
    ),
    Op(
        "background subtract",
        "Running EMA background estimate, emitting the foreground residual.",
        IMAGE,
        IMAGE,
        "spatial",
        20.6,
        "Static scenes where only the animals move and the substrate should vanish.",
        "Anything faster than the decay becomes background; warmup frames are not free.",
        common=True,
    ),
    Op(
        "denoise",
        "Edge-preserving smoothing tuned for sensor noise, not motion.",
        IMAGE,
        IMAGE,
        "spatial",
        6.2,
        "Dim footage where sensor noise leaks into the change-energy floor.",
        "Does not remove motion blur, and softens legitimate fine texture.",
        common=True,
    ),
    Op(
        "stabilize",
        "Cancel slow whole-frame drift with a rigid alignment to a rolling keyframe.",
        IMAGE,
        IMAGE,
        "spatial",
        14.8,
        "Tripod creep or thermal drift that would read as coherent global motion.",
        "Rigid only — it will not undo parallax or lens breathing.",
    ),
    Op(
        "crop to arena",
        "Restrict every later step to a region derived upstream.",
        IMAGE,
        IMAGE,
        "spatial",
        0.1,
        "When the replicate box is loose and the arena boundary is known.",
        "The region is fixed per replicate; it does not track a moving subject.",
    ),
    Op(
        "block signal · change energy",
        "Temporal-gradient energy per block (Jtt) — the cheap default.",
        IMAGE,
        SERIES,
        "extraction",
        3.1,
        "The first thing to try: any motion at all shows up here.",
        "Direction-blind, and lighting flicker shows up exactly like motion.",
        common=True,
    ),
    Op(
        "block signal · optical flow",
        "Lucas-Kanade flow speed per block — pays more for lighting robustness.",
        IMAGE,
        SERIES,
        "extraction",
        11.8,
        "When change energy is dominated by flicker or exposure steps.",
        "Speed only (no direction is kept), and it needs texture to grip.",
    ),
    Op(
        "morlet band",
        "Continuous wavelet transform; drag a frequency band out of the scalogram.",
        SERIES,
        SERIES,
        "temporal",
        2.2,
        "Rhythmic behavior with a characteristic frequency — gait, tremor, fanning.",
        "A band, not a detector: what leaves here still needs thresholding.",
        common=True,
    ),
    Op(
        "median smooth",
        "Running median over a short horizon; kills single-frame spikes.",
        SERIES,
        SERIES,
        "temporal",
        0.3,
        "Decode glitches and specular blinks that survive extraction.",
        "Horizons near the signal period start eating the signal itself.",
        common=True,
    ),
    Op(
        "envelope",
        "Magnitude envelope of the filtered signal.",
        SERIES,
        SERIES,
        "temporal",
        0.2,
        "When the detector should follow bursts of oscillation, not its phase.",
        "Meaningless upstream of the band-pass it is meant to envelope.",
        common=True,
    ),
    Op(
        "windowed count",
        "Blocks in band, mean over a detection window D, gated to events.",
        SERIES,
        EVENTS,
        "detection",
        0.1,
        "The standard gate: how many blocks, sustained how long.",
        "Emits events; nothing can run below it.",
    ),
)

BY_NAME = {op.name: op for op in REGISTRY}

CAPTIONS = {
    "rescale": "scale 0.25 · area",
    "normalize": "zscore · mean 128 sd 32",
    "background subtract": "decay 0.02 · warmup 90",
    "denoise": "sigma 1.5",
    "stabilize": "keyframe every 300",
    "crop to arena": "region: arena-1",
    "block signal · change energy": "block auto (16)",
    "block signal · optical flow": "block auto (16)",
    "morlet band": "band 9.9-25.0 Hz",
    "median smooth": "horizon 5 fr",
    "envelope": "hilbert",
    "windowed count": "D 30 fr · centered",
}

INITIAL = (
    "rescale",
    "normalize",
    "block signal · change energy",
    "morlet band",
    "windowed count",
)


# ---- the model: a list of steps and one walk that grades it -----------------


@dataclass
class Step:
    op: Op

    @property
    def caption(self) -> str:
        return CAPTIONS.get(self.op.name, "")


@dataclass(frozen=True)
class Status:
    state: str  # "ok" | "conflict" | "unreached"
    incoming: str  # the kind this step actually receives


def grade(steps: list[Step]) -> list[Status]:
    """One pass down the stack: each step is ok, the first mismatch, or after one."""
    kind = IMAGE
    out: list[Status] = []
    broken = False
    for step in steps:
        if broken:
            out.append(Status("unreached", kind))
        elif step.op.accepts != kind:
            out.append(Status("conflict", kind))
            broken = True
        else:
            out.append(Status("ok", kind))
            kind = step.op.emits
    return out


def incoming_at(steps: list[Step], seam: int) -> str:
    """The kind flowing through seam `seam` (before steps[seam])."""
    kind = IMAGE
    for step in steps[:seam]:
        if step.op.accepts != kind:
            break
        kind = step.op.emits
    return kind


# ---- small painted pieces ---------------------------------------------------


def _font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


class GapStrip(QWidget):
    """A seam. Invisible until hovered; hovered, a hairline and a plus."""

    clicked = Signal(int)

    def __init__(self, seam: int) -> None:
        super().__init__()
        self.seam = seam
        self.hot = False
        self.forced = False
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event: object) -> None:
        self.hot = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hot = False
        self.update()

    def mousePressEvent(self, event: object) -> None:
        self.clicked.emit(self.seam)

    def paintEvent(self, event: object) -> None:
        if not (self.hot or self.forced):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() / 2
        line = QColor(ACCENT)
        line.setAlpha(150)
        painter.setPen(QPen(line, 1))
        painter.drawLine(QRectF(0, y, 0, 0).topLeft(), QRectF(self.width(), y, 0, 0).topLeft())
        center_x = self.width() / 2
        radius = 7.0
        painter.setBrush(PANEL_HI)
        painter.setPen(QPen(ACCENT, 1))
        painter.drawEllipse(QRectF(center_x - radius, y - radius, radius * 2, radius * 2))
        painter.setPen(QPen(ACCENT, 1.4))
        painter.drawLine(
            QRectF(center_x - 3.5, y, 0, 0).topLeft(), QRectF(center_x + 3.5, y, 0, 0).topLeft()
        )
        painter.drawLine(
            QRectF(center_x, y - 3.5, 0, 0).topLeft(), QRectF(center_x, y + 3.5, 0, 0).topLeft()
        )


class StepCard(QWidget):
    """One operation. Owns no chain state; it is told its status and paints it."""

    replace_requested = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, index: int, step: Step, status: Status) -> None:
        super().__init__()
        self.index = index
        self.step = step
        self.status = status
        self.hot = False
        conflicted = status.state == "conflict"
        self.setFixedHeight(96 if conflicted else 58)

        self.swap_btn = QPushButton("Swap…", self)
        self.remove_btn = QPushButton("Remove", self)
        for btn in (self.swap_btn, self.remove_btn):
            btn.setVisible(conflicted)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {background: #3a2c2c; color: #eb6e64; border: 1px solid #7a4640;"
                " border-radius: 4px; padding: 3px 10px; font-size: 8pt;}"
                "QPushButton:hover {background: #4a3432;}"
            )
        self.swap_btn.clicked.connect(lambda: self.replace_requested.emit(self.index))
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.index))

        self.menu_btn = QPushButton("⋯", self)
        self.menu_btn.setVisible(False)
        self.menu_btn.setFixedSize(26, 20)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setStyleSheet(
            "QPushButton {background: transparent; color: #8b8e98; border: none; font-size: 10pt;}"
            "QPushButton:hover {color: #e6e7eb;}"
        )
        self.menu_btn.clicked.connect(lambda: self.replace_requested.emit(self.index))
        self.menu_btn.setToolTip("Replace this step")

    def resizeEvent(self, event: object) -> None:
        self.menu_btn.move(self.width() - 34, 8)
        x = self.width() - 12 - self.remove_btn.sizeHint().width()
        self.remove_btn.move(x, self.height() - 32)
        x -= 8 + self.swap_btn.sizeHint().width()
        self.swap_btn.move(x, self.height() - 32)

    def enterEvent(self, event: object) -> None:
        self.hot = True
        if self.status.state != "conflict":
            self.menu_btn.setVisible(True)
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hot = False
        self.menu_btn.setVisible(False)
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        conflicted = self.status.state == "conflict"
        unreached = self.status.state == "unreached"

        painter.setBrush(PANEL_HI if (self.hot and not unreached) else PANEL)
        edge = QColor(CONFLICT) if conflicted else QColor(LINE)
        painter.setPen(QPen(edge, 1))
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
        painter.setFont(_font(10, bold=True))
        painter.drawText(QRectF(18, 9, rect.width() - 120, 18), 0, self.step.op.name)
        painter.setPen(dim)
        painter.setFont(_font(8))
        painter.drawText(QRectF(18, 30, rect.width() - 120, 16), 0, self.step.caption)
        painter.drawText(
            QRectF(rect.width() - 96, 9, 84, 18),
            int(Qt.AlignmentFlag.AlignRight),
            f"{self.step.op.cost_ms:.1f} ms",
        )
        if unreached:
            painter.drawText(
                QRectF(rect.width() - 96, 30, 84, 16),
                int(Qt.AlignmentFlag.AlignRight),
                "unreached",
            )
        if conflicted:
            painter.setPen(CONFLICT)
            painter.setFont(_font(8))
            painter.drawText(
                QRectF(18, 52, rect.width() - 36, 16),
                0,
                f"expects {self.step.op.accepts} · receiving {self.status.incoming}",
            )


class ClickRow(QWidget):
    """A generic picker row: title, subtitle, optional right-hand badge."""

    picked = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        badge: str = "",
        badge_color: QColor = WARN,
        enabled: bool = True,
    ) -> None:
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.badge = badge
        self.badge_color = badge_color
        self.usable = enabled
        self.hot = False
        self.selected = False
        self.setFixedHeight(44 if subtitle else 32)
        if enabled:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event: object) -> None:
        self.hot = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hot = False
        self.update()

    def mousePressEvent(self, event: object) -> None:
        self.picked.emit()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        if self.selected or (self.hot and self.usable):
            painter.fillRect(self.rect(), PANEL_HI)
        title_color = QColor(TEXT if self.usable else DIM)
        if not self.usable:
            title_color.setAlpha(140)
        painter.setPen(title_color)
        painter.setFont(_font(9, bold=bool(self.subtitle)))
        span = self.width() - 28 - (70 if self.badge else 0)
        title = painter.fontMetrics().elidedText(self.title, Qt.TextElideMode.ElideRight, span)
        painter.drawText(QRect(14, 6, self.width() - 28, 16), 0, title)
        if self.subtitle:
            painter.setPen(DIM)
            painter.setFont(_font(8))
            sub = painter.fontMetrics().elidedText(
                self.subtitle, Qt.TextElideMode.ElideRight, self.width() - 28
            )
            painter.drawText(QRect(14, 24, self.width() - 28, 14), 0, sub)
        if self.badge:
            painter.setPen(self.badge_color)
            painter.setFont(_font(8))
            painter.drawText(
                QRect(0, 6, self.width() - 14, 16),
                int(Qt.AlignmentFlag.AlignRight),
                self.badge,
            )


# ---- overlays ---------------------------------------------------------------


class _Card(QFrame):
    """A child overlay that eats clicks so the window's dismiss logic misses it."""

    def mousePressEvent(self, event: object) -> None:
        pass  # accepted by default; do not fall through to the window


class Popover(_Card):
    """The 'Common here' list for one seam (or the replace list for one step)."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedWidth(352)
        self.setStyleSheet(
            f"QFrame {{background: {PANEL.name()}; border: 1px solid {LINE.name()};"
            " border-radius: 8px;}}"
        )
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(6, 8, 6, 8)
        self.body.setSpacing(2)


class Catalog(_Card):
    """'See all operations' — search, the full list for this seam, guidance."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(660, 470)
        self.setStyleSheet(
            f"QFrame {{background: {PANEL.name()}; border: 1px solid {LINE.name()};"
            " border-radius: 10px;}}"
            f"QLabel {{border: none; color: {TEXT.name()};}}"
            f"QLineEdit {{background: {BG.name()}; color: {TEXT.name()}; border: 1px solid"
            f" {LINE.name()}; border-radius: 5px; padding: 5px 8px;}}"
        )


class Scrim(QWidget):
    """Dims the stack while the catalogue is open; a click on it closes."""

    dismissed = Signal()

    def paintEvent(self, event: object) -> None:
        QPainter(self).fillRect(self.rect(), QColor(0, 0, 0, 130))

    def mousePressEvent(self, event: object) -> None:
        self.dismissed.emit()


# ---- the window -------------------------------------------------------------


class StackWindow(QWidget):
    def __init__(self, variant: str) -> None:
        super().__init__()
        self.variant = variant
        self.steps: list[Step] = [Step(BY_NAME[name]) for name in INITIAL]
        self.setWindowTitle(f"insertion mockup — {variant}")
        self.setStyleSheet(f"background: {BG.name()};")
        self.setMinimumSize(560, 880)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 16)
        outer.setSpacing(0)

        header = QLabel("LIVE CHAIN")
        header.setFont(_font(9, bold=True, spaced=True))
        header.setStyleSheet(f"color: {DIM.name()};")
        outer.addWidget(header)
        sub = QLabel("order is the data path — top to bottom · hover a seam to insert")
        sub.setFont(_font(8))
        sub.setStyleSheet(f"color: {DIM.name()};")
        outer.addWidget(sub)
        outer.addSpacing(12)

        self.stack_area = QVBoxLayout()
        self.stack_area.setSpacing(0)
        outer.addLayout(self.stack_area)
        outer.addStretch(1)

        self.footer = QLabel()
        self.footer.setFont(_font(9))
        outer.addWidget(self.footer)

        self.popover: Popover | None = None
        self.scrim: Scrim | None = None
        self.gaps: list[GapStrip] = []
        self.rebuild()

    # -- stack -----------------------------------------------------------

    def rebuild(self) -> None:
        self._close_overlays()
        while self.stack_area.count():
            item = self.stack_area.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # off-screen now; deleteLater alone ghosts into grabs
                widget.deleteLater()
        self.gaps = []

        statuses = grade(self.steps)
        seen_categories: set[str] = set()
        for i, (step, status) in enumerate(zip(self.steps, statuses, strict=True)):
            gap = GapStrip(i)
            gap.clicked.connect(self._open_insert)
            self.stack_area.addWidget(gap)
            self.gaps.append(gap)

            if step.op.category not in seen_categories:
                seen_categories.add(step.op.category)
                self.stack_area.addWidget(self._stage_label(step.op))

            card = StepCard(i, step, status)
            card.replace_requested.connect(self._open_replace)
            card.remove_requested.connect(self._remove)
            self.stack_area.addWidget(card)

        conflicts = [s for s in statuses if s.state == "conflict"]
        graded = zip(self.steps, statuses, strict=True)
        total = sum(s.op.cost_ms for s, st in graded if st.state == "ok")
        if conflicts:
            self.footer.setText(f"won't run — {len(conflicts)} conflict")
            self.footer.setStyleSheet(f"color: {CONFLICT.name()};")
        else:
            self.footer.setText(f"runs · {len(self.steps)} steps · {total:.1f} ms/frame")
            self.footer.setStyleSheet(f"color: {RUNS.name()};")

    def _stage_label(self, op: Op) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 10, 2, 4)
        title = QLabel(STAGE_TITLES[op.category])
        title.setFont(_font(8, bold=True, spaced=True))
        title.setStyleSheet(f"color: {DIM.name()};")
        layout.addWidget(title)
        layout.addStretch(1)
        chip = QLabel(f"{op.accepts} → {op.emits}" if op.accepts != op.emits else op.accepts)
        chip.setFont(_font(8))
        chip.setStyleSheet(f"color: {DIM.name()};")
        layout.addWidget(chip)
        return row

    # -- mutations ---------------------------------------------------------

    def _insert(self, seam: int, op: Op) -> None:
        self.steps.insert(seam, Step(op))
        self.rebuild()

    def _replace(self, index: int, op: Op) -> None:
        self.steps[index] = Step(op)
        self.rebuild()

    def _remove(self, index: int) -> None:
        del self.steps[index]
        self.rebuild()

    # -- pickers -----------------------------------------------------------

    def _candidates(self, incoming: str, below: Op | None) -> list[tuple[Op, bool]]:
        """Ops that fit the seam's incoming kind, flagged ok/breaks-below."""
        result = []
        for op in REGISTRY:
            if op.accepts != incoming:
                continue
            fits_below = below is None or below.accepts == op.emits
            result.append((op, fits_below))
        return result

    def _open_insert(self, seam: int) -> None:
        below = self.steps[seam].op
        incoming = incoming_at(self.steps, seam)
        anchor = self.gaps[seam]
        self._open_popover(
            anchor,
            caption="COMMON HERE",
            incoming=incoming,
            below=below,
            apply=lambda op, s=seam: self._insert(s, op),
        )

    def _open_replace(self, index: int) -> None:
        incoming = incoming_at(self.steps, index)
        below = self.steps[index + 1].op if index + 1 < len(self.steps) else None
        anchor = self.gaps[index]
        self._open_popover(
            anchor,
            caption=f"REPLACE '{self.steps[index].op.name}'",
            incoming=incoming,
            below=below,
            apply=lambda op, i=index: self._replace(i, op),
        )

    def _open_popover(
        self, anchor: QWidget, caption: str, incoming: str, below: Op | None, apply
    ) -> None:
        self._close_overlays()
        popover = Popover(self)
        label = QLabel(caption)
        label.setFont(_font(8, bold=True, spaced=True))
        label.setStyleSheet(f"color: {DIM.name()}; border: none;")
        label.setContentsMargins(10, 2, 10, 4)
        popover.body.addWidget(label)

        candidates = self._candidates(incoming, below)
        common = [(op, ok) for op, ok in candidates if op.common]
        hidden = 0
        shown = 0
        for op, fits_below in common:
            if self.variant == "strict" and not fits_below:
                hidden += 1
                continue
            badge = "" if fits_below else "needs a change below"
            row = ClickRow(op.name, op.blurb, badge=badge, badge_color=WARN)
            row.picked.connect(lambda o=op: apply(o))
            popover.body.addWidget(row)
            shown += 1
        if shown == 0:
            note = QLabel("nothing curated for this seam")
            note.setFont(_font(8))
            note.setStyleSheet(f"color: {DIM.name()}; border: none;")
            note.setContentsMargins(10, 2, 10, 2)
            popover.body.addWidget(note)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {LINE.name()}; border: none;")
        popover.body.addWidget(rule)

        see_all = ClickRow(f"See all operations…  ({len(candidates)} fit this seam)")
        see_all.picked.connect(lambda: self._open_catalog(caption, incoming, below, apply))
        popover.body.addWidget(see_all)
        if self.variant == "strict" and hidden:
            note = QLabel(f"{hidden} hidden — they would break the step below")
            note.setFont(_font(8))
            note.setStyleSheet(f"color: {DIM.name()}; border: none;")
            note.setContentsMargins(10, 2, 10, 2)
            popover.body.addWidget(note)

        popover.adjustSize()
        top_left = anchor.mapTo(self, anchor.rect().bottomLeft())
        x = min(max(top_left.x() + 40, 12), self.width() - popover.width() - 12)
        y = min(top_left.y() + 2, self.height() - popover.height() - 12)
        popover.move(x, y)
        popover.show()
        self.popover = popover

    # -- catalogue ----------------------------------------------------------

    def _open_catalog(self, caption: str, incoming: str, below: Op | None, apply) -> None:
        self._close_overlays()
        scrim = Scrim(self)
        scrim.setGeometry(self.rect())
        scrim.dismissed.connect(self._close_overlays)
        scrim.show()
        self.scrim = scrim

        catalog = Catalog(scrim)
        catalog.setFixedSize(min(600, self.width() - 32), min(500, self.height() - 120))
        layout = QVBoxLayout(catalog)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title = QLabel(f"All operations — {caption.lower()}")
        title.setFont(_font(10, bold=True))
        layout.addWidget(title)
        search = QLineEdit()
        search.setPlaceholderText("search")
        layout.addWidget(search)

        split = QHBoxLayout()
        split.setSpacing(12)
        layout.addLayout(split, 1)

        list_host = QWidget()
        list_col = QVBoxLayout(list_host)
        list_col.setContentsMargins(0, 0, 0, 0)
        list_col.setSpacing(2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(280)
        scroll.setStyleSheet(
            "QScrollArea {border: none; background: transparent;}"
            "QScrollArea > QWidget > QWidget {background: transparent;}"
            "QScrollBar:vertical {background: transparent; width: 6px; margin: 0;}"
            f"QScrollBar::handle:vertical {{background: {LINE.name()}; border-radius: 3px;"
            " min-height: 24px;}}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: none;}"
        )
        scroll.setWidget(list_host)
        split.addWidget(scroll)

        preview = QLabel()
        preview.setWordWrap(True)
        preview.setAlignment(Qt.AlignmentFlag.AlignTop)
        preview.setFont(_font(9))
        preview.setStyleSheet(
            f"background: {BG.name()}; border: 1px solid {LINE.name()};"
            " border-radius: 6px; padding: 12px;"
        )
        split.addWidget(preview, 1)

        buttons = QHBoxLayout()
        hint = QLabel("")
        hint.setFont(_font(8))
        hint.setStyleSheet(f"color: {DIM.name()};")
        buttons.addWidget(hint)
        buttons.addStretch(1)
        insert_btn = QPushButton("Insert")
        insert_btn.setEnabled(False)
        insert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        insert_btn.setStyleSheet(
            f"QPushButton {{background: {ACCENT.name()}; color: #10201c; border: none;"
            " border-radius: 5px; padding: 6px 22px; font-weight: bold;}}"
            "QPushButton:disabled {background: #33413e; color: #6a7a76;}"
        )
        buttons.addWidget(insert_btn)
        layout.addLayout(buttons)

        candidates = self._candidates(incoming, below)
        state: dict[str, object] = {"selected": None, "rows": []}

        def describe(op: Op, fits_below: bool) -> str:
            parts = [
                f"<b>{op.name}</b><br>"
                f"<span style='color:{DIM.name()}'>{op.accepts} → {op.emits}"
                f" · {op.cost_ms:.1f} ms/frame</span><br><br>"
                f"<b>When to use it</b><br>{op.when}<br><br>"
                f"<b>What it does not do</b><br>{op.avoid}"
            ]
            if not fits_below and below is not None:
                if self.variant == "strict":
                    parts.append(
                        f"<br><br><span style='color:{CONFLICT.name()}'>Disabled: the step below"
                        f" ('{below.name}') expects {below.accepts} and this emits {op.emits}."
                        " Replace the step below first (hover it → ⋯).</span>"
                    )
                else:
                    parts.append(
                        f"<br><br><span style='color:{WARN.name()}'>The step below"
                        f" ('{below.name}') expects {below.accepts}; inserting this will flag it"
                        " for a swap.</span>"
                    )
            return "".join(parts)

        def choose(op: Op, fits_below: bool, row: ClickRow) -> None:
            state["selected"] = (op, fits_below)
            for other in state["rows"]:
                other.selected = other is row
                other.update()
            preview.setText(describe(op, fits_below))
            allowed = fits_below or self.variant == "repair"
            insert_btn.setEnabled(allowed and row.usable)

        def populate(needle: str = "") -> None:
            while list_col.count():
                item = list_col.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
            rows: list[ClickRow] = []
            needle_lower = needle.lower()
            for op, fits_below in candidates:
                if needle_lower and needle_lower not in (op.name + op.blurb).lower():
                    continue
                disabled = self.variant == "strict" and not fits_below
                badge = "" if fits_below else "breaks step below"
                row = ClickRow(
                    op.name,
                    f"{op.accepts} → {op.emits}",
                    badge=badge,
                    badge_color=CONFLICT if disabled else WARN,
                    enabled=not disabled,
                )
                row.picked.connect(lambda o=op, f=fits_below, r=row: choose(o, f, r))
                list_col.addWidget(row)
                rows.append(row)
            list_col.addStretch(1)
            state["rows"] = rows

        search.textChanged.connect(populate)
        populate()
        rows = state["rows"]
        for row in rows:
            if row.usable:  # preselect so the guidance pane is never blank
                index = rows.index(row)
                choose(candidates[index][0], candidates[index][1], row)
                break
        hint.setText(f"{len(candidates)} operations fit this seam ({incoming} in)")
        insert_btn.clicked.connect(
            lambda: state["selected"] is not None and apply(state["selected"][0])
        )

        catalog.move(
            (scrim.width() - catalog.width()) // 2,
            (scrim.height() - catalog.height()) // 2,
        )
        catalog.show()

    # -- dismissal ----------------------------------------------------------

    def _close_overlays(self) -> None:
        if self.popover is not None:
            self.popover.deleteLater()
            self.popover = None
        if self.scrim is not None:
            self.scrim.deleteLater()
            self.scrim = None

    def mousePressEvent(self, event: object) -> None:
        self._close_overlays()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._close_overlays()

    def resizeEvent(self, event: object) -> None:
        if self.scrim is not None:
            self.scrim.setGeometry(self.rect())


# ---- shots (deterministic states for PNG review) ----------------------------


def apply_shot(window: StackWindow, shot: str) -> None:
    if shot == "gap":
        window.gaps[2].forced = True
        window.gaps[2].update()
    elif shot == "picker":
        window._open_insert(2)
    elif shot == "catalog":
        window._open_catalog(
            "insert above 'block signal · change energy'",
            IMAGE,
            window.steps[2].op,
            lambda op: window._insert(2, op),
        )
    elif shot == "conflict":
        if window.variant == "repair":
            window._insert(1, BY_NAME["block signal · optical flow"])
        else:
            window._open_catalog(
                "insert above 'normalize'",
                IMAGE,
                window.steps[1].op,
                lambda op: window._insert(1, op),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("strict", "repair"), default="repair")
    parser.add_argument(
        "--shot", choices=("none", "gap", "picker", "catalog", "conflict"), default="none"
    )
    parser.add_argument("--png", type=str, default="")
    parser.add_argument("--size", type=str, default="620x920")
    args = parser.parse_args()

    app = QApplication([])
    width, height = (int(part) for part in args.size.split("x"))
    window = StackWindow(args.variant)
    window.resize(width, height)
    window.show()
    if args.shot != "none":
        apply_shot(window, args.shot)
    if args.png:
        app.processEvents()
        window.grab().save(args.png)
        return
    app.exec()


if __name__ == "__main__":
    main()
