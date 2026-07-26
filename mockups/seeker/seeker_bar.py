"""The bottom seeker: one bar that carries scrub, window, coverage, detections.

The cross-tab timeline (gui/timeline_bar.py) currently shows the asset, the
working window, and a playhead. The target design in
docs/filter-tab-parity-plan.md loads more onto this one surface: the Length
control lives here, detections need to be findable from anywhere, and v1's
navigator strip proved that *coverage* - which spans have been examined, and
under which settings - is what keeps a 3-minute asset honest at a glance.
This mockup decides how much of that one bar can carry.

Two variants:

  lanes - a single strip. Signal bars fill it; coverage tints the bars
          (lit = examined with current settings, gray = examined under other
          settings, dark = never examined); detections are a green tick lane
          along the top edge; the working window is a bright bracket with
          corner handles and a header band.
  split - the same content in two stacked lanes: a thin status lane
          (detections + coverage blocks) above a clean scrub lane (signal +
          window + playhead). Nothing overlaps, at the cost of height.

Interaction rules being posed (the same in both variants):
  - press = seek (a commitment), move = scrub (a guess), release = commit -
    unchanged from gui/timeline_bar.py.
  - the window is directly manipulable: drag an edge handle to resize, drag
    the header band to move it whole; the Length spinbox and the bracket are
    two views of the same value and stay in lockstep.
  - detection ticks are floored to 1 px; |< and >| jump the playhead to the
    previous / next detection.
  - hovering shows a timecode bubble with the coverage state under the
    cursor; the bubble never blocks the strip (it floats above it).

Everything is fake: the signal, coverage spans, detections, and the palette.
The bar's job description is the decision; the skin is not.

Run:
    uv run python mockups/seeker/seeker_bar.py --variant lanes
    uv run python mockups/seeker/seeker_bar.py --variant split --shot hover --png out.png
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ---- palette (not the app's) -------------------------------------------------

BG = QColor(21, 22, 25)
PANEL = QColor(31, 33, 38)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
ACCENT = QColor(94, 200, 180)
DETECT = QColor(96, 210, 120)

#: Coverage states and their bar colors.
COVER_CURRENT = QColor(205, 210, 220)
COVER_OTHER = QColor(96, 100, 112)
COVER_NONE = QColor(52, 55, 62)

# ---- the fake asset ------------------------------------------------------------

FPS = 60.0
FRAMES = 10_800  # 3:00
WINDOW0 = (2_400, 3_000)
PLAYHEAD0 = 2_712

#: (start, end, state) - state: "current" | "other" | "none".
COVERAGE = (
    (0, 1400, "none"),
    (1400, 4600, "current"),
    (4600, 5200, "none"),
    (5200, 6900, "other"),
    (6900, 10_800, "none"),
)

#: Detection spans in frames; one is a single frame on purpose.
DETECTIONS = (
    (1710, 1770),
    (2140, 2260),
    (2705, 2790),
    (3480, 3495),
    (4210, 4211),
    (5600, 5720),
    (6280, 6350),
)


def synth_signal() -> np.ndarray:
    """Per-frame magnitude with structure, so log bar heights mean something."""
    rng = np.random.default_rng(5)
    x = np.exp(rng.normal(0.0, 0.5, FRAMES)).astype(np.float32)
    for lo, hi in DETECTIONS:
        pad = max((hi - lo) * 3, 90)
        a, b = max(lo - pad, 0), min(hi + pad, FRAMES)
        bump = np.sin(np.linspace(0, np.pi, b - a)) ** 2
        x[a:b] += bump * rng.uniform(6.0, 14.0)
    return x


SIGNAL = synth_signal()


def timecode(frame: float) -> str:
    seconds = frame / FPS
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}"


def coverage_at(frame: int) -> str:
    for lo, hi, state in COVERAGE:
        if lo <= frame < hi:
            return state
    return "none"


def _font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


# ---- the strip -----------------------------------------------------------------

EDGE_GRAB = 6
HEADER_BAND = 9


@dataclass
class Hover:
    x: float
    frame: int


class SeekerStrip(QWidget):
    """The drawable strip. Owns no truth: window/playhead are set in, drags
    signal out. `variant` only changes where things are painted."""

    sought = Signal(int, str)  # frame, phase: "press" | "scrub" | "commit"
    window_changed = Signal(int, int, bool)  # start, end, committed

    def __init__(self, variant: str) -> None:
        super().__init__()
        self.variant = variant
        self.window = WINDOW0
        self.playhead = PLAYHEAD0
        self.hover: Hover | None = None
        self._drag: str | None = None  # "seek" | "left" | "right" | "move"
        self._grab_offset = 0
        self.setMouseTracking(True)
        self.setFixedHeight(64 if variant == "lanes" else 78)

    # -- geometry ---------------------------------------------------------

    def lane_rects(self) -> tuple[QRect, QRect]:
        """(status lane, scrub lane). In `lanes` they coincide."""
        r = self.rect().adjusted(0, 2, 0, -2)
        if self.variant == "split":
            status = QRect(r.left(), r.top(), r.width(), 14)
            scrub = QRect(r.left(), r.top() + 17, r.width(), r.height() - 17)
            return status, scrub
        return r, r

    def x_of(self, frame: float) -> float:
        r = self.rect()
        return r.left() + frame / FRAMES * r.width()

    def frame_of(self, x: float) -> int:
        r = self.rect()
        return int(np.clip((x - r.left()) / max(r.width(), 1) * FRAMES, 0, FRAMES - 1))

    # -- input ------------------------------------------------------------

    def _hit(self, pos: QPointF) -> str:
        x_lo, x_hi = self.x_of(self.window[0]), self.x_of(self.window[1])
        _, scrub = self.lane_rects()
        if abs(pos.x() - x_lo) <= EDGE_GRAB:
            return "left"
        if abs(pos.x() - x_hi) <= EDGE_GRAB:
            return "right"
        in_header = scrub.top() <= pos.y() <= scrub.top() + HEADER_BAND
        if in_header and x_lo < pos.x() < x_hi:
            return "move"
        return "seek"

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        self._drag = self._hit(pos)
        if self._drag == "seek":
            self.sought.emit(self.frame_of(pos.x()), "press")
        elif self._drag == "move":
            self._grab_offset = self.frame_of(pos.x()) - self.window[0]
        self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        self.hover = Hover(pos.x(), self.frame_of(pos.x()))
        if self._drag == "seek":
            self.sought.emit(self.frame_of(pos.x()), "scrub")
        elif self._drag in ("left", "right", "move"):
            self._drag_window(pos.x(), committed=False)
        else:
            cursor = {
                "left": Qt.CursorShape.SizeHorCursor,
                "right": Qt.CursorShape.SizeHorCursor,
                "move": Qt.CursorShape.OpenHandCursor,
                "seek": Qt.CursorShape.PointingHandCursor,
            }[self._hit(pos)]
            self.setCursor(cursor)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        pos = event.position()
        if self._drag == "seek":
            self.sought.emit(self.frame_of(pos.x()), "commit")
        elif self._drag in ("left", "right", "move"):
            self._drag_window(pos.x(), committed=True)
        self._drag = None
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hover = None
        self.update()

    def _drag_window(self, x: float, *, committed: bool) -> None:
        frame = self.frame_of(x)
        start, end = self.window
        min_len = int(FPS)  # a window shorter than a second is a misclick
        if self._drag == "left":
            start = min(frame, end - min_len)
        elif self._drag == "right":
            end = max(frame, start + min_len)
        else:
            length = end - start
            start = int(np.clip(frame - self._grab_offset, 0, FRAMES - length))
            end = start + length
        self.window = (max(start, 0), min(end, FRAMES))
        self.window_changed.emit(*self.window, committed)

    # -- painting ------------------------------------------------------------

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PANEL)
        status, scrub = self.lane_rects()

        self._paint_bars(painter, scrub)
        if self.variant == "split":
            self._paint_status_lane(painter, status)
        else:
            self._paint_detection_ticks(painter, QRect(scrub.left(), scrub.top(), scrub.width(), 5))
        self._paint_window(painter, scrub)
        self._paint_playhead(painter, scrub)
        if self.hover is not None and self._drag is None:
            self._paint_bubble(painter, scrub)

    def _paint_bars(self, painter: QPainter, r: QRect) -> None:
        width = max(r.width(), 1)
        top_pad = 7 if self.variant == "lanes" else 2
        usable = r.height() - top_pad
        edges = np.linspace(0, FRAMES, width + 1).astype(int)
        log_all = np.log1p(SIGNAL)
        ceiling = float(log_all.max())
        painter.setPen(Qt.PenStyle.NoPen)
        for px in range(width):
            lo, hi = edges[px], max(edges[px + 1], edges[px] + 1)
            height = float(log_all[lo:hi].max()) / ceiling * usable
            state = coverage_at((lo + hi) // 2)
            color = {
                "current": COVER_CURRENT,
                "other": COVER_OTHER,
                "none": COVER_NONE,
            }[state]
            painter.fillRect(QRectF(r.left() + px, r.bottom() - height, 1, height), color)

    def _paint_detection_ticks(self, painter: QPainter, lane: QRect) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(DETECT)
        for lo, hi in DETECTIONS:
            x0, x1 = self.x_of(lo), self.x_of(hi)
            painter.drawRect(QRectF(x0, lane.top(), max(x1 - x0, 1.0), lane.height()))

    def _paint_status_lane(self, painter: QPainter, lane: QRect) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for lo, hi, state in COVERAGE:
            color = {
                "current": QColor(COVER_CURRENT),
                "other": QColor(COVER_OTHER),
                "none": QColor(COVER_NONE),
            }[state]
            color.setAlpha(70)
            x0, x1 = self.x_of(lo), self.x_of(hi)
            painter.fillRect(QRectF(x0, lane.top() + 8, x1 - x0, lane.height() - 8), color)
        painter.setBrush(DETECT)
        for lo, hi in DETECTIONS:
            x0, x1 = self.x_of(lo), self.x_of(hi)
            painter.drawRect(QRectF(x0, lane.top(), max(x1 - x0, 1.0), 6))

    def _paint_window(self, painter: QPainter, r: QRect) -> None:
        x0, x1 = self.x_of(self.window[0]), self.x_of(self.window[1])
        band = QColor(ACCENT)
        band.setAlpha(26)
        painter.fillRect(QRectF(x0, r.top(), x1 - x0, r.height()), band)
        header = QColor(ACCENT)
        header.setAlpha(90 if self._drag == "move" else 55)
        painter.fillRect(QRectF(x0, r.top(), x1 - x0, HEADER_BAND), header)
        pen = QPen(ACCENT, 2 if self._drag in ("left", "right") else 1.2)
        painter.setPen(pen)
        painter.drawLine(QPointF(x0, r.top()), QPointF(x0, r.bottom()))
        painter.drawLine(QPointF(x1, r.top()), QPointF(x1, r.bottom()))
        painter.setBrush(ACCENT)
        painter.setPen(Qt.PenStyle.NoPen)
        for x in (x0, x1):
            painter.drawRoundedRect(QRectF(x - 2.5, r.top(), 5, HEADER_BAND), 2, 2)

    def _paint_playhead(self, painter: QPainter, r: QRect) -> None:
        x = self.x_of(self.playhead)
        painter.setPen(QPen(TEXT, 1.2))
        painter.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
        painter.setBrush(TEXT)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(x - 4, r.top()),
                    QPointF(x + 4, r.top()),
                    QPointF(x, r.top() + 5),
                ]
            )
        )

    def _paint_bubble(self, painter: QPainter, r: QRect) -> None:
        assert self.hover is not None
        frame = self.hover.frame
        state = {
            "current": "examined - current settings",
            "other": "examined - OTHER settings",
            "none": "not examined",
        }[coverage_at(frame)]
        near = next((d for d in DETECTIONS if d[0] - 90 <= frame <= d[1] + 90), None)
        lines = [f"{timecode(frame)}  -  frame {frame:,}", state]
        if near is not None:
            lines.append(f"detection {timecode(near[0])} - {(near[1] - near[0]) / FPS:.2f} s")
        painter.setFont(_font(8))
        metrics = painter.fontMetrics()
        w = max(metrics.horizontalAdvance(t) for t in lines) + 16
        h = len(lines) * 14 + 8
        x = float(np.clip(self.hover.x - w / 2, 4, self.width() - w - 4))
        box = QRectF(x, r.top() + 2, w, h)
        painter.setPen(QPen(LINE, 1))
        painter.setBrush(QColor(BG.red(), BG.green(), BG.blue(), 235))
        painter.drawRoundedRect(box, 4, 4)
        painter.setPen(TEXT)
        for i, text in enumerate(lines):
            color = DETECT if text.startswith("detection") else (TEXT if i == 0 else DIM)
            painter.setPen(color)
            painter.drawText(QRectF(box.left() + 8, box.top() + 4 + i * 14, w - 16, 14), 0, text)


# ---- the bar (strip + transport + Length) --------------------------------------


class SeekerBar(QWidget):
    def __init__(self, variant: str) -> None:
        super().__init__()
        self.strip = SeekerStrip(variant)
        self.playing = False

        self.play_btn = QPushButton("play")
        self.prev_btn = QPushButton("|<")
        self.next_btn = QPushButton(">|")
        for btn in (self.play_btn, self.prev_btn, self.next_btn):
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{background: {PANEL.name()}; color: {TEXT.name()};"
                f" border: 1px solid {LINE.name()}; border-radius: 4px; padding: 2px 10px;}}"
                f"QPushButton:hover {{border-color: {DIM.name()};}}"
            )
        self.prev_btn.setToolTip("Previous detection")
        self.next_btn.setToolTip("Next detection")

        self.length = QDoubleSpinBox()
        self.length.setSuffix(" s")
        self.length.setRange(1.0, FRAMES / FPS)
        self.length.setDecimals(1)
        self.length.setFixedWidth(84)
        self.length.setStyleSheet(
            f"QDoubleSpinBox {{background: {PANEL.name()}; color: {TEXT.name()};"
            f" border: 1px solid {LINE.name()}; border-radius: 4px; padding: 2px 4px;}}"
        )
        length_label = QLabel("Length")
        length_label.setFont(_font(8))
        length_label.setStyleSheet(f"color: {DIM.name()};")

        self.clock = QLabel()
        self.clock.setFont(_font(9))
        self.clock.setStyleSheet(f"color: {TEXT.name()};")

        self.narration = QLabel("press = seek - move = scrub - release = commit")
        self.narration.setFont(_font(8))
        self.narration.setStyleSheet(f"color: {DIM.name()};")

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.narration, 1)
        controls.addWidget(length_label)
        controls.addWidget(self.length)
        controls.addWidget(self.clock)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(5)
        outer.addWidget(self.strip)
        outer.addLayout(controls)

        self.strip.sought.connect(self._on_seek)
        self.strip.window_changed.connect(self._on_window)
        self.length.valueChanged.connect(self._on_length)
        self.play_btn.clicked.connect(self._on_play)
        self.prev_btn.clicked.connect(lambda: self._jump(-1))
        self.next_btn.clicked.connect(lambda: self._jump(+1))
        self._sync(narrate=None)

    def _sync(self, narrate: str | None) -> None:
        start, end = self.strip.window
        self.length.blockSignals(True)
        self.length.setValue((end - start) / FPS)
        self.length.blockSignals(False)
        self.clock.setText(
            f"{timecode(self.strip.playhead)} / {timecode(FRAMES)}"
            f"   frame {self.strip.playhead:,} / {FRAMES:,}"
        )
        if narrate:
            self.narration.setText(narrate)
        self.strip.update()

    def _on_seek(self, frame: int, phase: str) -> None:
        self.strip.playhead = frame
        verb = {"press": "seek (commit)", "scrub": "scrub (guess)", "commit": "release (commit)"}
        self._sync(f"{verb[phase]} -> {timecode(frame)}")

    def _on_window(self, start: int, end: int, committed: bool) -> None:
        tier = "committed - re-render" if committed else "dragging - outline only"
        self._sync(f"window {start:,}-{end:,} ({(end - start) / FPS:.1f} s) - {tier}")

    def _on_length(self, seconds: float) -> None:
        start, _ = self.strip.window
        end = min(start + int(seconds * FPS), FRAMES)
        self.strip.window = (start, end)
        self._sync(f"Length -> {seconds:.1f} s (window end follows; start pinned)")

    def _on_play(self) -> None:
        self.playing = not self.playing
        self.play_btn.setText("pause" if self.playing else "play")
        self._sync("play" if self.playing else "pause")

    def _jump(self, direction: int) -> None:
        head = self.strip.playhead
        if direction > 0:
            target = next((lo for lo, _ in DETECTIONS if lo > head), None)
        else:
            target = next((lo for lo, _ in reversed(DETECTIONS) if lo < head), None)
        if target is None:
            self._sync("no detection that way")
            return
        self.strip.playhead = target
        self._sync(f"jump to detection at {timecode(target)}")


class Stage(QWidget):
    """A dark stand-in for the app above the bar, so the bar reads in place."""

    def __init__(self, variant: str) -> None:
        super().__init__()
        self.setWindowTitle(f"seeker mockup - {variant}")
        self.setStyleSheet(f"background: {BG.name()};")
        self.bar = SeekerBar(variant)
        placeholder = QLabel("(the application)")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setFont(_font(9))
        placeholder.setStyleSheet(f"color: {LINE.name()};")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(placeholder, 1)
        outer.addWidget(self.bar)


def apply_shot(stage: Stage, shot: str) -> None:
    strip = stage.bar.strip
    if shot == "hover":
        strip.hover = Hover(strip.x_of(2740), 2740)
        strip.update()
    elif shot == "drag":
        strip._drag = "right"
        strip._drag_window(strip.x_of(4400), committed=False)
        strip._drag = None
        stage.bar._sync("window 2,400-4,400 (33.3 s) - dragging - outline only")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("lanes", "split"), default="lanes")
    parser.add_argument("--shot", choices=("none", "hover", "drag"), default="none")
    parser.add_argument("--png", type=str, default="")
    parser.add_argument("--size", type=str, default="1280x300")
    args = parser.parse_args()

    app = QApplication([])
    stage = Stage(args.variant)
    width, height = (int(part) for part in args.size.split("x"))
    stage.resize(width, height)
    stage.show()
    if args.shot != "none":
        apply_shot(stage, args.shot)
    if args.png:
        app.processEvents()
        stage.grab().save(args.png)
        return
    app.exec()


if __name__ == "__main__":
    main()
