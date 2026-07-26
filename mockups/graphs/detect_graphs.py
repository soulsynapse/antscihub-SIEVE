"""The graphs themselves: what each one shows, and what dragging it does.

docs/filter-tab-parity-plan.md names the widgets; this mockup makes them
drag-able against honest data, so the interaction decisions get made by hand
and not by argument. The synthetic signal is real math on fake footage: 64
blocks, three 12 Hz bursts in a 4x4 cluster, one single-frame spike, and a
true Morlet transform over all of it — so narrowing the frequency band
genuinely sharpens the density plot, and the spike genuinely dilutes as D
grows.

Variant `detect` — the detection surface (four linked views):

  scalogram      log-frequency Morlet heatmap, COI faded, two draggable
                 frequency handles (clamped to the bank's edges).
  band power     time x value density heatmap of all blocks, log1p value
                 axis, two draggable value handles (drag off the top = inf),
                 click a block in the spatial panel to trace it here.
  blocks in band the green graph: windowed count line, detection spans,
                 one draggable count threshold.
  block heat     the frame with the block grid over it, fill = band power at
                 the playhead, outline = in the value band; click to solo.

  Interaction rules being pinned:
  - drag anywhere on a plot scrubs the shared playhead; drags that start on
    a handle move the handle. Handles win within 8 px.
  - band drags emit continuously (cheap re-derive); release commits (the
    expensive tier). The footer names each event as it happens.
  - an unset count threshold means the detector is DISARMED and nothing is
    green - unset is not "everything is a detection". (Deliberate deviation
    from v1, where unset meant unbounded.)
  - gate spans are floored to 1 px so a single-frame detection is visible at
    any zoom; the green is a status color and never used for data series.

Variant `color` — the stretch goal: configuring a "detected color" channel
by pointing at the paused frame. Click = this color counts; Shift+click (or
right-click) = this color must not count. Samples become removable chips, a
tolerance slider widens the gate, and the mask repaints live on the frame.

Everything visual is fake-palette; the data flow is the real proposal.

Run:
    uv run python mockups/graphs/detect_graphs.py --variant detect
    uv run python mockups/graphs/detect_graphs.py --variant color
    uv run python mockups/graphs/detect_graphs.py --shot tuned --png out.png
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

REPO = Path(__file__).resolve().parents[2]

# ---- palette (not the app's; magnitude ramps sequential, green = status) ----

BG = QColor(21, 22, 25)
PANEL = QColor(31, 33, 38)
LINE = QColor(55, 58, 66)
TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)
ACCENT = QColor(94, 200, 180)
BAND = QColor(240, 110, 100)
DETECT = QColor(96, 210, 120)
WARN = QColor(224, 176, 96)

#: Warm sequential ramp for the scalogram (dark -> light, one family).
SCALO_STOPS = ((12, 8, 20), (86, 24, 48), (168, 60, 44), (226, 130, 56), (250, 214, 130))
#: Cyan sequential ramp for the block-density plot.
DENSITY_STOPS = ((21, 22, 25), (24, 56, 74), (32, 110, 138), (70, 180, 200), (190, 240, 248))

# ---- the fake recording ------------------------------------------------------

FPS = 50.0
T = 1500  # 30 s
GRID = (8, 8)
B = GRID[0] * GRID[1]
FREQS = np.geomspace(0.5, 22.5, 24)
W0 = 6.0
BURSTS = ((250, 400), (700, 850), (1100, 1300))
SPIKE_FRAME = 540
CLUSTER = [r * GRID[1] + c for r in range(2, 6) for c in range(2, 6)]


def synth_blocks() -> np.ndarray:
    """(T, B) block series: noise floor, 12 Hz bursts in a cluster, one spike."""
    rng = np.random.default_rng(11)
    x = np.exp(rng.normal(0.0, 0.35, (T, B))).astype(np.float32) * 30.0
    tt = np.arange(T) / FPS
    wave = 90.0 + 55.0 * np.sin(2 * np.pi * 12.0 * tt)
    for lo, hi in BURSTS:
        ramp = np.sin(np.linspace(0, np.pi, hi - lo)) ** 2
        for b in CLUSTER:
            x[lo:hi, b] += wave[lo:hi] * ramp * rng.uniform(0.6, 1.0)
    x[SPIKE_FRAME, :] += 420.0
    return x


def morlet_power(x: np.ndarray) -> np.ndarray:
    """|CWT|^2 over FREQS. (T,) -> (F, T); (T, B) -> (F, T, B). numpy-only."""
    n = 4096
    scales = (W0 + math.sqrt(2.0 + W0 * W0)) / (4.0 * math.pi * FREQS)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=1.0 / FPS)
    spectrum = np.fft.fft(x, n=n, axis=0)
    out_shape = (len(FREQS), *x.shape)
    power = np.empty(out_shape, dtype=np.float32)
    for i, s in enumerate(scales):
        daughter = (
            math.sqrt(2.0 * math.pi * s * FPS)
            * math.pi**-0.25
            * np.exp(-0.5 * (s * omega - W0) ** 2)
            * (omega > 0)
        )
        shaped = daughter.reshape((n,) + (1,) * (x.ndim - 1))
        w = np.fft.ifft(spectrum * shaped, axis=0)[:T]
        power[i] = (np.abs(w) ** 2).astype(np.float32)
    return power


def coi_samples(f_hz: float) -> float:
    """Cone-of-influence e-folding width at f, in samples."""
    return 1.369 / f_hz * FPS


BLOCKS = synth_blocks()
CUBE = morlet_power(BLOCKS)  # (F, T, B)
POOLED = morlet_power(BLOCKS.mean(axis=1))  # (F, T)


def sample_frame() -> tuple[QImage, str]:
    """A real frame if footage exists, else a drawn stand-in with color blobs."""
    videos = sorted((REPO / "videos-testing").glob("*.MP4"))
    if videos:
        try:
            from sieve.decode.reader import VideoReader

            with VideoReader(videos[0]) as reader:
                frame = reader.read(2712, max_width=1024)
            image = QImage(
                frame.data.tobytes(),
                frame.width,
                frame.height,
                frame.width * 3,
                QImage.Format.Format_BGR888,
            )
            return image.copy(), videos[0].name
        except Exception:
            pass
    width, height = 960, 540
    rng = np.random.default_rng(3)
    canvas = np.full((height, width, 3), (48, 44, 40), dtype=np.uint8)
    for _ in range(26):
        cx, cy = rng.integers(0, width), rng.integers(0, height)
        radius = int(rng.integers(18, 60))
        color = rng.integers(40, 230, 3)
        yy, xx = np.ogrid[:height, :width]
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 < radius * radius
        canvas[mask] = color
    image = QImage(canvas.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888)
    return image.copy(), "generated - no footage in videos-testing/"


# ---- detector state (plain data; plots render it, they never own it) --------


@dataclass
class Detector:
    f_lo: float | None = None  # Hz; None = bank edge
    f_hi: float | None = None
    v_lo: float | None = None  # band-power value; None = unbounded
    v_hi: float | None = None
    c_lo: float | None = None  # blocks; None = detector disarmed
    c_hi: float | None = None
    d: int = 25
    centered: bool = True
    playhead: int = 320
    solo: int | None = None

    def freq_indices(self) -> tuple[int, int]:
        lo = FREQS[0] if self.f_lo is None else self.f_lo
        hi = FREQS[-1] if self.f_hi is None else self.f_hi
        i = int(np.searchsorted(FREQS, lo))
        j = int(np.searchsorted(FREQS, hi, side="right")) - 1
        i = min(max(i, 0), len(FREQS) - 1)
        j = min(max(j, i), len(FREQS) - 1)
        return i, j


@dataclass
class Derived:
    band_power: np.ndarray = field(default_factory=lambda: np.zeros((T, B), np.float32))
    count: np.ndarray = field(default_factory=lambda: np.zeros(T, np.float32))
    windowed: np.ndarray = field(default_factory=lambda: np.zeros(T, np.float32))
    gate: np.ndarray = field(default_factory=lambda: np.zeros(T, bool))
    armed: bool = False


def derive(det: Detector) -> Derived:
    """The whole chain, pure: cube -> band power -> count -> windowed -> gate."""
    i, j = det.freq_indices()
    m = CUBE[i : j + 1].sum(axis=0)
    v_lo = -np.inf if det.v_lo is None else det.v_lo
    v_hi = np.inf if det.v_hi is None else det.v_hi
    count = ((m >= v_lo) & (m <= v_hi)).sum(axis=1).astype(np.float32)
    cum = np.concatenate(([0.0], np.cumsum(count)))
    idx = np.arange(T)
    if det.centered:
        lo = np.clip(idx - det.d // 2, 0, T)
        hi = np.clip(idx + (det.d + 1) // 2, 0, T)
    else:
        lo = np.clip(idx - det.d + 1, 0, T)
        hi = idx + 1
    windowed = (cum[hi] - cum[lo]) / np.maximum(hi - lo, 1)
    armed = det.c_lo is not None or det.c_hi is not None
    c_lo = -np.inf if det.c_lo is None else det.c_lo
    c_hi = np.inf if det.c_hi is None else det.c_hi
    gate = armed & (windowed >= c_lo) & (windowed <= c_hi)
    return Derived(m, count, windowed, np.asarray(gate, bool), armed)


# ---- painting helpers --------------------------------------------------------


def _font(size: int, *, bold: bool = False, spaced: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    if spaced:
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
    return font


def ramp_lut(stops: tuple[tuple[int, int, int], ...], alpha: bool = False) -> np.ndarray:
    """256-entry ARGB32 lookup table interpolating the given stops."""
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, 256)
    channels = []
    for k in range(3):
        values = [s[k] for s in stops]
        channels.append(np.interp(t, positions, values))
    r, g, b = (c.astype(np.uint32) for c in channels)
    a = (t * 255).astype(np.uint32) if alpha else np.full(256, 255, np.uint32)
    return (a << 24) | (r << 16) | (g << 8) | b


def to_qimage(argb: np.ndarray) -> QImage:
    h, w = argb.shape
    data = np.ascontiguousarray(argb, dtype=np.uint32)
    return QImage(data.tobytes(), w, h, w * 4, QImage.Format.Format_ARGB32).copy()


# ---- the plot family ---------------------------------------------------------

MARGIN_L, MARGIN_R, MARGIN_T, MARGIN_B = 48, 66, 24, 8
GRAB_PX = 8


class BasePlot(QWidget):
    """Shared frame: title row, recessive grid, playhead, two band handles.

    Owns zero detector state. The window sets values in; drags signal out.
    `band_changed` fires per mouse-move (the cheap tier), `band_committed`
    on release (the expensive tier). Plain drags scrub the shared playhead.
    """

    band_changed = Signal(object, object)  # lo, hi (None = unbounded)
    band_committed = Signal(object, object)
    scrubbed = Signal(int)

    title = ""
    unbounded_allowed = True

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        self.lo: float | None = None
        self.hi: float | None = None
        self.playhead = 0
        self.handles_on = True
        self.readout = ""
        self.hover: QPointF | None = None
        self._drag: str | None = None  # "lo" | "hi" | "scrub"

    # value axis - subclasses override for log axes
    def _fwd(self, v: float) -> float:
        return v

    def _inv(self, t: float) -> float:
        return t

    def _range(self) -> tuple[float, float]:
        return 0.0, 1.0

    def plot_rect(self) -> QRect:
        return self.rect().adjusted(MARGIN_L, MARGIN_T, -MARGIN_R, -MARGIN_B)

    def x_of(self, frame: float) -> float:
        r = self.plot_rect()
        return r.left() + frame / max(T - 1, 1) * r.width()

    def frame_of(self, x: float) -> int:
        r = self.plot_rect()
        return int(np.clip((x - r.left()) / max(r.width(), 1) * (T - 1), 0, T - 1))

    def y_of(self, value: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        t = (self._fwd(value) - self._fwd(lo)) / max(self._fwd(hi) - self._fwd(lo), 1e-9)
        return r.bottom() - t * r.height()

    def value_of(self, y: float) -> float:
        lo, hi = self._range()
        r = self.plot_rect()
        t = (r.bottom() - y) / max(r.height(), 1)
        return self._inv(self._fwd(lo) + t * (self._fwd(hi) - self._fwd(lo)))

    # -- band handles ------------------------------------------------------

    def _handle_y(self, which: str) -> float:
        value = self.lo if which == "lo" else self.hi
        lo, hi = self._range()
        if value is None:
            value = lo if which == "lo" else hi
        return self.y_of(min(max(value, lo), hi))

    def set_band(self, lo: float | None, hi: float | None) -> None:
        self.lo, self.hi = lo, hi
        self.update()

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        if self.handles_on and self.plot_rect().adjusted(0, -12, 60, 12).contains(pos.toPoint()):
            near = sorted(("lo", "hi"), key=lambda w: abs(self._handle_y(w) - pos.y()))[0]
            if abs(self._handle_y(near) - pos.y()) <= GRAB_PX:
                self._drag = near
                return
        self._drag = "scrub"
        self.scrubbed.emit(self.frame_of(pos.x()))

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        self.hover = pos
        if self._drag in ("lo", "hi"):
            self._drag_handle(pos.y())
        elif self._drag == "scrub":
            self.scrubbed.emit(self.frame_of(pos.x()))
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hover = None
        self.update()

    def _drag_handle(self, y: float) -> None:
        r = self.plot_rect()
        lo, hi = self._range()
        if self.unbounded_allowed and y < r.top() - 4:
            value: float | None = None if self._drag == "hi" else self.value_of(r.top())
        elif self.unbounded_allowed and y > r.bottom() + 4:
            value = None if self._drag == "lo" else self.value_of(r.bottom())
        else:
            value = min(max(self.value_of(y), lo), hi)
        if self._drag == "lo":
            self.lo = value
            if value is not None and self.hi is not None and value > self.hi:
                self.lo, self.hi = self.hi, value
                self._drag = "hi"
        else:
            self.hi = value
            if value is not None and self.lo is not None and value < self.lo:
                self.lo, self.hi = value, self.lo
                self._drag = "lo"
        self.band_changed.emit(self.lo, self.hi)

    def mouseReleaseEvent(self, event: object) -> None:
        if self._drag in ("lo", "hi"):
            self.band_committed.emit(self.lo, self.hi)
        self._drag = None

    # -- painting ----------------------------------------------------------

    def fmt(self, value: float | None, which: str) -> str:
        if value is None:
            return "inf" if which == "hi" else "0"
        return f"{value:.3g}"

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PANEL)
        r = self.plot_rect()

        painter.setPen(DIM)
        painter.setFont(_font(8, bold=True, spaced=True))
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, self.title.upper())
        if self.readout:
            painter.drawText(
                QRect(10, 4, self.width() - 20, 14),
                int(Qt.AlignmentFlag.AlignRight),
                self.readout,
            )

        grid_pen = QPen(QColor(LINE.red(), LINE.green(), LINE.blue(), 90), 1)
        painter.setPen(grid_pen)
        for k in range(1, 4):
            y = r.top() + k * r.height() / 4
            painter.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))

        painter.save()
        painter.setClipRect(r)
        self.paint_content(painter, r)
        painter.restore()

        head_x = self.x_of(self.playhead)
        painter.setPen(QPen(QColor(TEXT.red(), TEXT.green(), TEXT.blue(), 130), 1))
        painter.drawLine(QPointF(head_x, r.top()), QPointF(head_x, r.bottom()))

        if self.handles_on:
            self._paint_handles(painter, r)

    def paint_content(self, painter: QPainter, r: QRect) -> None:  # override
        pass

    def _paint_handles(self, painter: QPainter, r: QRect) -> None:
        for which in ("lo", "hi"):
            y = self._handle_y(which)
            value = self.lo if which == "lo" else self.hi
            color = QColor(BAND)
            if value is None:
                color.setAlpha(110)
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(r.left(), y), QPointF(r.right() + 22, y))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(r.right() + 22, y), 3.2, 3.2)
            painter.setFont(_font(8))
            painter.drawText(
                QRectF(r.right() + 28, y - 8, MARGIN_R - 30, 16),
                int(Qt.AlignmentFlag.AlignVCenter),
                self.fmt(value, which),
            )


class ScalogramPlot(BasePlot):
    """Pooled Morlet power, log-frequency axis, COI faded, freq-band handles."""

    title = "scalogram - drag the frequency band"
    unbounded_allowed = False  # frequency handles clamp to the bank's edges

    def __init__(self) -> None:
        super().__init__()
        self._image = self._build_image()

    def _fwd(self, v: float) -> float:
        return math.log10(v)

    def _inv(self, t: float) -> float:
        return 10.0**t

    def _range(self) -> tuple[float, float]:
        return float(FREQS[0]), float(FREQS[-1])

    def _build_image(self) -> QImage:
        lut = ramp_lut(SCALO_STOPS)
        log_p = np.log10(POOLED + 1e-9)
        norm = (log_p - log_p.min()) / max(log_p.max() - log_p.min(), 1e-9)
        argb = lut[(norm * 255).astype(np.uint8)]
        for row, f in enumerate(FREQS):
            edge = int(min(coi_samples(float(f)), T))
            if edge <= 1:
                continue
            fade = np.linspace(0.15, 1.0, edge)
            for sl, ramp in ((np.s_[:edge], fade), (np.s_[T - edge :], fade[::-1])):
                cell = argb[row, sl]
                a = ((cell >> 24) * ramp).astype(np.uint32)
                argb[row, sl] = (a << 24) | (cell & 0x00FFFFFF)
        return to_qimage(argb[::-1])  # row 0 = lowest f; flip so top = high f

    def fmt(self, value: float | None, which: str) -> str:
        lo, hi = self._range()
        if value is None:
            value = lo if which == "lo" else hi
        return f"{value:.2f}"

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(12, 8, 20))
        painter.drawImage(QRectF(r), self._image)
        painter.setPen(DIM)
        painter.setFont(_font(7))
        for f in (0.5, 2.0, 8.0, 22.5):
            painter.drawText(
                QRectF(r.left() - 42, self.y_of(f) - 7, 38, 14),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                f"{f:g} Hz",
            )


class DensityPlot(BasePlot):
    """All blocks at once: per-frame value histogram, log1p axis, value band."""

    title = "band power by block - drag the value band"
    BINS = 96

    def __init__(self) -> None:
        super().__init__()
        self._image: QImage | None = None
        self._max = 1.0
        self._solo: np.ndarray | None = None

    def _fwd(self, v: float) -> float:
        return math.log1p(max(v, 0.0))

    def _inv(self, t: float) -> float:
        return math.expm1(t)

    def _range(self) -> tuple[float, float]:
        return 0.0, self._max

    def set_matrix(self, m: np.ndarray, solo: int | None) -> None:
        self._max = float(m.max()) or 1.0
        top = math.log1p(self._max)
        idx = np.minimum((np.log1p(m) / top * (self.BINS - 1)).astype(np.int32), self.BINS - 1)
        counts = np.zeros((self.BINS, T), np.float32)
        cols = np.repeat(np.arange(T), B)
        np.add.at(counts, (idx.ravel(), cols), 1.0)
        norm = np.log1p(counts) / math.log1p(B)
        lut = ramp_lut(DENSITY_STOPS)
        self._image = to_qimage(lut[(norm * 255).astype(np.uint8)][::-1])
        self._solo = m[:, solo] if solo is not None else None
        self.update()

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        painter.fillRect(r, QColor(*DENSITY_STOPS[0]))
        if self._image is not None:
            painter.drawImage(QRectF(r), self._image)
        if self._solo is not None:
            painter.setPen(QPen(ACCENT, 1.4))
            step = max(1, T // max(r.width(), 1))
            points = [
                QPointF(self.x_of(t), self.y_of(float(self._solo[t]))) for t in range(0, T, step)
            ]
            for a, b in pairwise(points):
                painter.drawLine(a, b)


class CountPlot(BasePlot):
    """The detection graph: windowed count, gate spans, count threshold."""

    title = "blocks in band - windowed over D"

    def __init__(self) -> None:
        super().__init__()
        self.windowed = np.zeros(T, np.float32)
        self.gate = np.zeros(T, bool)
        self.armed = False

    def _range(self) -> tuple[float, float]:
        return 0.0, float(B)

    def set_series(self, windowed: np.ndarray, gate: np.ndarray, armed: bool) -> None:
        self.windowed, self.gate, self.armed = windowed, gate, armed
        self.update()

    def fmt(self, value: float | None, which: str) -> str:
        if value is None:
            return "off" if which == "lo" else "inf"
        return f"{value:.0f}"

    def paint_content(self, painter: QPainter, r: QRect) -> None:
        if self.armed:
            fill = QColor(DETECT)
            fill.setAlpha(52)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            edges = np.flatnonzero(np.diff(np.r_[0, self.gate.view(np.int8), 0]))
            for lo, hi in zip(edges[::2], edges[1::2], strict=False):
                x0, x1 = self.x_of(int(lo)), self.x_of(int(hi))
                width = max(x1 - x0, 1.0)  # a 1-frame detection stays visible
                painter.drawRect(QRectF(x0, r.top(), width, r.height()))
        painter.setPen(QPen(DETECT if self.armed else DIM, 1.6))
        step = max(1, T // max(r.width(), 1))
        points = [
            QPointF(self.x_of(t), self.y_of(float(self.windowed[t]))) for t in range(0, T, step)
        ]
        for a, b in pairwise(points):
            painter.drawLine(a, b)


class BlockHeat(QWidget):
    """The frame with the block grid over it. Fill = band power at playhead,
    outline = in the value band now, click a block to solo it in the density
    plot. Hover reads the block out. The frame is context, not data."""

    solo_toggled = Signal(object)  # block index | None

    def __init__(self, frame: QImage, caption: str) -> None:
        super().__init__()
        self.frame = frame
        self.caption = caption
        self.values = np.zeros(B, np.float32)
        self.in_band = np.zeros(B, bool)
        self.solo: int | None = None
        self.scale_max = float(np.percentile(CUBE.sum(axis=0), 99.5))
        self.hover_block: int | None = None
        self.setMouseTracking(True)
        self.setMinimumSize(420, 300)

    def set_state(self, values: np.ndarray, in_band: np.ndarray, solo: int | None) -> None:
        self.values, self.in_band, self.solo = values, in_band, solo
        self.update()

    def _grid_rect(self) -> QRectF:
        r = QRectF(self.rect()).adjusted(10, 22, -10, -22)
        side = min(r.width(), r.height())
        return QRectF(r.center().x() - side / 2, r.center().y() - side / 2, side, side)

    def _block_at(self, pos: QPointF) -> int | None:
        g = self._grid_rect()
        if not g.contains(pos):
            return None
        col = int((pos.x() - g.left()) / g.width() * GRID[1])
        row = int((pos.y() - g.top()) / g.height() * GRID[0])
        return min(row, GRID[0] - 1) * GRID[1] + min(col, GRID[1] - 1)

    def mouseMoveEvent(self, event) -> None:
        self.hover_block = self._block_at(event.position())
        self.update()

    def leaveEvent(self, event: object) -> None:
        self.hover_block = None
        self.update()

    def mousePressEvent(self, event) -> None:
        block = self._block_at(event.position())
        self.solo_toggled.emit(None if block == self.solo else block)

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(DIM)
        painter.setFont(_font(8, bold=True, spaced=True))
        painter.drawText(QRect(10, 4, self.width() - 20, 14), 0, "BLOCK HEAT - CLICK TO SOLO")

        g = self._grid_rect()
        source = QRectF(self.frame.rect())
        side = min(source.width(), source.height())
        square = QRectF(source.center().x() - side / 2, source.center().y() - side / 2, side, side)
        painter.setOpacity(0.42)
        painter.drawImage(g, self.frame, square)
        painter.setOpacity(1.0)

        cell_w, cell_h = g.width() / GRID[1], g.height() / GRID[0]
        for b in range(B):
            row, col = divmod(b, GRID[1])
            cell = QRectF(g.left() + col * cell_w, g.top() + row * cell_h, cell_w, cell_h)
            heat = min(float(self.values[b]) / self.scale_max, 1.0)
            stop = SCALO_STOPS[-2]
            fill = QColor(*stop)
            fill.setAlpha(int(150 * heat))
            painter.fillRect(cell.adjusted(1, 1, -1, -1), fill)
            if self.in_band[b]:
                painter.setPen(QPen(ACCENT, 1.4))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(cell.adjusted(1.5, 1.5, -1.5, -1.5))
            if self.solo == b:
                painter.setPen(QPen(TEXT, 1.8))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(cell.adjusted(1.5, 1.5, -1.5, -1.5))

        painter.setPen(DIM)
        painter.setFont(_font(8))
        if self.hover_block is not None:
            b = self.hover_block
            row, col = divmod(b, GRID[1])
            state = "in band" if self.in_band[b] else "out"
            note = f"block ({row},{col}) - {self.values[b]:.0f} - {state}"
        else:
            note = self.caption
        painter.drawText(QRect(10, self.height() - 18, self.width() - 20, 14), 0, note)


# ---- the detect window --------------------------------------------------------


class DetectWindow(QWidget):
    """Four linked views over one detector value. All wiring passes through
    `_apply`, so 'who recomputes what' stays one function you can read."""

    def __init__(self) -> None:
        super().__init__()
        self.det = Detector()
        self.setWindowTitle("graphs mockup - detect")
        self.setStyleSheet(f"background: {BG.name()}; color: {TEXT.name()};")
        self.setMinimumSize(1240, 780)

        frame, caption = sample_frame()
        self.heat = BlockHeat(frame, caption)
        self.scalo = ScalogramPlot()
        self.density = DensityPlot()
        self.count = CountPlot()

        self.d_slider = QSlider(Qt.Orientation.Horizontal)
        self.d_slider.setRange(1, 250)
        self.d_slider.setValue(self.det.d)
        self.d_label = QLabel()
        self.d_label.setFont(_font(8))
        self.d_label.setStyleSheet(f"color: {DIM.name()};")
        self.centered_box = QCheckBox("centered")
        self.centered_box.setChecked(True)
        self.centered_box.setFont(_font(8))
        self.centered_box.setStyleSheet(f"color: {DIM.name()};")
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFixedWidth(72)
        self.reset_btn.setStyleSheet(
            f"QPushButton {{background: {PANEL.name()}; color: {TEXT.name()};"
            f" border: 1px solid {LINE.name()}; border-radius: 4px; padding: 3px;}}"
        )

        self.status = QLabel("drag a red handle; the footer narrates the event tiers")
        self.status.setFont(_font(8))
        self.status.setStyleSheet(f"color: {DIM.name()};")
        self.summary = QLabel()
        self.summary.setFont(_font(8))

        left = QVBoxLayout()
        left.addWidget(self.heat, 3)
        left.addWidget(self.count, 2)
        d_row = QHBoxLayout()
        d_row.addWidget(self.d_label)
        d_row.addWidget(self.d_slider, 1)
        d_row.addWidget(self.centered_box)
        d_row.addWidget(self.reset_btn)
        left.addLayout(d_row)

        right = QVBoxLayout()
        right.addWidget(self.scalo, 1)
        right.addWidget(self.density, 1)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addLayout(left, 5)
        top.addLayout(right, 6)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(8)
        outer.addLayout(top, 1)
        foot = QHBoxLayout()
        foot.addWidget(self.status, 1)
        foot.addWidget(self.summary)
        outer.addLayout(foot)

        self.scalo.band_changed.connect(lambda lo, hi: self._on_band("freq", lo, hi, False))
        self.scalo.band_committed.connect(lambda lo, hi: self._on_band("freq", lo, hi, True))
        self.density.band_changed.connect(lambda lo, hi: self._on_band("value", lo, hi, False))
        self.density.band_committed.connect(lambda lo, hi: self._on_band("value", lo, hi, True))
        self.count.band_changed.connect(lambda lo, hi: self._on_band("count", lo, hi, False))
        self.count.band_committed.connect(lambda lo, hi: self._on_band("count", lo, hi, True))
        for plot in (self.scalo, self.density, self.count):
            plot.scrubbed.connect(self._on_scrub)
        self.heat.solo_toggled.connect(self._on_solo)
        self.d_slider.valueChanged.connect(self._on_d)
        self.centered_box.toggled.connect(self._on_centered)
        self.reset_btn.clicked.connect(self._on_reset)

        self._apply("initial")

    # -- one place where state turns into pixels ---------------------------

    def _apply(self, why: str) -> None:
        det = self.det
        derived = derive(det)
        self.scalo.set_band(det.f_lo, det.f_hi)
        self.scalo.playhead = det.playhead
        self.density.set_band(det.v_lo, det.v_hi)
        self.density.playhead = det.playhead
        self.density.set_matrix(derived.band_power, det.solo)
        self.count.set_band(det.c_lo, det.c_hi)
        self.count.playhead = det.playhead
        self.count.set_series(derived.windowed, derived.gate, derived.armed)

        v_lo = -np.inf if det.v_lo is None else det.v_lo
        v_hi = np.inf if det.v_hi is None else det.v_hi
        now = derived.band_power[det.playhead]
        self.heat.set_state(now, (now >= v_lo) & (now <= v_hi), det.solo)

        i, j = det.freq_indices()
        self.scalo.readout = f"band {FREQS[i]:.2f}-{FREQS[j]:.2f} Hz"
        self.density.readout = (
            f"value {self.density.fmt(det.v_lo, 'lo')}-{self.density.fmt(det.v_hi, 'hi')}"
        )
        self.d_label.setText(f"D {det.d} fr ({det.d / FPS:.2f} s)")
        if derived.armed:
            spans = int(np.count_nonzero(np.diff(np.r_[0, derived.gate.view(np.int8)]) == 1))
            seconds = float(derived.gate.sum()) / FPS
            self.summary.setText(f"{spans} detections - {seconds:.1f} s total")
            self.summary.setStyleSheet(f"color: {DETECT.name()};")
        else:
            self.summary.setText("detector disarmed - place the count threshold")
            self.summary.setStyleSheet(f"color: {DIM.name()};")
        for widget in (self.scalo, self.density, self.count, self.heat):
            widget.update()

    # -- handlers ------------------------------------------------------------

    def _on_band(self, which: str, lo, hi, committed: bool) -> None:
        if which == "freq":
            self.det.f_lo, self.det.f_hi = lo, hi
        elif which == "value":
            self.det.v_lo, self.det.v_hi = lo, hi
        else:
            self.det.c_lo, self.det.c_hi = lo, hi
        tier = (
            "committed - rebuild anything deferred" if committed else "dragging - cheap re-derive"
        )
        self.status.setText(f"{which} band -> {tier}")
        self._apply(which)

    def _on_scrub(self, frame: int) -> None:
        self.det.playhead = frame
        self.status.setText(f"scrub -> frame {frame} ({frame / FPS:.2f} s)")
        self._apply("scrub")

    def _on_solo(self, block) -> None:
        self.det.solo = block
        label = "off" if block is None else f"block ({block // GRID[1]},{block % GRID[1]})"
        self.status.setText(f"solo -> {label}")
        self._apply("solo")

    def _on_d(self, value: int) -> None:
        self.det.d = value
        self.status.setText(f"D -> {value} fr (instant: prefix-sum mean)")
        self._apply("d")

    def _on_centered(self, checked: bool) -> None:
        self.det.centered = checked
        self._apply("centered")

    def _on_reset(self) -> None:
        self.det = Detector(playhead=self.det.playhead)
        self.d_slider.setValue(self.det.d)
        self.centered_box.setChecked(True)
        self.status.setText("reset -> bands cleared, D back to 0.5 s, detector disarmed")
        self._apply("reset")


# ---- the color variant ---------------------------------------------------------


@dataclass
class ColorSample:
    rgb: tuple[int, int, int]
    include: bool


class ColorFrame(QWidget):
    """The paused frame. Click = include this color; Shift/right = exclude."""

    sampled = Signal(object)  # ColorSample

    def __init__(self, frame: QImage) -> None:
        super().__init__()
        self.frame = frame.convertToFormat(QImage.Format.Format_RGB888)
        width = 480
        small = self.frame.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
        buffer = small.constBits().tobytes()
        self.small = (
            np.frombuffer(buffer, np.uint8)
            .reshape(small.height(), small.bytesPerLine() // 1)[:, : small.width() * 3]
            .reshape(small.height(), small.width(), 3)
            .astype(np.float32)
        )
        self.mask_img: QImage | None = None
        self.samples: list[ColorSample] = []
        self.setMinimumSize(560, 420)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def frame_rect(self) -> QRectF:
        r = QRectF(self.rect()).adjusted(10, 22, -10, -22)
        scale = min(r.width() / self.frame.width(), r.height() / self.frame.height())
        w, h = self.frame.width() * scale, self.frame.height() * scale
        return QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h)

    def mousePressEvent(self, event) -> None:
        r = self.frame_rect()
        pos = event.position()
        if not r.contains(pos):
            return
        fx = (pos.x() - r.left()) / r.width()
        fy = (pos.y() - r.top()) / r.height()
        h, w, _ = self.small.shape
        x, y = int(fx * (w - 1)), int(fy * (h - 1))
        patch = self.small[max(y - 1, 0) : y + 2, max(x - 1, 0) : x + 2].reshape(-1, 3)
        rgb = tuple(int(c) for c in patch.mean(axis=0))
        include = not (
            event.button() == Qt.MouseButton.RightButton
            or event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        self.sampled.emit(ColorSample(rgb, include))

    def set_mask(self, mask: np.ndarray | None, samples: list[ColorSample]) -> None:
        self.samples = samples
        if mask is None:
            self.mask_img = None
        else:
            h, w = mask.shape
            argb = np.zeros((h, w), np.uint32)
            tint = (ACCENT.red() << 16) | (ACCENT.green() << 8) | ACCENT.blue()
            argb[mask] = (150 << 24) | tint
            self.mask_img = to_qimage(argb)
        self.update()

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PANEL)
        painter.setPen(DIM)
        painter.setFont(_font(8, bold=True, spaced=True))
        painter.drawText(
            QRect(10, 4, self.width() - 20, 14),
            0,
            "PAUSED FRAME - CLICK: COLOR COUNTS - SHIFT/RIGHT: MUST NOT COUNT",
        )
        r = self.frame_rect()
        painter.drawImage(r, self.frame)
        if self.mask_img is not None:
            painter.drawImage(r, self.mask_img)


class ColorWindow(QWidget):
    """Configure a 'detected color' gate by pointing at the paused frame."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("graphs mockup - color gate")
        self.setStyleSheet(f"background: {BG.name()}; color: {TEXT.name()};")
        self.setMinimumSize(1080, 640)
        frame, caption = sample_frame()
        self.view = ColorFrame(frame)
        self.samples: list[ColorSample] = []
        self.tolerance = 46

        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)
        self.chips.addStretch(1)

        self.tol_slider = QSlider(Qt.Orientation.Horizontal)
        self.tol_slider.setRange(8, 140)
        self.tol_slider.setValue(self.tolerance)
        self.tol_label = QLabel()
        self.tol_label.setFont(_font(8))
        self.tol_label.setStyleSheet(f"color: {DIM.name()};")

        self.coverage = QLabel("no samples yet - click a color that should count")
        self.coverage.setFont(_font(12, bold=True))
        self.caption = QLabel(caption)
        self.caption.setFont(_font(8))
        self.caption.setStyleSheet(f"color: {DIM.name()};")

        side = QVBoxLayout()
        side.setSpacing(10)
        head = QLabel("COLOR GATE")
        head.setFont(_font(8, bold=True, spaced=True))
        head.setStyleSheet(f"color: {DIM.name()};")
        side.addWidget(head)
        side.addWidget(self.coverage)
        tol_row = QHBoxLayout()
        tol_row.addWidget(self.tol_label)
        tol_row.addWidget(self.tol_slider, 1)
        side.addLayout(tol_row)
        chip_head = QLabel("samples - click a chip to remove it")
        chip_head.setFont(_font(8))
        chip_head.setStyleSheet(f"color: {DIM.name()};")
        side.addWidget(chip_head)
        side.addLayout(self.chips)
        note = QLabel(
            "The gate becomes one more per-block channel: fraction of the\n"
            "block's pixels inside the color gate, fed to the same temporal\n"
            "filter and detector as every other signal."
        )
        note.setFont(_font(8))
        note.setStyleSheet(f"color: {DIM.name()};")
        side.addWidget(note)
        side.addStretch(1)
        side.addWidget(self.caption)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.addWidget(self.view, 3)
        outer.addLayout(side, 2)

        self.view.sampled.connect(self._on_sample)
        self.tol_slider.valueChanged.connect(self._on_tolerance)
        self._recompute()

    def _on_sample(self, sample: ColorSample) -> None:
        self.samples.append(sample)
        self._recompute()

    def _on_tolerance(self, value: int) -> None:
        self.tolerance = value
        self._recompute()

    def _remove(self, index: int) -> None:
        del self.samples[index]
        self._recompute()

    def _recompute(self) -> None:
        while self.chips.count() > 1:
            item = self.chips.takeAt(0)
            if item.widget() is not None:
                item.widget().setParent(None)
                item.widget().deleteLater()
        for index, sample in enumerate(self.samples):
            r, g, b = sample.rgb
            chip = QPushButton(("+" if sample.include else "-") + " x")
            chip.setFixedHeight(24)
            edge = "transparent" if sample.include else BAND.name()
            fg = "#101216" if (r + g + b) > 340 else "#e6e7eb"
            chip.setStyleSheet(
                f"QPushButton {{background: rgb({r},{g},{b}); color: {fg};"
                f" border: 2px solid {edge}; border-radius: 5px; padding: 2px 8px;}}"
            )
            chip.setToolTip(f"rgb({r},{g},{b}) - {'include' if sample.include else 'exclude'}")
            chip.clicked.connect(lambda checked=False, i=index: self._remove(i))
            self.chips.insertWidget(self.chips.count() - 1, chip)

        self.tol_label.setText(f"tolerance {self.tolerance}")
        includes = [s.rgb for s in self.samples if s.include]
        excludes = [s.rgb for s in self.samples if not s.include]
        if not includes:
            self.view.set_mask(None, self.samples)
            self.coverage.setText("no samples yet - click a color that should count")
            self.coverage.setStyleSheet(f"color: {DIM.name()};")
            return
        pixels = self.view.small  # (h, w, 3) float32
        mask = np.zeros(pixels.shape[:2], bool)
        for rgb in includes:
            dist = np.linalg.norm(pixels - np.array(rgb, np.float32), axis=2)
            mask |= dist <= self.tolerance
        for rgb in excludes:
            dist = np.linalg.norm(pixels - np.array(rgb, np.float32), axis=2)
            mask &= ~(dist <= self.tolerance * 0.8)
        self.view.set_mask(mask, self.samples)
        share = 100.0 * float(mask.mean())
        self.coverage.setText(f"{share:.1f}% of the frame is in the color gate")
        self.coverage.setStyleSheet(f"color: {ACCENT.name()};")


# ---- shots -------------------------------------------------------------------


def apply_shot(window: QWidget, shot: str) -> None:
    if isinstance(window, DetectWindow):
        if shot in ("tuned", "solo"):
            window.det.f_lo, window.det.f_hi = 8.0, 16.0
            window.det.v_lo, window.det.v_hi = 1600.0, None
            window.det.c_lo, window.det.c_hi = 10.0, None
            window.det.playhead = 320
        if shot == "solo":
            window.det.solo = CLUSTER[5]
        window._apply(shot)
    elif isinstance(window, ColorWindow) and shot == "sampled":
        h, w, _ = window.view.small.shape
        picks = [
            (int(w * 0.5), int(h * 0.45), True),
            (int(w * 0.25), int(h * 0.3), True),
            (int(w * 0.8), int(h * 0.75), False),
        ]
        for x, y, include in picks:
            rgb = tuple(int(c) for c in window.view.small[y, x])
            window.samples.append(ColorSample(rgb, include))
        window._recompute()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("detect", "color"), default="detect")
    parser.add_argument("--shot", choices=("none", "tuned", "solo", "sampled"), default="none")
    parser.add_argument("--png", type=str, default="")
    parser.add_argument("--size", type=str, default="1280x800")
    args = parser.parse_args()

    app = QApplication([])
    window: QWidget = DetectWindow() if args.variant == "detect" else ColorWindow()
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
