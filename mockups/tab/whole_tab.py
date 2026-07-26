"""The whole filter tab: the operation stack hosts the graphs.

docs/filter-tab-parity-plan.md fixes the frame: video left with the green
blocks-in-band graph and detection window D under it; the seeker (with
Length) across the bottom. The right column is the *operation stack* from
mockups/insertion, and everything lives inside its blocks:

  rescale          Downsample spinbox in the card body
  normalize        mode combo in the card body
  block signal     Block spinbox + the quick-switch (change energy Jtt |
                   LK optical flow) - one click swaps the step, bands kept
  morlet band      the scalogram and the band-power density graph, embedded
  windowed count   threshold/D summary; its graph is promoted under the
                   video per the target layout, and the card says so

Picking an operation - the wizard. A seam click (or a card's `swap`) opens
a near-full-window inset helper. It is not a list next to a description; it
is the *configuration surface for the provisional step*. Three zones:

  left     the equivalents for this seam - hover or click swaps the
           provisional step in place, so comparing candidates is the same
           gesture as choosing one
  center   the current video, playing (mocked as a still), with the
           provisional chain's spatial ops genuinely applied - `denoise`
           blurs the frame, `rescale` pixelates, `zscore` restretches -
           the signal graph below it, and the green detection graph with
           its D row below that - all fully live (handles drag, detections
           update), because a candidate is judged by what it does to the
           green
  right    the selected operation's own settings (the same widgets its
           stack card owns), and its guidance below

The chain cannot be broken from here: operations that would break the step
below, and duplicates of steps already in the chain, are listed but
disabled with the reason. Add commits; Cancel or Esc restores everything
exactly as it was. (The full don't-break-yourself ruleset - category
inference, domain nonsense - is real-implementation work; the wizard mocks
its shape: the suggested category leads the list.)

Removal stays visible on the stack: hovering any card shows `swap` and
`x`; conflicted cards (from removals or loaded files - insertion can no
longer create them) keep their inline Swap/Remove.

Run:
    uv run python mockups/tab/whole_tab.py
    uv run python mockups/tab/whole_tab.py --shot wizard --png out.png
    # shots: tuned, lk, conflict, wizard, wizard-spatial
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

_MOCKUPS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_MOCKUPS / "graphs"))
sys.path.insert(0, str(_MOCKUPS / "seeker"))
sys.path.insert(0, str(_MOCKUPS / "insertion"))

import detect_graphs as dg  # noqa: E402
import seeker_bar as sb  # noqa: E402
import stack_insert as si  # noqa: E402

# ---- the second signal ---------------------------------------------------------

_rng = np.random.default_rng(23)
LK_BLOCKS = np.sqrt(dg.BLOCKS) * 9.0 + _rng.normal(0.0, 1.5, dg.BLOCKS.shape).astype(np.float32)
LK_CUBE = dg.morlet_power(LK_BLOCKS)
LK_POOLED = dg.morlet_power(LK_BLOCKS.mean(axis=1))

JTT = "block signal · change energy"
LK = "block signal · optical flow"
CUBES = {JTT: dg.CUBE, LK: LK_CUBE}
POOLEDS = {JTT: dg.POOLED, LK: LK_POOLED}

TAB_WINDOW = (2_400, 4_200)
HEADER_H = 46
CONFLICT_EXTRA = 34


# ---- real-enough effects for the provisional preview ---------------------------


def _median_smooth(m: np.ndarray) -> np.ndarray:
    shifts = [np.roll(m, k, axis=0) for k in (-2, -1, 0, 1, 2)]
    return np.median(np.stack(shifts), axis=0).astype(np.float32)


def _envelope(m: np.ndarray) -> np.ndarray:
    width = 25
    pad = width // 2
    padded = np.pad(np.abs(m), ((pad, width - 1 - pad), (0, 0)), mode="edge")
    cum = np.vstack([np.zeros((1, m.shape[1]), np.float32), np.cumsum(padded, axis=0)])
    return ((cum[width:] - cum[:-width]) / width).astype(np.float32)


SERIES_EFFECTS = {"median smooth": _median_smooth, "envelope": _envelope}


def _box_blur(img: np.ndarray, width: int) -> np.ndarray:
    pad = width // 2
    x = np.pad(img, ((pad, width - 1 - pad), (pad, width - 1 - pad), (0, 0)), mode="edge")
    ii = x.cumsum(axis=0).cumsum(axis=1)
    ii = np.pad(ii, ((1, 0), (1, 0), (0, 0)))
    s = ii[width:, width:] - ii[:-width, width:] - ii[width:, :-width] + ii[:-width, :-width]
    return (s / (width * width)).astype(np.float32)


def derive_from(cube: np.ndarray, det: dg.Detector, effects: list[str]) -> dg.Derived:
    """dg.derive parameterized by signal cube and post-transform effects."""
    i, j = det.freq_indices()
    m = cube[i : j + 1].sum(axis=0)
    for name in effects:
        m = SERIES_EFFECTS[name](m)
    v_lo = -np.inf if det.v_lo is None else det.v_lo
    v_hi = np.inf if det.v_hi is None else det.v_hi
    count = ((m >= v_lo) & (m <= v_hi)).sum(axis=1).astype(np.float32)
    cum = np.concatenate(([0.0], np.cumsum(count)))
    idx = np.arange(dg.T)
    if det.centered:
        lo = np.clip(idx - det.d // 2, 0, dg.T)
        hi = np.clip(idx + (det.d + 1) // 2, 0, dg.T)
    else:
        lo = np.clip(idx - det.d + 1, 0, dg.T)
        hi = idx + 1
    windowed = (cum[hi] - cum[lo]) / np.maximum(hi - lo, 1)
    armed = det.c_lo is not None or det.c_hi is not None
    c_lo = -np.inf if det.c_lo is None else det.c_lo
    c_hi = np.inf if det.c_hi is None else det.c_hi
    gate = armed & (windowed >= c_lo) & (windowed <= c_hi)
    return dg.Derived(m, count, windowed, np.asarray(gate, bool), armed)


def make_scalogram(pooled: np.ndarray) -> dg.ScalogramPlot:
    """Build a ScalogramPlot over a given pooled matrix (module-global swap;
    mockup-only)."""
    kept = dg.POOLED
    dg.POOLED = pooled
    try:
        return dg.ScalogramPlot()
    finally:
        dg.POOLED = kept


class HoverRow(si.ClickRow):
    """A ClickRow that also reports hover, so the wizard can live-preview."""

    hovered = Signal()

    def enterEvent(self, event: object) -> None:
        super().enterEvent(event)
        if self.usable:
            self.hovered.emit()


class VideoPanel(QWidget):
    """The wizard's picture: the frame with the provisional chain's spatial
    ops actually applied. Playback is mocked as a still."""

    def __init__(self, caption: str) -> None:
        super().__init__()
        self.image: QImage | None = None
        self.caption = caption
        self.setMinimumHeight(240)

    def set_image(self, image: QImage) -> None:
        self.image = image
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), dg.BG)
        if self.image is not None:
            r = QRectF(self.rect()).adjusted(0, 0, 0, -16)
            scale = min(r.width() / self.image.width(), r.height() / self.image.height())
            w, h = self.image.width() * scale, self.image.height() * scale
            target = QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h)
            painter.drawImage(target, self.image)
        painter.setPen(dg.DIM)
        painter.setFont(si._font(8))
        painter.drawText(
            QRectF(0, self.height() - 15, self.width(), 14),
            int(Qt.AlignmentFlag.AlignHCenter),
            f"{self.caption} - playing (mocked as a still), edited by the provisional chain",
        )


class StackCard(QWidget):
    """One step: a painted header over a body of real widgets."""

    def __init__(
        self,
        index: int,
        step: si.Step,
        status: si.Status,
        caption: str,
        provisional: bool = False,
    ) -> None:
        super().__init__()
        self.index = index
        self.step = step
        self.status = status
        self.caption = caption
        self.provisional = provisional
        self.hot = False

        conflicted = status.state == "conflict"
        header = HEADER_H + (CONFLICT_EXTRA if conflicted else 0)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, header, 14, 10)
        self.body.setSpacing(6)

        hover_css = (
            "QPushButton {background: transparent; color: #8b8e98; border: 1px solid"
            " transparent; border-radius: 4px; padding: 1px 8px; font-size: 8pt;}"
            "QPushButton:hover {color: #e6e7eb; border-color: #55583f;}"
        )
        self.swap_hover = QPushButton("swap", self)
        self.remove_hover = QPushButton("x", self)
        for btn in (self.swap_hover, self.remove_hover):
            btn.setVisible(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(hover_css)
        self.swap_hover.setToolTip("Replace this step")
        self.remove_hover.setToolTip("Remove this step")

        self.swap_btn = QPushButton("Swap…", self)
        self.remove_btn = QPushButton("Remove", self)
        for btn in (self.swap_btn, self.remove_btn):
            btn.setVisible(conflicted)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {background: #3a2c2c; color: #eb6e64; border: 1px solid #7a4640;"
                " border-radius: 4px; padding: 2px 10px; font-size: 8pt;}"
                "QPushButton:hover {background: #4a3432;}"
            )

    def resizeEvent(self, event: object) -> None:
        x = self.width() - 10 - self.remove_hover.sizeHint().width()
        self.remove_hover.move(x, 26)
        x -= 4 + self.swap_hover.sizeHint().width()
        self.swap_hover.move(x, 26)
        if self.status.state == "conflict":
            x = self.width() - 14 - self.remove_btn.sizeHint().width()
            self.remove_btn.move(x, HEADER_H + 2)
            x -= 8 + self.swap_btn.sizeHint().width()
            self.swap_btn.move(x, HEADER_H + 2)

    def enterEvent(self, event: object) -> None:
        self.hot = True
        if self.status.state != "conflict" and not self.provisional:
            self.swap_hover.setVisible(True)
            self.remove_hover.setVisible(True)
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hot = False
        self.swap_hover.setVisible(False)
        self.remove_hover.setVisible(False)
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        conflicted = self.status.state == "conflict"
        unreached = self.status.state == "unreached"

        painter.setBrush(si.PANEL_HI if (self.hot and not unreached) else si.PANEL)
        if self.provisional:
            pen = QPen(si.ACCENT, 1.2)
            pen.setStyle(Qt.PenStyle.DashLine)
        else:
            pen = QPen(si.CONFLICT if conflicted else si.LINE, 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 6, 6)
        if conflicted:
            painter.setBrush(si.CONFLICT)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), 3.5, rect.height()), 2, 2)

        text = QColor(si.TEXT)
        dim = QColor(si.DIM)
        if unreached:
            text.setAlpha(110)
            dim.setAlpha(90)
        painter.setPen(text)
        painter.setFont(si._font(10, bold=True))
        painter.drawText(QRectF(18, 8, rect.width() - 130, 18), 0, self.step.op.name)
        painter.setPen(dim)
        painter.setFont(si._font(8))
        painter.drawText(QRectF(18, 27, rect.width() - 130, 15), 0, self.caption)
        painter.drawText(
            QRectF(rect.width() - 96, 8, 84, 18),
            int(Qt.AlignmentFlag.AlignRight),
            f"{self.step.op.cost_ms:.1f} ms",
        )
        note = "provisional" if self.provisional else ("unreached" if unreached else "")
        if note:
            painter.setPen(si.ACCENT if self.provisional else dim)
            painter.drawText(
                QRectF(rect.width() - 130, 27, 118, 15),
                int(Qt.AlignmentFlag.AlignRight),
                note,
            )
        if conflicted:
            painter.setPen(si.CONFLICT)
            painter.drawText(
                QRectF(18, HEADER_H + 4, rect.width() - 200, 16),
                0,
                f"expects {self.step.op.accepts} · receiving {self.status.incoming}",
            )


class TabWindow(QWidget):
    """Left: where the signal is. Right: the chain, graphs embedded.
    Bottom: the seeker. Over it all, when choosing: the wizard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("filter tab - stack hosts the graphs")
        self.setStyleSheet(f"background: {dg.BG.name()}; color: {dg.TEXT.name()};")
        self.setMinimumSize(1380, 940)
        self.det = dg.Detector()
        self.steps: list[si.Step] = [
            si.Step(si.BY_NAME[name])
            for name in ("rescale", "normalize", JTT, "morlet band", "windowed count")
        ]
        #: (mode, index, op) while the wizard previews; op None before the
        #: first hover.
        self.provisional: tuple[str, int, si.Op | None] | None = None
        self.wizard: QFrame | None = None
        self.scrim: si.Scrim | None = None
        self.cards: list[StackCard] = []
        self.gaps: list[si.GapStrip] = []

        frame, self.frame_caption = dg.sample_frame()
        rgb = frame.convertToFormat(QImage.Format.Format_RGB888).scaledToWidth(
            560, Qt.TransformationMode.SmoothTransformation
        )
        raw = np.frombuffer(rgb.constBits().tobytes(), np.uint8)
        raw = raw.reshape(rgb.height(), rgb.bytesPerLine())[:, : rgb.width() * 3]
        self.base_small = raw.reshape(rgb.height(), rgb.width(), 3).astype(np.float32)

        self.heat = dg.BlockHeat(frame, self.frame_caption)
        self.count = dg.CountPlot()
        self.density = dg.DensityPlot()
        self.density.setMinimumHeight(160)
        self.scalo_stack = QStackedWidget()
        self.scalo_stack.setMinimumHeight(160)
        self.scalos = {name: make_scalogram(POOLEDS[name]) for name in (JTT, LK)}
        for plot in self.scalos.values():
            self.scalo_stack.addWidget(plot)

        # -- persistent step-parameter widgets (reparented into cards) ------
        field_css = (
            f"background: {dg.BG.name()}; color: {dg.TEXT.name()};"
            f" border: 1px solid {dg.LINE.name()}; border-radius: 4px; padding: 2px 4px;"
        )
        self._field_css = field_css
        self.downsample = QDoubleSpinBox()
        self.downsample.setRange(0.05, 1.0)
        self.downsample.setSingleStep(0.05)
        self.downsample.setDecimals(2)
        self.downsample.setValue(0.25)
        self.normalize = QComboBox()
        self.normalize.addItems(["off", "zscore"])
        self.normalize.setCurrentText("zscore")
        self.block = QSpinBox()
        self.block.setRange(0, 64)
        self.block.setValue(0)
        self.block.setSpecialValueText("auto (16)")
        for widget in (self.downsample, self.normalize, self.block):
            widget.setStyleSheet(field_css)
        self.signal_btns: dict[str, QPushButton] = {}
        for name, label in ((JTT, "change energy (Jtt)"), (LK, "LK optical flow")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{{field_css}}}"
                f"QPushButton:checked {{border-color: {dg.ACCENT.name()};"
                f" color: {dg.ACCENT.name()};}}"
            )
            btn.clicked.connect(lambda checked=False, n=name: self._on_signal(n))
            self.signal_btns[name] = btn
        self._param_widgets: list[QWidget] = [
            self.downsample,
            self.normalize,
            self.block,
            *self.signal_btns.values(),
        ]
        self._param_rows: list[QWidget] = []
        self.detect_note = QLabel("graph and detection window D live under the video")
        self.detect_note.setFont(si._font(8))
        self.detect_note.setStyleSheet(f"color: {dg.DIM.name()};")

        # -- left column ------------------------------------------------------
        self.d_slider = QSlider(Qt.Orientation.Horizontal)
        self.d_slider.setRange(1, 250)
        self.d_slider.setValue(self.det.d)
        self.d_label = QLabel()
        self.d_label.setFont(si._font(8))
        self.d_label.setStyleSheet(f"color: {dg.DIM.name()};")
        self.centered_box = QCheckBox("centered")
        self.centered_box.setChecked(True)
        self.centered_box.setFont(si._font(8))
        self.centered_box.setStyleSheet(f"color: {dg.DIM.name()};")
        self.summary = QLabel()
        self.summary.setFont(si._font(8))
        # The D row lives in one widget so the wizard can borrow it whole.
        self.d_row_host = QWidget()
        d_row = QHBoxLayout(self.d_row_host)
        d_row.setContentsMargins(0, 0, 0, 0)
        d_row.addWidget(self.d_label)
        d_row.addWidget(self.d_slider, 1)
        d_row.addWidget(self.centered_box)
        d_row.addWidget(self.summary)

        left = QVBoxLayout()
        left.addWidget(self.heat, 3)
        left.addWidget(self.count, 2)
        left.addWidget(self.d_row_host)
        self.left_layout = left

        # -- right column: the stack ------------------------------------------
        stack_head = QHBoxLayout()
        title = QLabel("LIVE CHAIN")
        title.setFont(si._font(8, bold=True, spaced=True))
        title.setStyleSheet(f"color: {dg.DIM.name()};")
        stack_head.addWidget(title)
        stack_head.addStretch(1)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setStyleSheet(
            f"QPushButton {{{field_css}}} QPushButton:hover {{border-color: {dg.DIM.name()};}}"
        )
        stack_head.addWidget(self.reset_btn)

        self.stack_host = QWidget()
        self.stack_area = QVBoxLayout(self.stack_host)
        self.stack_area.setContentsMargins(0, 0, 6, 0)
        self.stack_area.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.stack_host)
        scroll.setStyleSheet(
            "QScrollArea {border: none; background: transparent;}"
            "QScrollArea > QWidget > QWidget {background: transparent;}"
            "QScrollBar:vertical {background: transparent; width: 6px; margin: 0;}"
            f"QScrollBar::handle:vertical {{background: {dg.LINE.name()}; border-radius: 3px;"
            " min-height: 24px;}}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: none;}"
        )

        right = QVBoxLayout()
        right.addLayout(stack_head)
        right.addWidget(scroll, 1)

        # -- assembly ----------------------------------------------------------
        self.seeker = sb.SeekerBar("lanes")
        self.seeker.strip.window = TAB_WINDOW
        self.seeker._sync(None)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addLayout(left, 5)
        top.addLayout(right, 6)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 6)
        outer.setSpacing(8)
        outer.addLayout(top, 1)
        outer.addWidget(self.seeker)

        # -- wiring -------------------------------------------------------------
        for scalo in self.scalos.values():
            scalo.band_changed.connect(lambda lo, hi: self._on_band("freq", lo, hi, False))
            scalo.band_committed.connect(lambda lo, hi: self._on_band("freq", lo, hi, True))
            scalo.scrubbed.connect(self._on_graph_scrub)
        self.density.band_changed.connect(lambda lo, hi: self._on_band("value", lo, hi, False))
        self.density.band_committed.connect(lambda lo, hi: self._on_band("value", lo, hi, True))
        self.density.scrubbed.connect(self._on_graph_scrub)
        self.count.band_changed.connect(lambda lo, hi: self._on_band("count", lo, hi, False))
        self.count.band_committed.connect(lambda lo, hi: self._on_band("count", lo, hi, True))
        self.count.scrubbed.connect(self._on_graph_scrub)
        self.heat.solo_toggled.connect(self._on_solo)
        self.d_slider.valueChanged.connect(self._on_d)
        self.centered_box.toggled.connect(self._on_centered)
        self.reset_btn.clicked.connect(self._on_reset)
        self.downsample.valueChanged.connect(self._on_param)
        self.block.valueChanged.connect(self._on_param)
        self.normalize.currentTextChanged.connect(lambda _t: self._on_param())
        self.seeker.strip.sought.disconnect(self.seeker._on_seek)
        self.seeker.strip.sought.connect(self._on_seeker_seek)

        self._rebuild_stack()
        self._apply()

    # -- displayed chain (real steps + the provisional one) -------------------

    def _displayed(self) -> tuple[list[si.Step], int | None]:
        steps = list(self.steps)
        if self.provisional is None or self.provisional[2] is None:
            return steps, None
        mode, index, op = self.provisional
        if mode == "insert":
            steps.insert(index, si.Step(op))
        else:
            steps[index] = si.Step(op)
        return steps, index

    def _signal_name(self) -> str | None:
        steps, _ = self._displayed()
        statuses = si.grade(steps)
        for step, status in zip(steps, statuses, strict=True):
            if step.op.name in CUBES and status.state == "ok":
                return step.op.name
        return None

    def _step_ok(self, name: str) -> bool:
        steps, _ = self._displayed()
        statuses = si.grade(steps)
        return any(
            step.op.name == name and status.state == "ok"
            for step, status in zip(steps, statuses, strict=True)
        )

    def _effects(self) -> list[str]:
        steps, _ = self._displayed()
        statuses = si.grade(steps)
        return [
            step.op.name
            for step, status in zip(steps, statuses, strict=True)
            if status.state == "ok" and step.op.name in SERIES_EFFECTS
        ]

    def _caption_for(self, op: si.Op) -> str:
        if op.name == "rescale":
            return f"scale {self.downsample.value():.2f} · area"
        if op.name == "normalize":
            return f"{self.normalize.currentText()}"
        if op.name in CUBES:
            block = self.block.value()
            return f"block {'auto (16)' if block == 0 else block}"
        if op.name == "morlet band":
            i, j = self.det.freq_indices()
            return f"band {dg.FREQS[i]:.2f}-{dg.FREQS[j]:.2f} Hz"
        if op.name == "windowed count":
            thr = "off" if self.det.c_lo is None else f">= {self.det.c_lo:.0f}"
            return f"D {self.det.d} fr · threshold {thr}"
        return si.CAPTIONS.get(op.name, "")

    # -- the provisional video --------------------------------------------------

    def _video_image(self) -> QImage:
        """The frame with every reachable image-stage op actually applied."""
        img = self.base_small.copy()
        h, w, _ = img.shape
        steps, _ = self._displayed()
        statuses = si.grade(steps)
        for step, status in zip(steps, statuses, strict=True):
            if status.state != "ok" or step.op.emits != si.IMAGE:
                continue
            name = step.op.name
            if name == "rescale":
                k = max(1, round(1.0 / self.downsample.value()))
                small = img[::k, ::k]
                img = np.repeat(np.repeat(small, k, axis=0), k, axis=1)[:h, :w]
                if img.shape[0] < h or img.shape[1] < w:
                    img = np.pad(
                        img, ((0, h - img.shape[0]), (0, w - img.shape[1]), (0, 0)), mode="edge"
                    )
            elif name == "normalize" and self.normalize.currentText() == "zscore":
                mean, std = float(img.mean()), float(img.std()) or 1.0
                img = (img - mean) * (48.0 / std) + 128.0
            elif name == "background subtract":
                img = img - _box_blur(img, 15) + 128.0
            elif name == "denoise":
                img = _box_blur(img, 5)
        out = np.clip(img, 0, 255).astype(np.uint8)
        return QImage(out.tobytes(), w, h, w * 3, QImage.Format.Format_RGB888).copy()

    # -- stack construction -----------------------------------------------------

    def _detach_persistent(self) -> None:
        """Pull long-lived widgets out before their host cards are deleted.

        The knobs must leave their row containers FIRST: a parentless PySide
        widget dies with its Python reference, and it takes its children
        with it.
        """
        for widget in (*self._param_widgets, self.scalo_stack, self.density, self.detect_note):
            widget.setParent(None)
        for row in self._param_rows:
            row.setParent(None)
            row.deleteLater()
        self._param_rows = []

    def _param_row(self, label: str, *widgets: QWidget) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        tag = QLabel(label)
        tag.setFont(si._font(8))
        tag.setStyleSheet(f"color: {dg.DIM.name()};")
        layout.addWidget(tag)
        for widget in widgets:
            layout.addWidget(widget)
        layout.addStretch(1)
        self._param_rows.append(row)
        return row

    def _settings_rows(self, name: str) -> list[QWidget]:
        """The operation's own settings, as rows of the persistent widgets."""
        if name == "rescale":
            return [self._param_row("Downsample", self.downsample)]
        if name == "normalize":
            return [self._param_row("Normalize", self.normalize)]
        if name in CUBES:
            for btn_name, btn in self.signal_btns.items():
                btn.setChecked(btn_name == name)
            return [
                self._param_row("Block", self.block),
                self._param_row("signal", *self.signal_btns.values()),
            ]
        return []

    def _fill_body(self, card: StackCard, taken: set[str]) -> None:
        name = card.step.op.name
        if card.status.state != "ok":
            return
        prov_op = self.provisional[2] if self.provisional else None
        wizard_owns = (
            prov_op is not None
            and not card.provisional
            and (name == prov_op.name or (name in CUBES and prov_op.name in CUBES))
        )
        if card.provisional or wizard_owns:
            note = QLabel("configuring in the helper")
            note.setFont(si._font(8))
            color = dg.ACCENT.name() if card.provisional else dg.DIM.name()
            note.setStyleSheet(f"color: {color};")
            self._param_rows.append(note)
            card.body.addWidget(note)
            return
        key = "extraction" if name in CUBES else name
        if key in taken:
            return
        if name == "morlet band":
            signal = self._signal_name()
            if signal is not None:
                self.scalo_stack.setCurrentWidget(self.scalos[signal])
                card.body.addWidget(self.scalo_stack)
                if self.wizard is None:  # the wizard borrows the density plot
                    card.body.addWidget(self.density)
            taken.add(key)
            return
        if name == "windowed count":
            card.body.addWidget(self.detect_note)
            taken.add(key)
            return
        rows = self._settings_rows(name)
        if rows:
            for row in rows:
                card.body.addWidget(row)
            taken.add(key)

    def _rebuild_stack(self) -> None:
        self._detach_persistent()
        while self.stack_area.count():
            item = self.stack_area.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.cards, self.gaps = [], []

        steps, provisional_index = self._displayed()
        statuses = si.grade(steps)
        cards: list[StackCard] = []
        seen: set[str] = set()
        for i, (step, status) in enumerate(zip(steps, statuses, strict=True)):
            gap = si.GapStrip(i)
            gap.clicked.connect(self._on_gap)
            self.stack_area.addWidget(gap)
            self.gaps.append(gap)
            if step.op.category not in seen:
                seen.add(step.op.category)
                self.stack_area.addWidget(self._stage_label(step.op))
            card = StackCard(
                i, step, status, self._caption_for(step.op), provisional=i == provisional_index
            )
            card.swap_hover.clicked.connect(
                lambda checked=False, k=i: self._open_wizard("replace", k)
            )
            card.swap_btn.clicked.connect(
                lambda checked=False, k=i: self._open_wizard("replace", k)
            )
            card.remove_hover.clicked.connect(lambda checked=False, k=i: self._remove(k))
            card.remove_btn.clicked.connect(lambda checked=False, k=i: self._remove(k))
            self.stack_area.addWidget(card)
            cards.append(card)
        self.cards = cards
        self.stack_area.addStretch(1)

        taken: set[str] = set()
        for card in cards:
            self._fill_body(card, taken)

    def _stage_label(self, op: si.Op) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 8, 2, 3)
        title = QLabel(si.STAGE_TITLES[op.category])
        title.setFont(si._font(8, bold=True, spaced=True))
        title.setStyleSheet(f"color: {dg.DIM.name()};")
        layout.addWidget(title)
        layout.addStretch(1)
        chip = QLabel(f"{op.accepts} → {op.emits}" if op.accepts != op.emits else op.accepts)
        chip.setFont(si._font(8))
        chip.setStyleSheet(f"color: {dg.DIM.name()};")
        layout.addWidget(chip)
        return row

    def _refresh_captions(self) -> None:
        for card in self.cards:
            card.caption = self._caption_for(card.step.op)
            card.update()

    # -- the wizard ---------------------------------------------------------------

    def _wizard_candidates(self, mode: str, index: int) -> list[tuple[si.Op, bool, str]]:
        """(op, enabled, reason). The wizard cannot break the chain: breakers
        and duplicates are visible but disabled, with the reason."""
        incoming = si.incoming_at(self.steps, index)
        if mode == "insert":
            below: si.Op | None = self.steps[index].op
        else:
            below = self.steps[index + 1].op if index + 1 < len(self.steps) else None
        present = {step.op.name for step in self.steps}
        if mode == "replace":
            present.discard(self.steps[index].op.name)
        out = []
        for op in si.REGISTRY:
            if op.accepts != incoming:
                continue
            if mode == "replace" and op.name == self.steps[index].op.name:
                continue
            if below is not None and below.accepts != op.emits:
                out.append((op, False, "breaks below"))
            elif op.name in present or (op.name in CUBES and present & set(CUBES)):
                out.append((op, False, "in chain"))
            else:
                out.append((op, True, ""))
        # The suggested category leads the list: the stage at the seam.
        anchor = self.steps[min(index, len(self.steps) - 1)].op.category
        order = [anchor] + [c for c in si.STAGE_TITLES if c != anchor]
        out.sort(key=lambda item: order.index(item[0].category))
        return out

    def _open_wizard(self, mode: str, index: int) -> None:
        if self.wizard is not None:
            return
        self.provisional = (mode, index, None)
        where = (
            f"insert above '{self.steps[index].op.name}'"
            if mode == "insert"
            else f"replace '{self.steps[index].op.name}'"
        )
        anchor = self.steps[min(index, len(self.steps) - 1)].op.category

        scrim = si.Scrim(self)
        scrim.setGeometry(self.rect())
        scrim.show()
        self.scrim = scrim

        wizard = QFrame(scrim)
        wizard.setStyleSheet(
            f"QFrame {{background: {dg.BG.name()}; border: 1px solid {dg.ACCENT.name()};"
            " border-radius: 10px;}"
            f"QLabel {{border: none; color: {dg.TEXT.name()};}}"
        )
        margin = 34
        wizard.setGeometry(self.rect().adjusted(margin, margin, -margin, -margin))
        layout = QHBoxLayout(wizard)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # -- left: the equivalents for this seam ---------------------------
        list_col = QVBoxLayout()
        list_col.setSpacing(6)
        title = QLabel(f"Operations — {where}")
        title.setFont(si._font(10, bold=True))
        list_col.addWidget(title)
        suggested = QLabel(f"suggested here: {si.STAGE_TITLES[anchor].lower()}")
        suggested.setFont(si._font(8))
        suggested.setStyleSheet(f"color: {dg.ACCENT.name()};")
        list_col.addWidget(suggested)
        search = QLineEdit()
        search.setPlaceholderText("search")
        search.setStyleSheet(
            f"QLineEdit {{background: {dg.PANEL.name()}; color: {dg.TEXT.name()};"
            f" border: 1px solid {dg.LINE.name()}; border-radius: 5px; padding: 5px 8px;}}"
        )
        list_col.addWidget(search)
        rows_host = QWidget()
        self._wizard_list = QVBoxLayout(rows_host)
        self._wizard_list.setContentsMargins(0, 0, 0, 0)
        self._wizard_list.setSpacing(2)
        rows_scroll = QScrollArea()
        rows_scroll.setWidgetResizable(True)
        rows_scroll.setStyleSheet(
            "QScrollArea {border: none; background: transparent;}"
            "QScrollArea > QWidget > QWidget {background: transparent;}"
        )
        rows_scroll.setWidget(rows_host)
        list_col.addWidget(rows_scroll, 1)
        hint = QLabel("hover to try - the whole tab previews it")
        hint.setFont(si._font(8))
        hint.setStyleSheet(f"color: {dg.DIM.name()};")
        list_col.addWidget(hint)
        left_host = QWidget()
        left_host.setLayout(list_col)
        left_host.setFixedWidth(280)
        left_host.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(left_host)

        # -- center: the two things you watch (video over graph) -------------
        center = QVBoxLayout()
        center.setSpacing(8)
        self._wizard_video = VideoPanel(self.frame_caption)
        center.addWidget(self._wizard_video, 3)
        self._wizard_graph_slot = QVBoxLayout()
        center.addLayout(self._wizard_graph_slot, 2)
        self._wizard_count_slot = QVBoxLayout()
        self._wizard_count_slot.setSpacing(4)
        center.addLayout(self._wizard_count_slot, 2)
        layout.addLayout(center, 1)

        # -- right: what you read and tweak (settings over guidance) ---------
        side = QVBoxLayout()
        side.setSpacing(8)
        settings_head = QLabel("SETTINGS")
        settings_head.setFont(si._font(8, bold=True, spaced=True))
        settings_head.setStyleSheet(f"color: {dg.DIM.name()};")
        side.addWidget(settings_head)
        self._wizard_settings = QVBoxLayout()
        self._wizard_settings.setSpacing(4)
        side.addLayout(self._wizard_settings)
        self._wizard_md = QLabel()
        self._wizard_md.setWordWrap(True)
        self._wizard_md.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._wizard_md.setFont(si._font(9))
        self._wizard_md.setStyleSheet(
            f"background: {dg.PANEL.name()}; border: 1px solid {dg.LINE.name()};"
            " border-radius: 6px; padding: 10px;"
        )
        side.addWidget(self._wizard_md, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(
            f"QPushButton {{background: {dg.PANEL.name()}; color: {dg.TEXT.name()};"
            f" border: 1px solid {dg.LINE.name()}; border-radius: 5px; padding: 6px 16px;}}"
        )
        cancel.clicked.connect(self._wizard_cancel)
        buttons.addWidget(cancel)
        self._wizard_add = QPushButton("Add")
        self._wizard_add.setEnabled(False)
        self._wizard_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wizard_add.setStyleSheet(
            f"QPushButton {{background: {dg.ACCENT.name()}; color: #10201c; border: none;"
            " border-radius: 5px; padding: 6px 22px; font-weight: bold;}}"
            "QPushButton:disabled {background: #33413e; color: #6a7a76;}"
        )
        self._wizard_add.clicked.connect(self._wizard_commit)
        buttons.addWidget(self._wizard_add)
        side.addLayout(buttons)
        side_host = QWidget()
        side_host.setLayout(side)
        side_host.setFixedWidth(330)
        side_host.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(side_host)

        self.wizard = wizard
        self._wizard_ctx = (mode, index)
        search.textChanged.connect(lambda _t: self._wizard_populate())
        self._wizard_search = search
        self._wizard_populate()
        self._wizard_md.setText(
            f"<span style='color:{dg.DIM.name()}'>Hover an operation to try it: the video,"
            " the graph, the chain, and the detections all preview it live. Its settings"
            " appear on the left of this pane to tune before you commit. Add keeps it;"
            " Cancel or Esc puts everything back.</span>"
        )
        wizard.show()
        self._rebuild_stack()
        self._apply()
        self._wizard_sync()
        self._narrate(f"{where} - hover to preview")

    def _wizard_populate(self) -> None:
        mode, index = self._wizard_ctx
        while self._wizard_list.count():
            item = self._wizard_list.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        needle = self._wizard_search.text().lower() if hasattr(self, "_wizard_search") else ""
        rows: list[HoverRow] = []
        last_category = None
        for op, enabled, reason in self._wizard_candidates(mode, index):
            if needle and needle not in (op.name + op.blurb).lower():
                continue
            if op.category != last_category:
                last_category = op.category
                header = QLabel(si.STAGE_TITLES[op.category])
                header.setFont(si._font(7, bold=True, spaced=True))
                header.setStyleSheet(f"color: {dg.DIM.name()};")
                header.setContentsMargins(4, 6, 0, 1)
                self._wizard_list.addWidget(header)
            row = HoverRow(
                op.name,
                op.blurb,
                badge=reason,
                badge_color=si.CONFLICT if reason == "breaks below" else si.WARN,
                enabled=enabled,
            )
            if enabled:
                row.hovered.connect(lambda o=op: self._wizard_select(o))
                row.picked.connect(lambda o=op, r=row: self._wizard_pick(o, r))
            rows.append(row)
            self._wizard_list.addWidget(row)
        self._wizard_list.addStretch(1)
        self._wizard_rows = rows

    def _wizard_select(self, op: si.Op) -> None:
        mode, index = self._wizard_ctx
        self.provisional = (mode, index, op)
        self._wizard_add.setEnabled(True)
        self._wizard_md.setText(
            f"<b>{op.name}</b><br>"
            f"<span style='color:{dg.DIM.name()}'>{op.accepts} → {op.emits}"
            f" · {op.cost_ms:.1f} ms/frame</span><br><br>"
            f"<b>When to use it</b><br>{op.when}<br><br>"
            f"<b>What it does not do</b><br>{op.avoid}"
        )
        self._rebuild_stack()
        self._apply()
        self._wizard_sync()

    def _wizard_pick(self, op: si.Op, row: HoverRow) -> None:
        for other in self._wizard_rows:
            other.selected = other is row
            other.update()
        self._wizard_select(op)

    def _wizard_sync(self) -> None:
        """After any rebuild while the wizard is open: give it the video,
        the graph, and the provisional op's settings."""
        if self.wizard is None:
            return
        self._wizard_video.set_image(self._video_image())
        if self.density.parent() is None:
            self._wizard_graph_slot.addWidget(self.density)
        if self.count.parent() is not self.wizard:
            # The detection graph and its D row move into the wizard whole:
            # a candidate is usually judged by what it does to the green.
            self._wizard_count_slot.addWidget(self.count)
            self._wizard_count_slot.addWidget(self.d_row_host)
        while self._wizard_settings.count():
            item = self._wizard_settings.takeAt(0)
            widget = item.widget()
            if widget is not None and widget not in self._param_widgets:
                widget.deleteLater()
        op = self.provisional[2] if self.provisional else None
        if op is None:
            return
        rows = self._settings_rows(op.name)
        if not rows:
            note = QLabel("this operation has no settings in the mockup")
            note.setFont(si._font(8))
            note.setStyleSheet(f"color: {dg.DIM.name()};")
            self._param_rows.append(note)
            rows = [note]
        for row in rows:
            self._wizard_settings.addWidget(row)

    def _wizard_commit(self) -> None:
        if self.provisional is None or self.provisional[2] is None:
            return
        mode, index, op = self.provisional
        if mode == "insert":
            self.steps.insert(index, si.Step(op))
        else:
            self.steps[index] = si.Step(op)
        self._wizard_close(f"added '{op.name}' -> replan extraction")

    def _wizard_cancel(self) -> None:
        self._wizard_close("cancelled - chain unchanged")

    def _wizard_close(self, message: str) -> None:
        self.provisional = None
        if self.wizard is not None:
            # Reclaim the borrowed detection views before the wizard dies,
            # or they die with it.
            self.count.setParent(None)
            self.d_row_host.setParent(None)
            self.left_layout.insertWidget(1, self.count, 2)
            self.left_layout.insertWidget(2, self.d_row_host)
            self.wizard.deleteLater()
            self.wizard = None
        if self.scrim is not None:
            self.scrim.deleteLater()
            self.scrim = None
        self._narrate(message)
        self._rebuild_stack()
        self._apply()

    # -- stack event entries ------------------------------------------------------

    def _on_gap(self, seam: int) -> None:
        if self.wizard is None:
            self._open_wizard("insert", seam)

    def _remove(self, index: int) -> None:
        if self.wizard is not None:
            return
        name = self.steps[index].op.name
        del self.steps[index]
        self._narrate(f"removed '{name}'")
        self._rebuild_stack()
        self._apply()

    def _on_signal(self, name: str) -> None:
        for i, step in enumerate(self.steps):
            if step.op.name in CUBES:
                self.steps[i] = si.Step(si.BY_NAME[name])
                self._narrate(f"swap block signal -> {name.split('· ')[-1]} (bands kept)")
                break
        else:
            # the quick-switch pressed on a provisional extraction in the wizard
            if self.provisional is not None:
                mode, index, _op = self.provisional
                self.provisional = (mode, index, si.BY_NAME[name])
        self._rebuild_stack()
        self._apply()
        self._wizard_sync()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self.wizard is not None:
            self._wizard_cancel()

    def resizeEvent(self, event: object) -> None:
        if self.scrim is not None:
            self.scrim.setGeometry(self.rect())
        if self.wizard is not None:
            margin = 34
            self.wizard.setGeometry(self.rect().adjusted(margin, margin, -margin, -margin))

    # -- graph/detector plumbing ----------------------------------------------------

    @property
    def cube(self) -> np.ndarray | None:
        name = self._signal_name()
        return None if name is None else CUBES[name]

    def _narrate(self, text: str) -> None:
        self.seeker.narration.setText(text)

    def _graph_to_asset(self, frame: int) -> int:
        w0, w1 = self.seeker.strip.window
        return int(w0 + frame / max(dg.T - 1, 1) * (w1 - w0))

    def _asset_to_graph(self, frame: int) -> int:
        w0, w1 = self.seeker.strip.window
        frac = (np.clip(frame, w0, w1) - w0) / max(w1 - w0, 1)
        return int(frac * (dg.T - 1))

    def _apply(self) -> None:
        det = self.det
        cube = self.cube
        chain_runs = cube is not None and self._step_ok("morlet band")
        broken = cube is None or not chain_runs
        derived = dg.Derived() if broken else derive_from(cube, det, self._effects())
        for name, scalo in self.scalos.items():
            scalo.set_band(det.f_lo, det.f_hi)
            scalo.playhead = det.playhead
            i, j = det.freq_indices()
            scalo.readout = f"band {dg.FREQS[i]:.2f}-{dg.FREQS[j]:.2f} Hz - {name.split('· ')[-1]}"
        self.density.set_band(det.v_lo, det.v_hi)
        self.density.playhead = det.playhead
        self.density.set_matrix(derived.band_power, det.solo)
        self.density.readout = (
            f"value {self.density.fmt(det.v_lo, 'lo')}-{self.density.fmt(det.v_hi, 'hi')}"
        )
        detector_ok = self._step_ok("windowed count") and chain_runs
        self.count.set_band(det.c_lo, det.c_hi)
        self.count.playhead = det.playhead
        self.count.set_series(derived.windowed, derived.gate, derived.armed and detector_ok)
        self.count.readout = "" if detector_ok else "no reachable 'windowed count' step"

        v_lo = -np.inf if det.v_lo is None else det.v_lo
        v_hi = np.inf if det.v_hi is None else det.v_hi
        now = derived.band_power[det.playhead]
        self.heat.set_state(now, (now >= v_lo) & (now <= v_hi), det.solo)

        self.d_label.setText(f"D {det.d} fr ({det.d / dg.FPS:.2f} s)")
        if not chain_runs or not detector_ok:
            self.summary.setText("chain incomplete - see the stack")
            self.summary.setStyleSheet(f"color: {si.CONFLICT.name()};")
        elif derived.armed:
            spans = int(np.count_nonzero(np.diff(np.r_[0, derived.gate.view(np.int8)]) == 1))
            seconds = float(derived.gate.sum()) / dg.FPS
            self.summary.setText(f"{spans} detections - {seconds:.1f} s")
            self.summary.setStyleSheet(f"color: {dg.DETECT.name()};")
        else:
            self.summary.setText("disarmed - place the count threshold")
            self.summary.setStyleSheet(f"color: {dg.DIM.name()};")

        self._refresh_captions()
        self.seeker.strip.playhead = self._graph_to_asset(det.playhead)
        self.seeker._sync(None)
        for widget in (self.count, self.density, self.heat, self.scalo_stack.currentWidget()):
            if widget is not None:
                widget.update()

    # -- handlers ---------------------------------------------------------------

    def _on_band(self, which: str, lo, hi, committed: bool) -> None:
        if which == "freq":
            self.det.f_lo, self.det.f_hi = lo, hi
        elif which == "value":
            self.det.v_lo, self.det.v_hi = lo, hi
        else:
            self.det.c_lo, self.det.c_hi = lo, hi
        tier = "committed - rebuild deferred work" if committed else "dragging - cheap re-derive"
        self._narrate(f"{which} band -> {tier}")
        self._apply()

    def _on_graph_scrub(self, frame: int) -> None:
        self.det.playhead = frame
        self._narrate(f"scrub (graph) -> {frame / dg.FPS:.2f} s in window")
        self._apply()

    def _on_seeker_seek(self, frame: int, phase: str) -> None:
        self.det.playhead = self._asset_to_graph(frame)
        self.seeker.strip.playhead = frame
        verb = {"press": "seek (commit)", "scrub": "scrub (guess)", "commit": "release (commit)"}
        self._narrate(f"{verb[phase]} -> {sb.timecode(frame)}")
        self._apply()

    def _on_solo(self, block) -> None:
        self.det.solo = block
        label = "off" if block is None else f"block ({block // dg.GRID[1]},{block % dg.GRID[1]})"
        self._narrate(f"solo -> {label}")
        self._apply()

    def _on_param(self, *_args) -> None:
        self._narrate("parameter -> replan extraction (coalesced)")
        self._refresh_captions()
        if self.wizard is not None:
            self._wizard_video.set_image(self._video_image())

    def _on_d(self, value: int) -> None:
        self.det.d = value
        self._narrate(f"D -> {value} fr (instant)")
        self._apply()

    def _on_centered(self, checked: bool) -> None:
        self.det.centered = checked
        self._apply()

    def _on_reset(self) -> None:
        self.det = dg.Detector(playhead=self.det.playhead)
        self.downsample.setValue(0.25)
        self.block.setValue(0)
        self.normalize.setCurrentText("zscore")
        self.d_slider.setValue(self.det.d)
        self.centered_box.setChecked(True)
        self._narrate("reset -> params to defaults, bands cleared, disarmed; the chain is kept")
        self._rebuild_stack()
        self._apply()


def apply_shot(window: TabWindow, shot: str) -> None:
    if shot in ("tuned", "lk", "wizard", "wizard-spatial"):
        window.det.f_lo, window.det.f_hi = 8.0, 16.0
        window.det.v_lo, window.det.v_hi = 1600.0, None
        window.det.c_lo, window.det.c_hi = 10.0, None
    if shot == "lk":
        window._on_signal(LK)
    elif shot == "wizard":
        window._rebuild_stack()
        window._apply()
        window._open_wizard("insert", 4)  # above 'windowed count'
        window._wizard_select(si.BY_NAME["median smooth"])
    elif shot == "wizard-spatial":
        window._rebuild_stack()
        window._apply()
        window._open_wizard("insert", 2)  # above the extraction
        window._wizard_select(si.BY_NAME["denoise"])
    elif shot == "conflict":
        window.steps.insert(1, si.Step(si.BY_NAME[LK]))
        window._rebuild_stack()
        window._apply()
    else:
        window._rebuild_stack()
        window._apply()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shot",
        choices=("none", "tuned", "lk", "conflict", "wizard", "wizard-spatial"),
        default="none",
    )
    parser.add_argument("--png", type=str, default="")
    parser.add_argument("--size", type=str, default="1460x960")
    args = parser.parse_args()

    app = QApplication([])
    window = TabWindow()
    width, height = (int(part) for part in args.size.split("x"))
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
