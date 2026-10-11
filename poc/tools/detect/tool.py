"""Detection over a block-signal series. v2's detector, as one series tool.

Morlet band power per block (Torrence & Compo, w0 = 6), a value band on
it, the count of blocks in band per frame, a windowed mean over D frames,
and a threshold on that giving the gate and its intervals. The settings
widget is the three plots with their handles: the scalogram (frequency
band), the density (value band), and the count (threshold).

Band power is cached on (series key, length, frequency band), so a value
band or threshold drag never recomputes the transform. That was v2's
two-tier signal contract; here it is an `if`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget
from scipy import fft as _fft

NAME = "detect"
KIND = "series"
DEFAULTS = {"flo": 1.0, "fhi": 6.0, "vlo": 5000.0, "vhi": float("inf"), "count": 40.0, "window": 30, "centered": True}

W0 = 6.0
PAD_EFOLDINGS = 3.0
N_FREQS = 24


# --- wavelet (ported from v2 core/ops/wavelet.py, semantics intact) ----------


def default_freqs(fps, fmin=0.5, fmax=25.0, n=N_FREQS):
    return np.geomspace(fmin, min(fmax, 0.45 * fps), n)


def morlet_scales(freqs_hz):
    return (W0 + np.sqrt(2.0 + W0 * W0)) / (4.0 * np.pi * np.asarray(freqs_hz, np.float64))


def coi_efolding_s(freqs_hz):
    return np.sqrt(2.0) * morlet_scales(freqs_hz)


def _daughter(scale, omega, heavi, dt):
    norm = np.sqrt(2.0 * np.pi * scale / dt) * np.pi**-0.25
    return (norm * heavi * np.exp(-0.5 * (scale * omega - W0) ** 2)).astype(np.complex64)


def _setup(n_frames, fs, freqs_hz):
    dt = 1.0 / fs
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = int(_fft.next_fast_len(n_frames + support))
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    return dt, n, omega, omega > 0


def morlet_power(x, fs, freqs_hz):
    """(T,) -> (F, T) float32 scalogram power."""
    x32 = np.asarray(x, np.float32)
    n_frames = x32.shape[0]
    dt, n, omega, heavi = _setup(n_frames, fs, freqs_hz)
    xf = _fft.fft(x32, n=n)
    out = np.empty((len(freqs_hz), n_frames), np.float32)
    for i, s in enumerate(morlet_scales(freqs_hz)):
        w = _fft.ifft(xf * _daughter(float(s), omega, heavi, dt))[:n_frames]
        out[i] = w.real**2 + w.imag**2
    return out


def band_indices(freqs_hz, flo, fhi):
    freqs = np.asarray(freqs_hz, np.float64)
    i = int(np.searchsorted(freqs, flo, "left"))
    j = int(np.searchsorted(freqs, fhi, "right"))
    if j <= i:
        i = int(np.argmin(np.abs(freqs - flo)))
        j = i + 1
    return i, j


def morlet_band_power(x, fs, freqs_hz, i, j, block_chunk=512):
    """(T, B) -> (T, B) power summed over frequency rows [i, j)."""
    x32 = np.asarray(x, np.float32)
    n_frames, n_blocks = x32.shape
    dt, n, omega, heavi = _setup(n_frames, fs, freqs_hz)
    daughters = [_daughter(float(s), omega, heavi, dt) for s in morlet_scales(freqs_hz)[i:j]]
    out = np.zeros((n_frames, n_blocks), np.float32)

    def transform(c0):
        c1 = min(n_blocks, c0 + block_chunk)
        xf = _fft.fft(x32[:, c0:c1], n=n, axis=0, workers=1)
        acc = np.zeros((n_frames, c1 - c0), np.float32)
        for d in daughters:
            w = _fft.ifft(xf * d[:, None], axis=0, workers=1)[:n_frames]
            acc += w.real**2 + w.imag**2
        out[:, c0:c1] = acc

    starts = range(0, n_blocks, block_chunk)
    if len(starts) < 2:
        for c0 in starts:
            transform(c0)
    else:
        with ThreadPoolExecutor() as pool:
            list(pool.map(transform, starts))
    return out


# --- detection (ported from v2 core/ops/detection.py) --------------------------


def inband_count(m, lo, hi):
    inband = (m >= lo) & (m <= hi) & np.isfinite(m)
    return inband.sum(axis=1).astype(np.float32)


def windowed_mean(count, window, centered):
    n = count.shape[0]
    if n == 0 or window <= 1:
        return count.astype(np.float32)
    c = np.concatenate([[0.0], np.cumsum(count, dtype=np.float64)])
    t = np.arange(n)
    if centered:
        lo = np.maximum(0, t - window // 2)
        hi = np.minimum(n, t + (window - window // 2))
    else:
        hi = t + 1
        lo = np.maximum(0, hi - window)
    return ((c[hi] - c[lo]) / (hi - lo)).astype(np.float32)


def gate_intervals(gate, start=0):
    g = np.asarray(gate, bool)
    if not g.any():
        return []
    edges = np.diff(np.concatenate([[0], g.astype(np.int8), [0]]))
    return [(int(s + start), int(e + start)) for s, e in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))]


# --- the tool ------------------------------------------------------------------

_cache: dict = {}


def _cached(key, make):
    if key not in _cache:
        if len(_cache) > 6:
            _cache.pop(next(iter(_cache)))
        _cache[key] = make()
    return _cache[key]


def run(series, params):
    data = np.asarray(series.data, np.float32)
    T = data.shape[0]
    flat = data.reshape(T, -1)
    freqs = default_freqs(series.fps)
    i, j = band_indices(freqs, params["flo"], params["fhi"])
    band_power = _cached((series.key, T, i, j), lambda: morlet_band_power(flat, series.fps, freqs, i, j))
    scalogram = _cached((series.key, T, "scalogram"), lambda: morlet_power(flat.mean(axis=1), series.fps, freqs))
    count = inband_count(band_power, params["vlo"], params["vhi"])
    windowed = windowed_mean(count, int(params["window"]), bool(params["centered"]))
    gate = windowed >= params["count"]
    return {
        "freqs": freqs,
        "band": (i, j),
        "scalogram": scalogram,
        "band_power": band_power,
        "count": count,
        "windowed": windowed,
        "gate": gate,
        "intervals": gate_intervals(gate, series.start),
        "blocks": flat.shape[1],
    }


# --- the widget: three plots, three handles -------------------------------------

DENSITY_BINS = 64


class Settings(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        pg.setConfigOptions(imageAxisOrder="row-major", antialias=False)
        self.freqs = default_freqs(60.0)
        self.start = 0
        self.vmax_log = 14.0

        self.scalogram = pg.PlotWidget(title="scalogram (pooled over blocks) — drag the band for frequency")
        self.scalo_img = pg.ImageItem()
        self.scalogram.addItem(self.scalo_img)
        self.freq_band = pg.LinearRegionItem(orientation="horizontal", brush=(255, 255, 255, 40), pen=pg.mkPen("y", width=2))
        self.scalogram.addItem(self.freq_band)

        self.density = pg.PlotWidget(title="band power by block (log1p) — drag the band for value")
        self.dens_img = pg.ImageItem()
        self.density.addItem(self.dens_img)
        self.value_band = pg.LinearRegionItem(orientation="horizontal", brush=(255, 255, 255, 40), pen=pg.mkPen("y", width=2))
        self.density.addItem(self.value_band)

        self.count = pg.PlotWidget(title="blocks in band, windowed — drag the line for threshold")
        self.gate_fill = pg.PlotCurveItem(pen=None, fillLevel=0, brush=(60, 200, 60, 90))
        self.count.addItem(self.gate_fill)
        self.count_curve = pg.PlotCurveItem(pen=pg.mkPen("w"))
        self.count.addItem(self.count_curve)
        self.threshold = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen("y", width=2))
        self.count.addItem(self.threshold)

        self.playheads = []
        for plot in (self.scalogram, self.density, self.count):
            line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen((255, 80, 80), width=1))
            plot.addItem(line)
            self.playheads.append(line)
        self.density.setXLink(self.scalogram)
        self.count.setXLink(self.scalogram)

        self.window = QSpinBox()
        self.window.setRange(1, 600)
        self.window.setValue(DEFAULTS["window"])
        self.centered = QCheckBox("centered window")
        self.centered.setChecked(DEFAULTS["centered"])
        self.readout = QLabel()
        controls = QHBoxLayout()
        controls.addWidget(QLabel("window D (frames)"))
        controls.addWidget(self.window)
        controls.addWidget(self.centered)
        controls.addWidget(self.readout, 1)

        plots = QHBoxLayout()
        plots.addWidget(self.scalogram)
        plots.addWidget(self.density)
        plots.addWidget(self.count)
        layout = QVBoxLayout(self)
        layout.addLayout(plots, 1)
        layout.addLayout(controls)

        self._set_handles(DEFAULTS)
        self.freq_band.sigRegionChanged.connect(self._emit)
        self.value_band.sigRegionChanged.connect(self._emit)
        self.threshold.sigPositionChanged.connect(self._emit)
        self.window.valueChanged.connect(self._emit)
        self.centered.toggled.connect(self._emit)

    def _set_handles(self, p):
        self.freq_band.setRegion((self._hz_to_y(p["flo"]), self._hz_to_y(p["fhi"])))
        vhi = p["vhi"] if np.isfinite(p["vhi"]) else np.expm1(self.vmax_log)
        self.value_band.setRegion((np.log1p(p["vlo"]), np.log1p(vhi)))
        self.threshold.setPos(p["count"])

    def _hz_to_y(self, hz):
        return float(np.interp(np.log(hz), np.log(self.freqs), np.arange(len(self.freqs))))

    def _y_to_hz(self, y):
        return float(np.exp(np.interp(y, np.arange(len(self.freqs)), np.log(self.freqs))))

    def _emit(self):
        p = self.params()
        self.readout.setText(
            f"band {p['flo']:.2f}–{p['fhi']:.2f} Hz   value {p['vlo']:.1f}–{p['vhi']:.1f}   "
            f"threshold {p['count']:.1f} blocks"
        )
        self.changed.emit()

    def params(self):
        ylo, yhi = self.freq_band.getRegion()
        vlo, vhi = self.value_band.getRegion()
        return {
            "flo": self._y_to_hz(ylo),
            "fhi": self._y_to_hz(yhi),
            "vlo": float(np.expm1(vlo)),
            "vhi": float("inf") if vhi >= self.vmax_log - 1e-6 else float(np.expm1(vhi)),
            "count": float(self.threshold.value()),
            "window": self.window.value(),
            "centered": self.centered.isChecked(),
        }

    def show_result(self, result, start, fps):
        self.start = start
        self.freqs = result["freqs"]
        T = result["count"].shape[0]
        x0, x1 = start, start + T
        scalo = np.log1p(result["scalogram"])
        self.scalo_img.setImage(scalo, autoLevels=True)
        self.scalo_img.setRect(pg.QtCore.QRectF(x0, 0, T, len(self.freqs)))
        self.scalogram.setYRange(0, len(self.freqs))
        self.scalogram.getAxis("left").setTicks(
            [[(k, f"{self.freqs[k]:.1f}") for k in range(0, len(self.freqs), 4)]]
        )

        bp = np.log1p(result["band_power"])
        vlo, vhi = self.value_band.getRegion()
        unbounded = vhi >= self.vmax_log - 1e-6
        self.vmax_log = float(max(bp.max(), 1.0))
        if unbounded:
            # keep "no upper bound" meaning that as the scale grows with the record
            self.value_band.blockSignals(True)
            self.value_band.setRegion((min(vlo, self.vmax_log), self.vmax_log))
            self.value_band.blockSignals(False)
        bins = np.linspace(0, self.vmax_log, DENSITY_BINS + 1)
        hist = np.stack([np.histogram(col, bins)[0] for col in bp]).T.astype(np.float32)
        self.dens_img.setImage(np.log1p(hist), autoLevels=True)
        self.dens_img.setRect(pg.QtCore.QRectF(x0, 0, T, self.vmax_log))
        self.density.setYRange(0, self.vmax_log)

        xs = np.arange(x0, x1)
        self.count_curve.setData(xs, result["windowed"])
        top = max(float(result["windowed"].max()), float(self.threshold.value()) * 1.2, 1.0)
        self.gate_fill.setData(xs, result["gate"].astype(np.float32) * top, stepMode=None)
        self.count.setYRange(0, top)
        self.scalogram.setXRange(x0, x1, padding=0)

    def set_playhead(self, row):
        for line in self.playheads:
            line.setPos(row)


def settings(parent=None):
    return Settings(parent)
