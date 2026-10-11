"""The player: one video, one chain, the tools' own widgets, and a loop window.

This is the whole of what a tool's standalone.py gets, and it is the same
module SIEVE's window builds on. Nothing in here knows any tool by name.
"""

from __future__ import annotations

import threading
from typing import Any

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .chain import Chain

#: Rows between partial series results while the window fills.
PROGRESS_EVERY = 30


class SeriesWorker(QThread):
    """Walks the loop window through the chain on its own thread; latest wins.

    A frame-param change restarts the walk from the window start. A
    series-param change reruns only the series tool on the stack in hand.
    """

    result = Signal(object, int, int)  # series result, window start, rows so far

    def __init__(self, chain: Chain) -> None:
        super().__init__()
        self.chain = chain
        self._wake = threading.Event()
        self._stop = False
        self._window = (0, 1)
        self._want_rev = -1
        self._series_only = False

    def request(self, start: int, length: int, series_only: bool = False) -> None:
        self._window = (start, length)
        self._want_rev = self.chain.revision
        self._series_only = series_only
        self._wake.set()

    def stop(self) -> None:
        self._stop = True
        self._wake.set()
        self.wait(2000)

    def run(self) -> None:
        stack: list[np.ndarray] = []
        done_for: tuple[int, int, int] | None = None
        while not self._stop:
            self._wake.wait()
            self._wake.clear()
            if self._stop:
                return
            start, length = self._window
            rev = self._want_rev
            if self._series_only and done_for == (start, length, rev) and stack:
                self._emit(stack, start)
                continue
            stack = []
            last = self.chain.last_frame_stage()
            for i in range(length):
                if self._stop or self._wake.is_set():
                    break
                stack.append(self.chain.stage(last, start + i))
                if (i + 1) % PROGRESS_EVERY == 0 or i == length - 1:
                    self._emit(stack, start)
            else:
                done_for = (start, length, rev)

    def _emit(self, stack: list[np.ndarray], start: int) -> None:
        out = self.chain.run_series(np.stack(stack), start)
        self.result.emit(out, start, len(stack))


class PlayerWindow(QMainWindow):
    def __init__(self, chain: Chain, window_length: int = 600) -> None:
        super().__init__()
        self.chain = chain
        self.row = 0
        self.series_result: dict[str, Any] | None = None
        self.series_start = 0
        self.series_rows = 0
        self.setWindowTitle(f"sieve_tool — {chain.source.path.name}")

        self.image = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumSize(320, 240)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, chain.source.count - 1)
        self.slider.valueChanged.connect(self.seek)
        self.play_button = QPushButton("Play")
        self.play_button.setCheckable(True)
        self.play_button.toggled.connect(self._toggle_play)
        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / chain.fps))
        self.timer.timeout.connect(self._tick)

        self.loop_start = QSpinBox()
        self.loop_start.setRange(0, chain.source.count - 1)
        self.loop_len = QSpinBox()
        self.loop_len.setRange(30, min(chain.source.count, 20000))
        self.loop_len.setValue(min(window_length, chain.source.count))
        self.loop_start.valueChanged.connect(self._window_changed)
        self.loop_len.valueChanged.connect(self._window_changed)

        self.show_stage = QComboBox()
        self.show_stage.addItem("decoded frame", -1)
        for i, stage in enumerate(chain.stages):
            self.show_stage.addItem(stage.tool.NAME, i)
        self.show_stage.setCurrentIndex(self.show_stage.count() - 1)
        self.show_stage.currentIndexChanged.connect(lambda _: self._render())

        transport = QHBoxLayout()
        transport.addWidget(self.play_button)
        transport.addWidget(QLabel("loop start"))
        transport.addWidget(self.loop_start)
        transport.addWidget(QLabel("length"))
        transport.addWidget(self.loop_len)
        transport.addWidget(QLabel("show"))
        transport.addWidget(self.show_stage)
        transport.addStretch(1)
        self.row_label = QLabel("0")
        transport.addWidget(self.row_label)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.image, 1)
        left_layout.addWidget(self.slider)
        left_layout.addLayout(transport)

        self.tabs = QTabWidget()
        self.widgets = []
        for i, stage in enumerate(chain.stages):
            widget = stage.tool.settings()
            widget.changed.connect(lambda i=i, w=widget: self._stage_changed(i, w))
            self.tabs.addTab(widget, stage.tool.NAME)
            self.widgets.append(widget)

        top = QSplitter(Qt.Orientation.Horizontal)
        top.addWidget(left)
        top.addWidget(self.tabs)
        top.setStretchFactor(0, 3)
        top.setStretchFactor(1, 1)

        self.series_widget = None
        if chain.series_stage is not None:
            self.series_widget = chain.series_stage.tool.settings()
            self.series_widget.changed.connect(self._series_changed)
            whole = QSplitter(Qt.Orientation.Vertical)
            whole.addWidget(top)
            whole.addWidget(self.series_widget)
            whole.setStretchFactor(0, 2)
            whole.setStretchFactor(1, 1)
            self.setCentralWidget(whole)
        else:
            self.setCentralWidget(top)

        self.worker = SeriesWorker(chain)
        self.worker.result.connect(self._series_result)
        self.worker.start()
        self.report_timer = QTimer(self)
        self.report_timer.setInterval(1000)
        self.report_timer.timeout.connect(self._report)
        self.report_timer.start()
        self.resize(1400, 900)
        self._window_changed()
        self._render()

    # --- transport -------------------------------------------------------

    @Slot(int)
    def seek(self, row: int) -> None:
        self.row = row
        self._render()

    def _toggle_play(self, on: bool) -> None:
        self.play_button.setText("Pause" if on else "Play")
        if on:
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        start, length = self.loop_start.value(), self.loop_len.value()
        nxt = self.row + 1
        if nxt >= start + length or nxt < start:
            nxt = start
        self.slider.setValue(nxt)

    def _window_changed(self) -> None:
        start, length = self.loop_start.value(), self.loop_len.value()
        if not start <= self.row < start + length:
            self.slider.setValue(start)
        self.worker.request(start, length)

    # --- tool params -----------------------------------------------------

    def _stage_changed(self, index: int, widget: QWidget) -> None:
        self.chain.set_params(index, widget.params())
        self.worker.request(self.loop_start.value(), self.loop_len.value())
        self._render()

    def _series_changed(self) -> None:
        assert self.series_widget is not None
        self.chain.set_series_params(self.series_widget.params())
        self.worker.request(self.loop_start.value(), self.loop_len.value(), series_only=True)

    def _series_result(self, result: object, start: int, rows: int) -> None:
        self.series_result = result  # type: ignore[assignment]
        self.series_start = start
        self.series_rows = rows
        if self.series_widget is not None and result is not None:
            self.series_widget.show_result(result, start, self.chain.fps)
            self.series_widget.set_playhead(self.row)
        self._render()

    # --- drawing ---------------------------------------------------------

    def _render(self) -> None:
        index = self.show_stage.currentData()
        try:
            data = self.chain.stage(index, self.row)
        except Exception as exc:  # a tool that raises must not kill the player
            self.image.setText(str(exc))
            return
        display = "image" if index < 0 else getattr(self.chain.stages[index].tool, "DISPLAY", "image")
        rgb = to_rgb(data, display)
        if self._gated(self.row):
            cv2.rectangle(rgb, (0, 0), (rgb.shape[1] - 1, rgb.shape[0] - 1), (255, 40, 40), 6)
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(
            self.image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation
        )
        self.image.setPixmap(pix)
        self.row_label.setText(f"row {self.row}")
        if self.series_widget is not None:
            self.series_widget.set_playhead(self.row)

    def _gated(self, row: int) -> bool:
        if not self.series_result or "gate" not in self.series_result:
            return False
        gate = self.series_result["gate"]
        i = row - self.series_start
        return 0 <= i < len(gate) and bool(gate[i])

    def _report(self) -> None:
        rep = self.chain.report()
        parts = [f"decodes {rep['decodes']}", f"memo {rep['memo_entries']}"]
        parts += [f"{s['stage']} {s['runs']}x {s['ms_per_run']:.1f}ms" for s in rep["stages"]]
        parts.append(f"series rows {self.series_rows}/{self.loop_len.value()}")
        self.statusBar().showMessage("   ".join(parts))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._render()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.timer.stop()
        self.worker.stop()
        super().closeEvent(event)


def to_rgb(data: np.ndarray, display: str) -> np.ndarray:
    """Any tool output as an RGB uint8 picture the label can show."""
    arr = np.asarray(data)
    if display == "grid":
        finite = arr[np.isfinite(arr)]
        hi = float(np.percentile(finite, 99)) if finite.size else 1.0
        scaled = np.clip(np.nan_to_num(arr) / max(hi, 1e-9), 0, 1)
        u8 = (scaled * 255).astype(np.uint8)
        u8 = cv2.resize(u8, (arr.shape[1] * 16, arr.shape[0] * 16), interpolation=cv2.INTER_NEAREST)
        return cv2.cvtColor(cv2.applyColorMap(u8, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        return np.ascontiguousarray(cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB))
    return np.ascontiguousarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))
