from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.band_plot import DIM, LINE, PANEL, TEXT, plot_font
from sieve.gui.chain_model import (
    ChainKind,
    DetectorState,
    DetectorUpdate,
    LiveChain,
    Status,
    grade,
)
from sieve.gui.count_plot import CountPlot
from sieve.gui.density_plot import DensityPlot, DensitySurface
from sieve.gui.param_form import param_rows
from sieve.gui.wizard_model import (
    Candidate,
    CatalogEntry,
    candidates_for_insert,
    candidates_for_swap,
    guidance_for,
    insert_step,
    swap_step,
)


_SCRIM = QColor(12, 13, 15, 150)

_STAGE_ROLE = Qt.ItemDataRole.UserRole
_DISARMED = "disarmed — place the count threshold"
_CHAIN_INCOMPLETE = "chain incomplete — see the stack"


def last_image_node_id(chain: LiveChain) -> str | None:
    found: str | None = None
    for step, step_grade in zip(chain.steps, grade(chain.steps), strict=True):
        if step_grade.status is not Status.OK or step.node is None:
            break
        if step.kind_out is ChainKind.IMAGE:
            found = step.node.node_id
    return found


def frame_to_qimage(frame: NDArray[Any]) -> QImage | None:
    data = np.asarray(frame)
    if data.ndim == 3 and data.shape[2] == 3:
        contiguous = np.ascontiguousarray(data.astype(np.uint8, copy=False))
        height, width = contiguous.shape[:2]
        return QImage(
            contiguous.tobytes(), width, height, width * 3, QImage.Format.Format_BGR888
        ).copy()
    if data.ndim == 2:
        gray = np.clip(data, 0, 255).astype(np.uint8)
        height, width = gray.shape
        return QImage(
            np.ascontiguousarray(gray).tobytes(),
            width,
            height,
            width,
            QImage.Format.Format_Grayscale8,
        ).copy()
    return None


class _FramePane(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image: QImage | None = None
        self.setMinimumHeight(180)

    def show_frame(self, image: QImage | None) -> None:
        self._image = image
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL)
        if self._image is None or self._image.isNull():
            painter.setPen(DIM)
            painter.setFont(plot_font(9))
            painter.drawText(
                self.rect(),
                int(Qt.AlignmentFlag.AlignCenter),
                "waiting for a preview frame",
            )
            painter.end()
            return
        scaled = self._image.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()


class StepWizard(QWidget):
    chain_proposed = Signal(object, str)

    hover_preview = Signal(object)

    hover_ended = Signal()
    accepted = Signal()
    cancelled = Signal()

    def __init__(
        self,
        chain: LiveChain,
        target: int | str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._original = chain
        self._target = target
        self._selected: CatalogEntry | None = None
        self._provisional: LiveChain | None = None
        self._provisional_id: str | None = None
        self._params: dict[str, dict[str, object]] = {}
        if isinstance(target, int):
            self._candidates = candidates_for_insert(chain, target)
            heading = "INSERT A STEP"
        else:
            self._candidates = candidates_for_swap(chain, target)
            step = next(s for s in chain.steps if s.step_id == target)
            heading = f"REPLACE {step.title.upper()}"
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._build(heading)
        self._populate()

    def start(self) -> None:
        self._select_initial()

    def _build(self, heading: str) -> None:
        self._panel = QWidget(self)
        self._panel.setObjectName("wizardPanel")
        self._panel.setStyleSheet(
            f"#wizardPanel {{background: {PANEL.name()}; border: 1px solid {LINE.name()};"
            " border-radius: 8px;}"
        )
        title = QLabel(heading)
        title.setFont(plot_font(9, bold=True, spaced=True))
        title.setStyleSheet(f"color: {DIM.name()};")
        self._search = QLineEdit()
        self._search.setPlaceholderText("search operations")
        self._search.textChanged.connect(self._filter_rows)
        self._list = QListWidget()
        self._list.setMouseTracking(True)
        self._list.itemEntered.connect(self._on_row_hovered)
        self._list.itemClicked.connect(self._on_row_clicked)
        self._list.viewport().installEventFilter(self)
        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(self._search)
        left.addWidget(self._list, 1)
        self._frame_pane = _FramePane()
        self.density = DensityPlot()
        self.density.setMinimumHeight(140)
        self.count = CountPlot()
        self.count.setMinimumHeight(140)
        self.d_slider = QSlider(Qt.Orientation.Horizontal)
        self.d_slider.setRange(1, 600)
        self._d_label = QLabel()
        self.centered = QCheckBox("centered")
        self._summary = QLabel()
        d_row = QHBoxLayout()
        d_row.addWidget(self._d_label)
        d_row.addWidget(self.d_slider, 1)
        d_row.addWidget(self.centered)
        d_row.addWidget(self._summary)
        center = QVBoxLayout()
        center.setSpacing(4)
        center.addWidget(self._frame_pane, 3)
        center.addWidget(self.density, 2)
        center.addWidget(self.count, 2)
        center.addLayout(d_row)
        self._step_title = QLabel()
        self._step_title.setFont(plot_font(10, bold=True))
        self._step_title.setStyleSheet(f"color: {TEXT.name()};")
        self._settings_host = QWidget()
        self._settings = QVBoxLayout(self._settings_host)
        self._settings.setContentsMargins(0, 0, 0, 0)
        self._settings.setSpacing(4)
        self._guidance = QLabel()
        self._guidance.setTextFormat(Qt.TextFormat.MarkdownText)
        self._guidance.setWordWrap(True)
        self._guidance.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._guidance.setStyleSheet(f"color: {DIM.name()};")
        guidance_scroll = QScrollArea()
        guidance_scroll.setWidgetResizable(True)
        guidance_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        guidance_scroll.setWidget(self._guidance)
        self._add = QPushButton("Add")
        self._add.setEnabled(False)
        self._add.clicked.connect(self._on_add)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.cancelled)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self._add)
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(self._step_title)
        right.addWidget(self._settings_host)
        right.addWidget(guidance_scroll, 1)
        right.addLayout(buttons)
        columns = QHBoxLayout(self._panel)
        columns.setContentsMargins(16, 12, 16, 12)
        columns.setSpacing(14)
        outer_left = QVBoxLayout()
        outer_left.addWidget(title)
        outer_left.addLayout(left, 1)
        columns.addLayout(outer_left, 3)
        columns.addLayout(center, 5)
        columns.addLayout(right, 4)

    def _populate(self) -> None:
        last_stage = None
        for candidate in self._candidates:
            if candidate.entry.stage is not last_stage:
                last_stage = candidate.entry.stage
                header = QListWidgetItem(str(last_stage).upper())
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                header.setFont(plot_font(7, bold=True, spaced=True))
                self._list.addItem(header)
            item = QListWidgetItem(self._row_text(candidate))
            item.setData(_STAGE_ROLE, candidate.entry.entry_id)
            item.setToolTip(candidate.entry.blurb)
            if not candidate.enabled:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(item)

    @staticmethod
    def _row_text(candidate: Candidate) -> str:
        if candidate.enabled:
            return candidate.entry.title
        return f"{candidate.entry.title} — {candidate.reason}"

    def _select_initial(self) -> None:
        wanted = self._target if isinstance(self._target, str) else None
        enabled = [c for c in self._candidates if c.enabled]
        first = next((c for c in enabled if c.entry.entry_id == wanted), None)
        if first is None and enabled:
            first = enabled[0]
        if first is not None:
            self.select_entry(first.entry.entry_id)

    def _candidate(self, entry_id: str) -> Candidate | None:
        return next((c for c in self._candidates if c.entry.entry_id == entry_id), None)

    def _propose(self, entry: CatalogEntry) -> tuple[LiveChain, str]:
        params = self._params.get(entry.entry_id)
        if isinstance(self._target, int):
            return insert_step(self._original, self._target, entry, params)
        return swap_step(self._original, self._target, entry, params)

    def select_entry(self, entry_id: str) -> bool:
        candidate = self._candidate(entry_id)
        if candidate is None or not candidate.enabled:
            return False
        self._selected = candidate.entry
        self._provisional, self._provisional_id = self._propose(candidate.entry)
        self._add.setEnabled(True)
        self._mark_selected_row(entry_id)
        self._rebuild_settings()
        self.chain_proposed.emit(self._provisional, self._provisional_id)
        return True

    def _mark_selected_row(self, entry_id: str) -> None:
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item.data(_STAGE_ROLE) == entry_id:
                self._list.setCurrentItem(item)
                return

    def _on_row_clicked(self, item: QListWidgetItem) -> None:
        entry_id = item.data(_STAGE_ROLE)
        if isinstance(entry_id, str):
            self.select_entry(entry_id)

    def _on_row_hovered(self, item: QListWidgetItem) -> None:
        entry_id = item.data(_STAGE_ROLE)
        candidate = self._candidate(entry_id) if isinstance(entry_id, str) else None
        if candidate is None or not candidate.enabled:
            self.hover_ended.emit()
            return
        if (
            self._selected is not None
            and candidate.entry.entry_id == self._selected.entry_id
        ):
            self.hover_ended.emit()
            return
        hypothetical, _ = self._propose(candidate.entry)
        self.hover_preview.emit(hypothetical)

    def eventFilter(self, watched: object, event: Any) -> bool:
        if watched is self._list.viewport() and event.type() == event.Type.Leave:
            self.hover_ended.emit()
        return False

    def _filter_rows(self, needle: str) -> None:
        wanted = needle.strip().lower()
        for index in range(self._list.count()):
            item = self._list.item(index)
            entry_id = item.data(_STAGE_ROLE)
            if not isinstance(entry_id, str):
                continue
            candidate = self._candidate(entry_id)
            haystack = (
                ""
                if candidate is None
                else (f"{candidate.entry.title} {candidate.entry.blurb}".lower())
            )
            item.setHidden(bool(wanted) and wanted not in haystack)

    def _rebuild_settings(self) -> None:
        while self._settings.count():
            item = self._settings.takeAt(0)
            widget = None if item is None else item.widget()
            if widget is not None:
                widget.deleteLater()
        entry = self._selected
        if entry is None or self._provisional is None:
            return
        self._step_title.setText(entry.title)
        step = next(
            s for s in self._provisional.steps if s.step_id == self._provisional_id
        )
        if step.node is not None:
            for row in param_rows(step.node, entry.hidden_params, self._on_param_edit):
                self._settings.addWidget(row)
        else:
            note = QLabel("its parameters are the graphs below — drag them")
            note.setStyleSheet(f"color: {DIM.name()};")
            self._settings.addWidget(note)
        guidance = guidance_for(entry)
        parts = [f"**{guidance.summary}**"]
        if guidance.when_to_use:
            parts.append(f"### When to use it\n\n{guidance.when_to_use}")
        if guidance.not_do:
            parts.append(f"### What it does not do\n\n{guidance.not_do}")
        if guidance.cost:
            parts.append(f"### Cost\n\n{guidance.cost}")
        self._guidance.setText("\n\n".join(parts))

    def _on_param_edit(self, name: str, value: object) -> None:
        if self._selected is None:
            return
        self._params.setdefault(self._selected.entry_id, {})[name] = value
        self._provisional, self._provisional_id = self._propose(self._selected)
        self.chain_proposed.emit(self._provisional, self._provisional_id)

    def show_frame(self, image: QImage | None) -> None:
        self._frame_pane.show_frame(image)

    def apply_state(
        self,
        *,
        update: DetectorUpdate | None,
        surface: DensitySurface | None = None,
        start: int,
        frames: int,
        detector: DetectorState,
        fps: float,
        temporal_ok: bool,
        detection_ok: bool,
        playhead: int,
    ) -> None:
        seconds = detector.window_frames / fps if fps > 0 else 0.0
        self._d_label.setText(f"D {detector.window_frames} fr ({seconds:.2f} s)")
        for widget in (self.d_slider, self.centered):
            widget.blockSignals(True)
        self.d_slider.setValue(detector.window_frames)
        self.centered.setChecked(detector.centered)
        for widget in (self.d_slider, self.centered):
            widget.blockSignals(False)
        if update is None:
            self.count.set_series(np.zeros(0, np.float32), region_blocks=1, armed=False)
            self.count.set_gate(None)
            self.count.set_notice(
                "no reachable temporal filter step"
                if not temporal_ok
                else "no series yet"
            )
            self._summary.setText(
                _CHAIN_INCOMPLETE if not (temporal_ok and detection_ok) else ""
            )
            return
        blocks = update.band_power.shape[1]
        solo = detector.solo_block
        solo_trace = (
            update.band_power[:, solo] if solo is not None and solo < blocks else None
        )
        self.density.set_series(update.band_power, solo_trace, surface=surface)
        self.density.set_span(start, frames)
        self.density.set_playhead(playhead)
        self.density.set_band(*detector.value_band)
        self.count.set_span(start, frames)
        self.count.set_playhead(playhead)
        self.count.set_series(
            update.windowed, region_blocks=blocks, armed=detector.armed and detection_ok
        )
        self.count.set_gate(update.gate if detection_ok else None)
        if detector.count_frac is None:
            self.count.clear_band()
            self.count.set_notice("" if not detection_ok else _DISARMED)
        else:
            lo, hi = detector.count_frac
            self.count.set_band(
                lo * blocks if np.isfinite(lo) else lo,
                hi * blocks if np.isfinite(hi) else hi,
            )
            self.count.set_notice("")
        if not detection_ok:
            self.count.set_notice("no reachable detection step")
        if not temporal_ok or not detection_ok:
            self._summary.setText(_CHAIN_INCOMPLETE)
        elif update.intervals is None:
            self._summary.setText(_DISARMED)
        else:
            gated = float(update.gate.sum()) / fps if update.gate is not None else 0.0
            self._summary.setText(f"{len(update.intervals)} detections · {gated:.1f} s")

    @property
    def provisional_chain(self) -> LiveChain | None:
        return self._provisional

    @property
    def provisional_step_id(self) -> str | None:
        return self._provisional_id

    @property
    def selected_entry(self) -> CatalogEntry | None:
        return self._selected

    @property
    def add_button(self) -> QPushButton:
        return self._add

    @property
    def settings_host(self) -> QWidget:
        return self._settings_host

    @property
    def candidate_list(self) -> QListWidget:
        return self._list

    def candidate_rows(self) -> list[QListWidgetItem]:
        rows: list[QListWidgetItem] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if isinstance(item.data(_STAGE_ROLE), str):
                rows.append(item)
        return rows

    def _on_add(self) -> None:
        if self._selected is not None and self._provisional is not None:
            self.accepted.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: object) -> None:
        del event
        margin = 28
        self._panel.setGeometry(
            margin,
            margin,
            max(0, self.width() - 2 * margin),
            max(0, self.height() - 2 * margin),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _SCRIM)
        painter.end()

    def mousePressEvent(self, event: object) -> None:
        del event
