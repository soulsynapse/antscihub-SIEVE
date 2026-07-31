from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from itertools import count
from math import isfinite
from time import perf_counter

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRect, Qt, Signal, Slot
from PySide6.QtGui import QHideEvent, QImage, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.pipeline_model import ClipRange, CropArtifact
from sieve.core.pool_meter import PoolMeter
from sieve.core.wavelet import default_freqs
from sieve.detect import gate_to
from sieve.filters.block_signal import resolve_block
from sieve.gui.band_plot import DIM
from sieve.gui.block_spin import BlockSpinBox
from sieve.gui.chain_model import (
    SIGNAL_LABELS,
    ChainKind,
    ChainStep,
    DetectorState,
    DetectorUpdate,
    LiveChain,
    Stage,
    Status,
    caption_for,
    parity_chain,
    recompute,
    snapped_band_label,
)
from sieve.gui.chain_stack import MATERIALIZE_PRICE, ChainStackView
from sieve.gui.commit_combo import CommitCombo
from sieve.gui.composite_view import StepCompositeView
from sieve.gui.concurrency import resolve_worker_split
from sieve.gui.count_plot import CountPlot
from sieve.gui.crop_binding import CropBacking, CropState
from sieve.gui.density_plot import DensityPlot, DensitySurface
from sieve.gui.detector_worker import (
    DetectorFailure,
    DetectorRequest,
    DetectorResult,
    DetectorRunner,
    settled_for,
)
from sieve.gui.document import ReplicateDocument
from sieve.gui.graph_hud import GraphHud
from sieve.gui.gray_toggle import GrayToggle
from sieve.gui.materialize_worker import MaterializeRequest, MaterializeRunner
from sieve.gui.param_form import param_rows
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.scalogram_plot import ScalogramPlot
from sieve.gui.series_collector import SeriesCollector
from sieve.gui.wizard import StepWizard, frame_to_qimage, last_image_node_id
from sieve.gui.wizard_model import catalog, chain_from_pipeline


BAND_DRAG_BUDGET = "band_drag_repaint"
KNOB_BUDGET = "knob_to_graphs"


FIRST_PARTIAL_BUDGET = "knob_to_first_partial"


DENSITY_BUDGET = "density_rebuild"


_HEAT_PERCENTILE = 99.5

_CHAIN_INCOMPLETE = "chain incomplete — see the stack"
_DISARMED = "disarmed — place the count threshold"


PLAYBACK_RATES = (1.0, 2.0, 5.0)


class FilterTab(QWidget):
    status_message = Signal(str)

    graphs_updated = Signal()

    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        runner: PreviewRunner,
        parent: QWidget | None = None,
        *,
        metrics: MetricBus | None = None,
        preferences: Preferences | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        self._runner = runner
        self._metrics = METRICS if metrics is None else metrics
        self._preferences = (
            preferences if preferences is not None else Preferences(parent=self)
        )
        self._chain = parity_chain(30.0)
        self._defaults = parity_chain(30.0)
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._series_start: int | None = None
        self._series2d: np.ndarray | None = None
        self._grid: tuple[int, int] = (1, 1)
        self._update: DetectorUpdate | None = None
        self._pooled_power: np.ndarray | None = None
        self._density_surface: DensitySurface | None = None
        self._derive_failure: str | None = None
        self._playhead = 0
        self._detector = DetectorRunner(self)
        self._detector.ready.connect(self._on_detector_ready)
        self._detector.failed.connect(self._on_detector_failed)
        self._span: tuple[int, int] = (0, 0)
        self._filled = 0
        self._settled = 0
        self._series_final = False
        self._knob_armed_at: float | None = None
        self._partial_published = False
        self._heat_source: NDArray[np.float32] | None = None
        self._heat_max = 0.0
        self._selected_step: str | None = None
        self._frame_image: QImage | None = None
        self._composite_grab: list[tuple[np.ndarray | None, np.ndarray, bool]] = []
        self._composite_revisions: set[int] = set()
        self._series_pending = False
        self._composite_outstanding: int | None = None
        self._composite_deferred = False
        self._wizard: StepWizard | None = None
        self._wizard_snapshot: LiveChain | None = None
        self._wizard_undo_index: int | None = None
        self._provisional_id: str | None = None
        self._grab: list[np.ndarray] = []
        self._extra_bodies: dict[str, QWidget] = {}
        self._value_band_memory: dict[str, tuple[float, float]] = {}
        self._gestures = count(1)
        self._d_gesture: int | None = None
        self._materializer = MaterializeRunner(self)
        self._writing_row: int | None = None
        self._build_widgets()
        self._build_layout()
        self._connect()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self._refresh_source_card()

    def _build_widgets(self) -> None:
        self._speed = QToolButton()
        self._speed.setToolTip("Playback speed — click to cycle 1x, 2x, 5x")
        self._speed.setText(f"{self._player.playback_rate:g}x")
        self._gray_toggle = GrayToggle(self._preferences)
        self._composite = StepCompositeView()
        self._count = CountPlot()
        self._scalogram = ScalogramPlot()
        self._scalogram.setMinimumHeight(160)
        self._density = DensityPlot()
        self._density.setMinimumHeight(160)
        self._stack = ChainStackView()
        self._hud = GraphHud()
        self._d_slider = QSlider(Qt.Orientation.Horizontal)
        self._d_slider.setRange(1, 600)
        self._d_label = QLabel()
        self._centered = QCheckBox("centered")
        self._summary = QLabel()
        self._downsample = QDoubleSpinBox()
        self._downsample.setRange(0.05, 1.0)
        self._downsample.setSingleStep(0.05)
        self._downsample.setDecimals(2)
        self._normalize = CommitCombo()
        self._normalize.addItems(["off", "zscore"])
        self._block = BlockSpinBox()
        self._block.setRange(0, 256)
        self._signal_buttons: dict[str, QPushButton] = {}
        for signal_id, label in SIGNAL_LABELS.items():
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _=False, s=signal_id: self._on_signal_switch(s)
            )
            self._signal_buttons[signal_id] = button
        self._detect_note = QLabel("graph and detection window D live under the video")
        self._detect_note.setStyleSheet(f"color: {DIM.name()};")
        self._rescale_row = _row("Downsample", self._downsample)
        self._normalize_row = _row("Normalize", self._normalize)
        self._block_row = _row("Block", self._block)
        self._signal_row = _row("Signal", *self._signal_buttons.values())

    def _build_layout(self) -> None:
        d_row = QHBoxLayout()
        d_row.addWidget(self._d_label)
        d_row.addWidget(self._d_slider, 1)
        d_row.addWidget(self._centered)
        d_row.addWidget(self._summary)
        controls = QHBoxLayout()
        controls.setSpacing(6)
        controls.addStretch(1)
        controls.addWidget(self._speed)
        controls.addWidget(self._gray_toggle)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addLayout(controls)
        left.addWidget(self._composite, 6)
        left.addWidget(self._count, 2)
        left.addLayout(d_row)
        left.addWidget(self._hud, 1)
        columns = QHBoxLayout()
        columns.setSpacing(10)
        columns.addLayout(left, 5)
        columns.addWidget(self._stack, 6)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        layout.addLayout(columns, 1)

    def _connect(self) -> None:
        self._speed.clicked.connect(self._on_speed_clicked)
        self._gray_toggle.luma_changed.connect(self._on_luma_changed)
        self._runner.window_render_changed.connect(self._gray_toggle.set_rendering)
        self._player.frame_changed.connect(self._on_frame_changed)
        self._document.source_changed.connect(self._on_source_changed)
        self._document.clip_changed.connect(self.resubmit)
        self._document.selection_changed.connect(self._on_selection_changed)
        self._document.replicate_changed.connect(self._on_replicate_changed)
        self._document.tuning_changed.connect(self._on_tuning_changed)
        self._document.detector_changed.connect(self._on_detector_changed)
        self._document.pipeline_changed.connect(self._on_pipeline_changed)
        self._runner.opened.connect(self.resubmit)
        self._runner.render_started.connect(self._collector_start)
        self._runner.render_started.connect(self._hud_begin)
        self._runner.frame_cost.connect(self._on_frame_cost)
        self._runner.render_finished.connect(self._on_render_finished)
        self._runner.render_failed.connect(self._on_render_failed)
        card = self._stack.source_card
        card.materialize_requested.connect(self._on_materialize)
        card.cancel_requested.connect(self._materializer.cancel)
        card.discard_requested.connect(self._on_discard_crop)
        self._materializer.progressed.connect(card.set_progress)
        self._materializer.written.connect(self._on_crop_written)
        self._materializer.failed.connect(self._on_crop_failed)
        self._materializer.cancelled.connect(self._on_crop_cancelled)
        self._document.crops_changed.connect(self._refresh_source_card)
        self._document.selection_changed.connect(self._refresh_source_card)
        self._document.replicate_changed.connect(self._refresh_source_card)
        self._document.structure_changed.connect(self._refresh_source_card)
        self._document.clip_changed.connect(self._refresh_source_card)
        self._document.pipeline_changed.connect(self._refresh_source_card)
        self._document.source_changed.connect(self._refresh_source_card)
        self._stack.reset_clicked.connect(self._on_reset)
        self._stack.select_requested.connect(self._on_step_selected)
        self._stack.remove_requested.connect(self._on_remove)
        self._stack.swap_requested.connect(self._on_swap_requested)
        self._stack.insert_requested.connect(self._on_insert_requested)
        self._downsample.valueChanged.connect(self._on_downsample)
        self._normalize.textActivated.connect(self._on_normalize)
        self._block.valueChanged.connect(self._on_block)
        for plot in (self._scalogram, self._density, self._count, self._hud):
            plot.pressed.connect(self._player.seek)
            plot.scrubbed.connect(self._player.scrub)
            plot.committed.connect(self._player.seek)
        self._scalogram.band_changed.connect(self._on_freq_drag)
        self._scalogram.band_committed.connect(self._on_freq_commit)
        self._density.band_changed.connect(self._on_value_drag)
        self._density.band_committed.connect(self._on_value_band)
        self._count.band_changed.connect(self._on_count_drag)
        self._count.band_committed.connect(self._on_count_band)
        self._composite.solo_toggled.connect(self._on_solo)
        self._d_slider.sliderPressed.connect(self._on_d_pressed)
        self._d_slider.sliderReleased.connect(self._on_d_released)
        self._d_slider.valueChanged.connect(self._on_window_frames)
        self._centered.toggled.connect(self._on_centered)

    def shutdown(self) -> None:
        self._detector.shutdown()
        self._materializer.shutdown()

    @property
    def chain(self) -> LiveChain:
        return self._chain

    @property
    def stack(self) -> ChainStackView:
        return self._stack

    @property
    def count_plot(self) -> CountPlot:
        return self._count

    @property
    def scalogram(self) -> ScalogramPlot:
        return self._scalogram

    @property
    def density(self) -> DensityPlot:
        return self._density

    @property
    def downsample_knob(self) -> QDoubleSpinBox:
        return self._downsample

    @property
    def summary_text(self) -> str:
        return self._summary.text()

    @property
    def hud(self) -> GraphHud:
        return self._hud

    @property
    def detector_meter(self) -> PoolMeter:
        return self._detector.meter

    @property
    def composite(self) -> StepCompositeView:
        return self._composite

    @property
    def materializer(self) -> MaterializeRunner:
        return self._materializer

    @property
    def selected_step(self) -> str | None:
        return self._selected_step

    @property
    def gray_toggle(self) -> GrayToggle:
        return self._gray_toggle

    @property
    def speed_button(self) -> QToolButton:
        return self._speed

    @Slot()
    def _on_speed_clicked(self) -> None:
        current = self._player.playback_rate
        index = PLAYBACK_RATES.index(current) if current in PLAYBACK_RATES else 0
        rate = PLAYBACK_RATES[(index + 1) % len(PLAYBACK_RATES)]
        self._player.set_playback_rate(rate)
        self._speed.setText(f"{self._player.playback_rate:g}x")

    @Slot(bool)
    def _on_luma_changed(self, enabled: bool) -> None:
        if self.isVisible():
            self._player.set_viewport_luma(enabled)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._player.set_viewport_luma(self._gray_toggle.effective_luma)
        self._record_visit()

    def _record_visit(self) -> None:
        index = self._document.selected_index
        if index is not None:
            self._document.mark_visited(index)

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        self._player.set_viewport_luma(False)

    def _fps(self) -> float:
        return self._document.source_fps or 30.0

    def _block_step(self):
        steps = self._chain.steps
        return next(
            (
                s
                for s in steps
                if s.node is not None and s.node.filter_id == "block_signal"
            ),
            None,
        )

    def _block_node_id(self) -> str | None:
        step = self._block_step()
        return None if step is None or step.node is None else step.node.node_id

    def _set_node_params(self, filter_id: str, **params: object) -> None:
        steps = tuple(
            replace(
                s,
                node=s.node.model_copy(update={"params": {**s.node.params, **params}}),
            )
            if s.node is not None and s.node.filter_id == filter_id
            else s
            for s in self._chain.steps
        )
        self._chain = replace(self._chain, steps=steps)

    def _set_detector(self, detector: DetectorState) -> None:
        self._chain = replace(self._chain, detector=detector)

    def _node_id_for(self, filter_id: str) -> str | None:
        for step in self._chain.steps:
            if step.node is not None and step.node.filter_id == filter_id:
                return step.node.node_id
        return None

    def _submit_params(
        self, changes_by_filter: dict[str, dict[str, object]], text: str
    ) -> None:
        by_node: dict[str, Mapping[str, object]] = {}
        for filter_id, params in changes_by_filter.items():
            node_id = self._node_id_for(filter_id)
            if node_id is None or node_id not in self._document.pipeline:
                by_node = {}
                break
            by_node[node_id] = params
        if not by_node:
            for filter_id, params in changes_by_filter.items():
                self._set_node_params(filter_id, **params)
            self._knob_edited()
            return
        index = self._document.undo_stack.index()
        self._knob_armed_at = perf_counter()
        self._document.edit_params(by_node, text)
        if self._document.undo_stack.index() == index:
            self._knob_armed_at = None

    def _submit_detector(
        self, changes: dict[str, object], text: str, *, gesture: int | None = None
    ) -> None:
        if not len(self._document.pipeline.nodes):
            detector = self._chain.detector
            updated = replace(detector, **changes)
            if updated.freq_band == detector.freq_band:
                self._cheap_retune(updated)
            else:
                self._set_detector(updated)
                self._derive(reuse_band_power=False)
            return
        self._document.edit_detector(changes, text, gesture=gesture)

    @Slot(int)
    def _on_replicate_changed(self, index: int) -> None:
        if index != self._document.selected_index:
            return
        self._refresh_from_document()
        self.resubmit()

    @Slot()
    def _on_tuning_changed(self) -> None:
        self._refresh_from_document()
        self.resubmit()

    @Slot()
    def _on_detector_changed(self) -> None:
        previous = self._chain.detector
        resolved = DetectorState.from_settings(
            self._document.resolved_detector_for_selection(),
            solo_block=previous.solo_block,
        )
        if resolved == previous:
            self._sync_widgets_from_chain()
            return
        self._set_detector(resolved)
        self._sync_widgets_from_chain()
        self._stack.update_captions(self._captions())
        self._derive(reuse_band_power=resolved.freq_band == previous.freq_band)

    @Slot()
    def _on_pipeline_changed(self) -> None:
        document_ids = [node.node_id for node in self._document.pipeline.nodes]
        chain_ids = [
            step.node.node_id for step in self._chain.steps if step.node is not None
        ]
        if document_ids == chain_ids:
            return
        try:
            rebuilt = chain_from_pipeline(self._document.pipeline, self._fps())
        except Exception as error:
            self.status_message.emit(f"cannot display the loaded graph: {error}")
            return
        self._chain = rebuilt
        self._defaults = parity_chain(self._fps())
        for step in rebuilt.steps:
            if step.node is not None:
                self._ensure_body(step.step_id)
        self._refresh_from_document()
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._selected_step = None
        self._rebuild_stack()
        self._apply()
        self.resubmit()

    def _refresh_from_document(self) -> None:
        document = self._document
        steps = tuple(
            replace(
                step,
                node=step.node.model_copy(
                    update={"params": document.resolved_node_params(step.node.node_id)}
                ),
            )
            if step.node is not None and step.node.node_id in document.pipeline
            else step
            for step in self._chain.steps
        )
        detector = DetectorState.from_settings(
            document.resolved_detector_for_selection(),
            solo_block=self._chain.detector.solo_block,
        )
        self._chain = replace(self._chain, steps=steps, detector=detector)
        self._sync_widgets_from_chain()
        self._stack.update_captions(self._captions())

    @Slot()
    def resubmit(self) -> None:
        window = self._document.window
        if window is None:
            return
        node_id = self._block_node_id()
        if node_id is not None and node_id != self._collector.node_id:
            self._collector = SeriesCollector(node_id)
        collector = self._collector
        replicate = self._document.selected_replicate
        expected = self._runner.revision + 1
        grabber = self._grabber(self._chain) if self._wizard is not None else None
        composite = self._composite_grabber()
        def feed(result: object) -> None:
            collector.add(expected, result)  # type: ignore[arg-type]
            if grabber is not None:
                grabber(result)
            if composite is not None:
                composite(result)
        if self._runner.request_render(
            self._chain.pipeline(), window, replicate, consumer=feed
        ):
            self._series_pending = True
            self._composite_outstanding = None
            self._composite_deferred = False
            self._span = (window.start, window.frame_count)
            self._filled = 0
            self._settled = 0
            self._series_final = False

    def _grabber(self, chain: LiveChain):
        window = self._document.window
        node_id = last_image_node_id(chain)
        if window is None or node_id is None:
            return None
        want = min(max(self._playhead, window.start), window.end - 1)
        slot = self._grab
        def grab(result: object) -> None:
            frame = getattr(result, "outputs", {}).get(node_id)
            if frame is not None and getattr(result, "index", None) == want:
                slot[:] = [np.asarray(frame.data)]
        return grab

    @Slot(int)
    def _collector_start(self, revision: int) -> None:
        if revision in self._composite_revisions:
            return
        self._collector.start(revision)
        self._detector.set_revision(revision)

    @Slot(int)
    def _hud_begin(self, revision: int) -> None:
        self._composite_revisions = {
            r for r in self._composite_revisions if r >= revision
        }
        if revision in self._composite_revisions:
            return
        window = self._document.window
        if window is not None:
            self._hud.set_span(window.start, window.frame_count)
        self._hud.begin()

    @Slot(int, float)
    def _on_frame_cost(self, index: int, elapsed_ms: float) -> None:
        if self._wizard is not None and self._grab:
            self._wizard.show_frame(frame_to_qimage(self._grab.pop()))
        if self._composite_grab:
            self._apply_composite(*self._composite_grab.pop())
        if self._runner.revision in self._composite_revisions:
            return
        self._hud.add_cost(index, elapsed_ms)
        self._kick_partial()

    def _kick_partial(self, *, final: bool = False) -> None:
        if not final and (self._detector.busy or not self._series_pending):
            return
        series = self._collector.snapshot_rows(self._runner.revision)
        if series is None or (not final and len(series.rows) <= self._filled):
            return
        self._detector.submit(
            DetectorRequest(
                revision=self._runner.revision,
                series=series.rows,
                start_index=series.start_index,
                fps=self._fps(),
                state=self._chain.detector,
                final=final,
            )
        )

    def _release_composite_slot(self) -> None:
        self._composite_outstanding = None
        if self._composite_deferred:
            self._composite_deferred = False
            self._refresh_composite()

    @Slot(object)
    def _on_render_finished(self, render: object) -> None:
        del render
        self._series_pending = False
        if self._wizard is not None and self._grab:
            self._wizard.show_frame(frame_to_qimage(self._grab.pop()))
        if self._composite_grab:
            self._apply_composite(*self._composite_grab.pop())
        if self._collector.snapshot_rows(self._runner.revision) is not None:
            self._kick_partial(final=True)
        self._release_composite_slot()

    @Slot(object)
    def _on_detector_ready(self, result: DetectorResult) -> None:
        self._derive_failure = None
        self._series_start = result.start_index
        self._series2d = result.series2d
        self._grid = result.grid
        self._update = result.update
        self._pooled_power = result.pooled_power
        self._density_surface = result.density
        self._metrics.publish(
            DENSITY_BUDGET, result.density_ms, detail=f"B = {result.density.blocks:,}"
        )
        self._filled = result.frames
        self._settled = result.settled
        self._series_final = result.final
        if self._knob_armed_at is not None:
            elapsed = (perf_counter() - self._knob_armed_at) * 1000.0
            if result.final:
                self._metrics.publish(KNOB_BUDGET, elapsed)
                self._knob_armed_at = None
                self._partial_published = False
            elif not self._partial_published:
                self._metrics.publish(FIRST_PARTIAL_BUDGET, elapsed)
                self._partial_published = True
        self._apply()
        if result.final:
            self.graphs_updated.emit()
        else:
            self._kick_partial()

    @Slot(object)
    def _on_detector_failed(self, failure: DetectorFailure) -> None:
        self._derive_failure = failure.message
        self._apply()

    @Slot(str)
    def _on_render_failed(self, message: str) -> None:
        del message
        self._series_pending = False
        self._release_composite_slot()

    def _reachable(self) -> tuple[bool, bool]:
        temporal = False
        for step, grade in zip(self._chain.steps, self._chain.grades(), strict=True):
            if step.stage is Stage.TEMPORAL_FILTER and grade.status is Status.OK:
                temporal = True
        return temporal, self._chain.detection_reachable()

    def _derive(self, *, reuse_band_power: bool) -> None:
        temporal_ok, _ = self._reachable()
        if self._series_start is None or self._series2d is None or not temporal_ok:
            self._update = None
            self._apply()
            return
        band_power = (
            self._update.band_power
            if reuse_band_power and self._update is not None
            else None
        )
        update = recompute(
            self._series2d,
            self._fps(),
            self._chain.detector,
            start_index=self._series_start,
            band_power=band_power,
            workers=resolve_worker_split().detector,
        )
        self._settled = settled_for(
            self._filled, self._fps(), self._chain.detector, final=self._series_final
        )
        self._update = gate_to(update, self._settled, self._series_start)
        self._apply()

    def _heat_scale(self, band_power: NDArray[np.float32]) -> float:
        if band_power is not self._heat_source:
            self._heat_source = band_power
            self._heat_max = float(np.percentile(band_power, _HEAT_PERCENTILE))
        return self._heat_max

    def _apply(self) -> None:
        detector = self._chain.detector
        fps = self._fps()
        temporal_ok, detection_ok = self._reachable()
        update = self._update
        seconds = detector.window_frames / fps if fps > 0 else 0.0
        self._d_label.setText(f"D {detector.window_frames} fr ({seconds:.2f} s)")
        if update is None or self._series_start is None:
            self._count.set_series(
                np.zeros(0, np.float32), region_blocks=1, armed=False
            )
            self._count.set_gate(None)
            if self._derive_failure is not None:
                self._count.set_notice(
                    f"the graphs did not derive — {self._derive_failure}"
                )
            elif not temporal_ok:
                self._count.set_notice("no reachable temporal filter step")
            elif not detection_ok:
                self._count.set_notice("no reachable detection step")
            else:
                self._count.set_notice("no series yet — waiting for a render")
            self._composite.set_grid_caption("")
            self._composite.set_block_state(
                np.zeros(1, np.float32), np.zeros(1, bool), None
            )
            if not temporal_ok or not detection_ok:
                self._summary.setText(_CHAIN_INCOMPLETE)
            else:
                self._summary.setText("")
            self._push_wizard_state(None, 0, 0, temporal_ok, detection_ok)
            return
        start, span = (
            self._span if self._span[1] > 0 else (self._series_start, self._filled)
        )
        frames = self._filled
        blocks = update.band_power.shape[1]
        signal = self._signal_label()
        freqs = default_freqs(fps)
        if self._pooled_power is not None:
            self._scalogram.set_power(self._pooled_power, freqs, fps)
        self._scalogram.set_span(start, span)
        self._scalogram.set_filled(frames, self._settled)
        self._scalogram.set_playhead(self._playhead)
        self._scalogram.set_band(
            max(detector.freq_band[0], float(freqs[0])),
            min(detector.freq_band[1], float(freqs[-1])),
        )
        self._scalogram.set_readout(
            f"{snapped_band_label(detector.freq_band, fps)} · {signal}"
        )
        solo = detector.solo_block
        solo_trace = (
            update.band_power[:, solo] if solo is not None and solo < blocks else None
        )
        self._density.set_series(
            update.band_power, solo_trace, surface=self._density_surface
        )
        self._density.set_span(start, span)
        self._density.set_filled(frames, self._settled)
        self._density.set_playhead(self._playhead)
        self._density.set_band(*detector.value_band)
        self._count.set_span(start, span)
        self._count.set_filled(frames, self._settled)
        self._count.set_playhead(self._playhead)
        self._count.set_series(
            update.windowed, region_blocks=blocks, armed=detector.armed and detection_ok
        )
        self._count.set_gate(update.gate if detection_ok else None)
        if detector.count_frac is None:
            self._count.clear_band()
            self._count.set_notice("" if not detection_ok else _DISARMED)
        else:
            lo, hi = detector.count_frac
            self._count.set_band(
                lo * blocks if isfinite(lo) else lo,
                hi * blocks if isfinite(hi) else hi,
            )
            self._count.set_notice("")
        if not detection_ok:
            self._count.set_notice("no reachable detection step")
        ny, nx = self._grid
        self._composite.set_grid(ny, nx)
        self._composite.set_scale_max(self._heat_scale(update.band_power))
        self._composite.set_grid_caption(
            f"{signal} · {ny}x{nx} blocks · hover solos, click pins"
        )
        self._apply_block_state()
        if not temporal_ok or not detection_ok:
            self._summary.setText(_CHAIN_INCOMPLETE)
        elif update.intervals is None:
            self._summary.setText(_DISARMED)
        else:
            gated = float(update.gate.sum()) / fps if update.gate is not None else 0.0
            suffix = "" if self._series_final else " · filling"
            self._summary.setText(
                f"{len(update.intervals)} detections · {gated:.1f} s{suffix}"
            )
        self._stack.update_captions(self._captions())
        self._push_wizard_state(update, start, frames, temporal_ok, detection_ok)

    def _push_wizard_state(
        self,
        update: DetectorUpdate | None,
        start: int,
        frames: int,
        temporal_ok: bool,
        detection_ok: bool,
    ) -> None:
        if self._wizard is None:
            return
        self._wizard.apply_state(
            update=update,
            surface=self._density_surface,
            start=start,
            frames=frames,
            detector=self._chain.detector,
            fps=self._fps(),
            temporal_ok=temporal_ok,
            detection_ok=detection_ok,
            playhead=self._playhead,
        )

    def _apply_block_state(self) -> None:
        update = self._update
        if update is None or self._series_start is None:
            return
        row = self._playhead - self._series_start
        row = min(max(row, 0), update.band_power.shape[0] - 1)
        values = update.band_power[row]
        lo, hi = self._chain.detector.value_band
        in_band = (values >= lo) & (values <= hi)
        self._composite.set_block_state(
            values, in_band, self._chain.detector.solo_block
        )

    def _signal_label(self) -> str:
        step = self._block_step()
        if step is None or step.node is None:
            return ""
        signal = str(step.node.params.get("signal", ""))
        return SIGNAL_LABELS.get(signal, signal)

    def _captions(self) -> dict[str, str]:
        fps = self._fps()
        return {
            step.step_id: caption_for(step, self._chain.detector, fps)
            for step in self._chain.steps
        }

    def _rebuild_stack(self) -> None:
        self._ensure_selection()
        self._update_composite_caption()
        captions = self._captions()
        bodies: dict[str, tuple[QWidget, ...]] = {
            "rescale": (self._rescale_row,),
            "normalize": (self._normalize_row,),
            "block_signal": (self._block_row, self._signal_row),
            "morlet_band": (self._scalogram, self._density),
            "windowed_count": (self._detect_note,),
        }
        bodies.update(
            {step_id: (body,) for step_id, body in self._extra_bodies.items()}
        )
        self._stack.rebuild(
            self._chain.steps,
            self._chain.grades(),
            [captions[step.step_id] for step in self._chain.steps],
            bodies,
            provisional=self._provisional_id,
            selected=self._selected_step,
        )

    def _sync_widgets_from_chain(self) -> None:
        knobs = (
            self._downsample,
            self._normalize,
            self._block,
            self._d_slider,
            self._centered,
        )
        for widget in knobs:
            widget.blockSignals(True)
        try:
            for step in self._chain.steps:
                node = step.node
                if node is None:
                    continue
                if node.filter_id == "rescale":
                    self._downsample.setValue(float(node.params["scale"]))
                elif node.filter_id == "normalize":
                    self._normalize.setCurrentText(str(node.params["mode"]))
                elif node.filter_id == "block_signal":
                    self._block.setValue(int(node.params["block"]))
                    self._block.setSpecialValueText(
                        f"auto ({resolve_block(0, float(node.params['scale']))})"
                    )
                    for signal_id, button in self._signal_buttons.items():
                        button.setChecked(signal_id == str(node.params["signal"]))
            self._d_slider.setValue(self._chain.detector.window_frames)
            self._centered.setChecked(self._chain.detector.centered)
        finally:
            for widget in knobs:
                widget.blockSignals(False)

    @Slot(str)
    def _on_step_selected(self, step_id: str) -> None:
        if step_id == self._selected_step:
            return
        self._selected_step = step_id
        self._stack.set_selected(step_id)
        self._update_composite_caption()
        self._refresh_composite()

    def _ensure_selection(self) -> None:
        ids = {step.step_id for step in self._chain.steps}
        if self._selected_step in ids:
            return
        last_ok = None
        for step, step_grade in zip(
            self._chain.steps, self._chain.grades(), strict=True
        ):
            if step_grade.status is Status.OK:
                last_ok = step.step_id
        self._selected_step = last_ok

    def _composite_target(self) -> tuple[str | None, ChainStep] | None:
        steps = self._chain.steps
        ids = [step.step_id for step in steps]
        limit = (
            ids.index(self._selected_step)
            if self._selected_step in ids
            else len(steps) - 1
        )
        target: ChainStep | None = None
        upstream: str | None = None
        for index, (step, step_grade) in enumerate(
            zip(steps, self._chain.grades(), strict=True)
        ):
            if step_grade.status is not Status.OK or step.node is None or index > limit:
                break
            if target is not None and target.node is not None:
                upstream = target.node.node_id
            target = step
        return None if target is None else (upstream, target)

    def _update_composite_caption(self) -> None:
        target = self._composite_target()
        if target is None:
            self._composite.set_caption("")
            self._composite.set_notice("no runnable step to compose")
            self._composite.set_grid_visible(False)
            return
        _, step = target
        caption = step.title
        if step.step_id != self._selected_step:
            caption = f"{step.title} (deepest rendered)"
        self._composite.set_caption(caption)
        self._composite.set_grid_visible(step.kind_out is ChainKind.BLOCK_SERIES)

    def _composite_grabber(self):
        window = self._document.window
        target = self._composite_target()
        if window is None or target is None:
            return None
        upstream, step = target
        if step.node is None:
            return None
        node_id = step.node.node_id
        is_grid = step.kind_out is ChainKind.BLOCK_SERIES
        base_is_over = (
            upstream is None
            and step.node.filter_id == "rescale"
            and float(step.node.params.get("scale", 1.0)) >= 1.0
        )
        want = min(max(self._playhead, window.start), window.end - 1)
        slot = self._composite_grab
        def grab(result: object) -> None:
            if getattr(result, "index", None) != want:
                return
            outputs = getattr(result, "outputs", {})
            over = outputs.get(node_id)
            if over is None:
                return
            fallthrough = outputs.get(upstream) if upstream is not None else None
            base = over if base_is_over else fallthrough
            slot[:] = [
                (
                    None if base is None else np.asarray(base.data),
                    np.asarray(over.data),
                    is_grid,
                )
            ]
        return grab

    def _refresh_composite(self) -> None:
        if self._series_pending:
            return
        if self._composite_outstanding is not None:
            self._composite_deferred = True
            return
        window = self._document.window
        grab = self._composite_grabber()
        if window is None or grab is None:
            return
        want = min(max(self._playhead, window.start), window.end - 1)
        replicate = self._document.selected_replicate
        expected = self._runner.revision + 1
        self._composite_revisions.add(expected)
        if self._runner.request_frame(
            self._chain.pipeline(), want, replicate, consumer=grab
        ):
            self._composite_outstanding = expected
            self._composite_deferred = False
        else:
            self._composite_revisions.discard(expected)

    def _apply_composite(
        self, base: np.ndarray | None, over: np.ndarray, is_grid: bool
    ) -> None:
        base_image = (
            self._cropped_player_frame() if base is None else frame_to_qimage(base)
        )
        over_image = None if is_grid else frame_to_qimage(over)
        self._composite.set_frames(base_image, over_image)
        self._composite.set_grid_visible(is_grid)

    def _cropped_player_frame(self) -> QImage | None:
        image = self._frame_image
        if image is None:
            return None
        replicate = self._document.selected_replicate
        source = self._document.source_size
        if replicate is None or source is None:
            return image
        roi = replicate.roi
        scale_x = image.width() / source[0]
        scale_y = image.height() / source[1]
        rect = QRect(
            round(roi.x * scale_x),
            round(roi.y * scale_y),
            round(roi.width * scale_x),
            round(roi.height * scale_y),
        ).intersected(image.rect())
        return image.copy(rect) if not rect.isEmpty() else image

    def _knob_edited(self) -> None:
        self._stack.update_captions(self._captions())
        self._knob_armed_at = perf_counter()
        self.resubmit()

    @Slot(float)
    def _on_downsample(self, scale: float) -> None:
        self._block.setSpecialValueText(f"auto ({resolve_block(0, scale)})")
        self._submit_params(
            {"rescale": {"scale": scale}, "block_signal": {"scale": scale}},
            "Set Downsample",
        )

    @Slot(str)
    def _on_normalize(self, mode: str) -> None:
        self._submit_params({"normalize": {"mode": mode}}, "Set Normalize")

    @Slot(int)
    def _on_block(self, block: int) -> None:
        self._submit_params({"block_signal": {"block": block}}, "Set Block Size")

    def _on_signal_switch(self, signal_id: str) -> None:
        step = self._block_step()
        old_signal = (
            str(step.node.params.get("signal", ""))
            if step is not None and step.node
            else ""
        )
        for other_id, button in self._signal_buttons.items():
            button.setChecked(other_id == signal_id)
        if old_signal == signal_id:
            return
        detector = self._chain.detector
        restored = detector.value_band
        if old_signal:
            self._value_band_memory[old_signal] = detector.value_band
            restored = self._value_band_memory.get(
                signal_id, DetectorState().value_band
            )
        node_id = self._node_id_for("block_signal")
        if (
            node_id is not None
            and node_id in self._document.pipeline
            and self._wizard is None
        ):
            stack = self._document.undo_stack
            stack.beginMacro(f"Switch Signal to {SIGNAL_LABELS[signal_id]}")
            try:
                if restored != detector.value_band:
                    self._document.edit_detector(
                        {"value_band": restored}, "Set Value Band"
                    )
                self._knob_armed_at = perf_counter()
                self._document.edit_params(
                    {node_id: {"signal": signal_id}}, "Set Signal"
                )
            finally:
                stack.endMacro()
        else:
            if restored != detector.value_band:
                self._set_detector(replace(detector, value_band=restored))
            self._set_node_params("block_signal", signal=signal_id)
            self._knob_edited()
        self.status_message.emit(
            f"signal → {SIGNAL_LABELS[signal_id]} (value band remembered per signal)"
        )

    def _cheap_retune(self, detector: DetectorState) -> None:
        self._set_detector(detector)
        started = perf_counter()
        self._derive(reuse_band_power=True)
        self._metrics.publish(BAND_DRAG_BUDGET, (perf_counter() - started) * 1000.0)

    def _on_freq_drag(self, lo: float, hi: float) -> None:
        detector = replace(self._chain.detector, freq_band=(lo, hi))
        self._set_detector(detector)
        fps = self._fps()
        self._scalogram.set_readout(
            f"{snapped_band_label(detector.freq_band, fps)} · {self._signal_label()}"
        )
        self._stack.update_captions(self._captions())

    def _on_freq_commit(self, lo: float, hi: float) -> None:
        already = self._chain.detector.freq_band == (lo, hi)
        self._submit_detector({"freq_band": (lo, hi)}, "Set Frequency Band")
        if already:
            self._derive(reuse_band_power=False)

    def _on_value_drag(self, lo: float, hi: float) -> None:
        self._cheap_retune(replace(self._chain.detector, value_band=(lo, hi)))

    def _on_value_band(self, lo: float, hi: float) -> None:
        self._submit_detector({"value_band": (lo, hi)}, "Set Value Band")

    def _count_frac_for(self, lo: float, hi: float) -> tuple[float, float] | None:
        update = self._update
        if update is None:
            return None
        blocks = update.band_power.shape[1]
        return (
            lo / blocks if isfinite(lo) else max(lo, 0.0),
            hi / blocks if isfinite(hi) else hi,
        )

    def _on_count_drag(self, lo: float, hi: float) -> None:
        frac = self._count_frac_for(lo, hi)
        if frac is not None:
            self._cheap_retune(replace(self._chain.detector, count_frac=frac))

    def _on_count_band(self, lo: float, hi: float) -> None:
        frac = self._count_frac_for(lo, hi)
        if frac is not None:
            self._submit_detector({"count_frac": frac}, "Set Count Threshold")

    def _on_solo(self, block: object) -> None:
        solo = block if isinstance(block, int) else None
        if solo == self._chain.detector.solo_block:
            return
        started = perf_counter()
        self._set_detector(replace(self._chain.detector, solo_block=solo))
        self._apply()
        self._metrics.publish(BAND_DRAG_BUDGET, (perf_counter() - started) * 1000.0)

    @Slot()
    def _on_d_pressed(self) -> None:
        self._d_gesture = next(self._gestures)

    @Slot()
    def _on_d_released(self) -> None:
        gesture, self._d_gesture = self._d_gesture, None
        if gesture is None:
            return
        self._submit_detector(
            {"window_frames": self._chain.detector.window_frames},
            "Set Detection Window",
            gesture=gesture,
        )

    @Slot(int)
    def _on_window_frames(self, frames: int) -> None:
        frames = max(frames, 1)
        if self._d_gesture is not None:
            self._cheap_retune(replace(self._chain.detector, window_frames=frames))
            return
        self._submit_detector({"window_frames": frames}, "Set Detection Window")

    @Slot(bool)
    def _on_centered(self, centered: bool) -> None:
        self._submit_detector({"centered": centered}, "Set Centered")

    @Slot(str)
    def _on_swap_requested(self, step_id: str) -> None:
        self._open_wizard(step_id)

    @Slot(int)
    def _on_insert_requested(self, seam: int) -> None:
        self._open_wizard(seam)

    @property
    def wizard(self) -> StepWizard | None:
        return self._wizard

    def _open_wizard(self, target: int | str) -> None:
        if self._wizard is not None:
            return
        self._wizard_snapshot = self._chain
        self._wizard_undo_index = self._document.undo_stack.index()
        wizard = StepWizard(self._chain, target, parent=self)
        self._wizard = wizard
        wizard.chain_proposed.connect(self._on_chain_proposed)
        wizard.hover_preview.connect(self._on_hover_preview)
        wizard.hover_ended.connect(self._on_hover_ended)
        wizard.accepted.connect(self._on_wizard_accepted)
        wizard.cancelled.connect(self._on_wizard_cancelled)
        for plot in (wizard.density, wizard.count):
            plot.pressed.connect(self._player.seek)
            plot.scrubbed.connect(self._player.scrub)
            plot.committed.connect(self._player.seek)
        wizard.density.band_changed.connect(self._on_value_drag)
        wizard.density.band_committed.connect(self._on_value_band)
        wizard.count.band_changed.connect(self._on_count_drag)
        wizard.count.band_committed.connect(self._on_count_band)
        wizard.d_slider.sliderPressed.connect(self._on_d_pressed)
        wizard.d_slider.sliderReleased.connect(self._on_d_released)
        wizard.d_slider.valueChanged.connect(self._on_window_frames)
        wizard.centered.toggled.connect(self._on_centered)
        wizard.setGeometry(self.rect())
        wizard.show()
        wizard.raise_()
        wizard.setFocus()
        wizard.start()

    def _on_chain_proposed(self, chain: LiveChain, step_id: str) -> None:
        self._chain = chain
        self._provisional_id = step_id
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self._knob_armed_at = perf_counter()
        self.resubmit()

    def _on_hover_preview(self, chain: LiveChain) -> None:
        window = self._document.window
        if window is None:
            return
        grab = self._grabber(chain)
        if grab is None:
            return
        want = min(max(self._playhead, window.start), window.end - 1)
        replicate = self._document.selected_replicate
        expected = self._runner.revision + 1
        self._composite_revisions.add(expected)
        if self._runner.request_frame(chain.pipeline(), want, replicate, consumer=grab):
            self._composite_outstanding = expected
            self._composite_deferred = False
        else:
            self._composite_revisions.discard(expected)

    def _on_hover_ended(self) -> None:
        if self._wizard is None:
            return
        self._on_hover_preview(self._chain)

    def _on_wizard_accepted(self) -> None:
        step_id = self._provisional_id
        snapshot = self._wizard_snapshot
        self._close_wizard()
        if step_id is not None:
            self._ensure_body(step_id)
            self.status_message.emit(f"added '{step_id}'")
        self._document.sync_structure(self._chain.pipeline())
        if snapshot is not None and len(self._document.pipeline.nodes):
            before = snapshot.detector.as_settings_changes()
            after = self._chain.detector.as_settings_changes()
            changes = {
                name: value for name, value in after.items() if before[name] != value
            }
            if changes:
                self._document.edit_detector(changes, "Tune Detection")
        self._refresh_from_document()
        self._rebuild_stack()

    def _on_wizard_cancelled(self) -> None:
        snapshot = self._wizard_snapshot
        undo_index = self._wizard_undo_index
        self._close_wizard()
        if undo_index is not None:
            self._document.undo_stack.setIndex(undo_index)
        if snapshot is not None and snapshot is not self._chain:
            self._chain = snapshot
            self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self.status_message.emit("wizard cancelled — chain restored")
        self.resubmit()

    def _close_wizard(self) -> None:
        wizard = self._wizard
        self._wizard = None
        self._wizard_snapshot = None
        self._wizard_undo_index = None
        self._provisional_id = None
        self._grab.clear()
        if wizard is not None:
            wizard.hide()
            wizard.deleteLater()

    def _ensure_body(self, step_id: str) -> None:
        step = next((s for s in self._chain.steps if s.step_id == step_id), None)
        if step is None or step.node is None or step_id in self._extra_bodies:
            return
        if step_id in (
            "rescale",
            "normalize",
            "block_signal",
            "morlet_band",
            "windowed_count",
        ):
            return
        entry = next((e for e in catalog() if e.entry_id == step_id), None)
        hidden = entry.hidden_params if entry is not None else frozenset[str]()
        host = QWidget()
        column = QVBoxLayout(host)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        def edited(name: str, value: object, sid: str = step_id) -> None:
            self._on_extra_param(sid, name, value)
        for row in param_rows(step.node, hidden, edited):
            column.addWidget(row)
        self._extra_bodies[step_id] = host

    def _on_extra_param(self, step_id: str, name: str, value: object) -> None:
        step = next((s for s in self._chain.steps if s.step_id == step_id), None)
        if step is None or step.node is None:
            return
        if step.node.node_id in self._document.pipeline:
            index = self._document.undo_stack.index()
            self._knob_armed_at = perf_counter()
            self._document.edit_params(
                {step.node.node_id: {name: value}}, f"Set {name}"
            )
            if self._document.undo_stack.index() == index:
                self._knob_armed_at = None
            return
        steps = tuple(
            replace(
                s,
                node=s.node.model_copy(
                    update={"params": {**s.node.params, name: value}}
                ),
            )
            if s.step_id == step_id and s.node is not None
            else s
            for s in self._chain.steps
        )
        self._chain = replace(self._chain, steps=steps)
        self._knob_edited()

    @Slot(str)
    def _on_remove(self, step_id: str) -> None:
        self._chain = self._chain.without(step_id)
        self._document.sync_structure(self._chain.pipeline())
        self.status_message.emit(f"removed '{step_id}'")
        self._rebuild_stack()
        self._derive(reuse_band_power=True)
        self.resubmit()

    @Slot()
    def _on_reset(self) -> None:
        self._value_band_memory.clear()
        default_steps = {s.step_id: s for s in self._defaults.steps}
        defaults_by_node: dict[str, Mapping[str, object]] = {}
        for step in self._chain.steps:
            if step.node is None or step.node.node_id not in self._document.pipeline:
                continue
            default = default_steps.get(step.step_id)
            if default is not None and default.node is not None:
                defaults_by_node[step.node.node_id] = dict(default.node.params)
        if defaults_by_node or self._document.detector is not None:
            self._document.reset_tuning(defaults_by_node)
        else:
            self._chain = self._chain.reset(self._defaults)
            self._sync_widgets_from_chain()
        self._scalogram.clear_band()
        self._density.set_band(*self._chain.detector.value_band)
        self._count.clear_band()
        self._rebuild_stack()
        self.status_message.emit(
            "reset — parameters to defaults, bands cleared, disarmed; the chain is kept"
        )
        self._knob_edited()

    @Slot()
    def _refresh_source_card(self) -> None:
        card = self._stack.source_card
        document = self._document
        home = document.source_home
        index = document.selected_index
        replicate = document.selected_replicate
        if home is None or index is None or replicate is None:
            card.setVisible(False)
            return
        card.setVisible(True)
        subject = f"{replicate.name} · {home.video.name}"
        if self._writing_row == index:
            card.set_state(
                CropState.WRITING,
                subject=subject,
                detail="cutting the crop — the preview is paused while the write reads the source",
            )
            return
        backing = document.crop_backing(index)
        card.set_state(
            backing.state, subject=subject, detail=self._boundary_detail(backing)
        )

    def _boundary_detail(self, backing: CropBacking) -> str:
        if backing.state is CropState.ABSENT:
            return f"recut from the source on every render · {MATERIALIZE_PRICE}"
        artifact = backing.artifact
        if backing.state is CropState.STALE:
            return f"{backing.reason} — the file is still in the folder."
        if artifact is None:
            return ""
        return (
            f"at rest · {self._artifact_stamp(artifact)} · "
            "the box and the clip are held while this backs the replicate"
        )

    def _artifact_stamp(self, artifact: CropArtifact) -> str:
        home = self._document.source_home
        fmt = artifact.format
        extent = f"frames [{artifact.span.start}:{artifact.span.end})"
        if home is None:
            return f"{fmt} · {extent}"
        path = artifact.resolve(home.project_dir)
        try:
            stat = path.stat()
        except OSError:
            return f"{fmt} · {extent} · {path.name} (not readable)"
        written = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"{stat.st_size / 1e6:.1f} MB · {fmt} · {extent} · written {written}"

    @Slot()
    def _on_materialize(self) -> None:
        document = self._document
        home = document.source_home
        replicate = document.selected_replicate
        frames = document.source_frames
        index = document.selected_index
        if home is None or replicate is None or frames <= 0 or index is None:
            return
        span = ClipRange(start=0, end=frames)
        if self._materializer.busy:
            self.status_message.emit("a crop is already being written")
            return
        self._runner.set_paused(True)
        self._writing_row = index
        started = self._materializer.start(
            MaterializeRequest(
                video=home.video,
                replicate=replicate,
                span=span,
                project_dir=home.project_dir,
                luma=document.decodes_luma(),
            )
        )
        if not started:
            self._writing_row = None
            self._runner.set_paused(False)
            return
        self._refresh_source_card()
        self.status_message.emit(f"writing the crop for {replicate.name}…")

    @Slot(object)
    def _on_crop_written(self, record: object) -> None:
        self._writing_row = None
        if not isinstance(record, CropArtifact):
            return
        self._document.register_crop(record)
        self._resume_after_write()
        self.status_message.emit(
            "crop written and at rest — this replicate now reads from it"
        )

    @Slot(str)
    def _on_crop_failed(self, message: str) -> None:
        self._writing_row = None
        self._resume_after_write()
        self.status_message.emit(f"the crop was not written: {message}")

    @Slot()
    def _on_crop_cancelled(self) -> None:
        self._writing_row = None
        self._resume_after_write()
        self.status_message.emit("crop write cancelled — nothing was left on disk")

    def _resume_after_write(self) -> None:
        self._runner.set_paused(False)
        self._refresh_source_card()
        self.resubmit()

    @Slot()
    def _on_discard_crop(self) -> None:
        document = self._document
        home = document.source_home
        index = document.selected_index
        if home is None or index is None:
            return
        artifact = document.crop_backing(index).artifact
        if artifact is None:
            return
        path = artifact.resolve(home.project_dir)
        answer = QMessageBox.question(
            self,
            "Discard crop",
            f"Discard {path.name}?\n\n"
            "The file is deleted and this replicate is read from the source again.",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Discard:
            return
        self._runner.set_paused(True)
        self._runner.release_files()
        document.discard_crop(artifact)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            self.status_message.emit(
                f"the record is dropped, but {path.name} is still on disk: {error}"
            )
        self._runner.set_paused(False)
        self._refresh_source_card()
        self.resubmit()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        if self._wizard is not None:
            self._wizard.setGeometry(self.rect())

    @Slot()
    def _on_source_changed(self) -> None:
        if self._wizard is not None:
            self._close_wizard()
        self._value_band_memory.clear()
        fps = self._fps()
        self._chain = parity_chain(fps)
        self._defaults = parity_chain(fps)
        self._document.sync_structure(self._chain.pipeline())
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._series_start = None
        self._series2d = None
        self._update = None
        self._pooled_power = None
        self._density_surface = None
        self._heat_source = None
        self._heat_max = 0.0
        self._playhead = 0
        self._knob_armed_at = None
        self._selected_step = None
        self._frame_image = None
        self._derive_failure = None
        self._composite_grab.clear()
        self._composite_revisions.clear()
        self._series_pending = False
        self._composite_outstanding = None
        self._composite_deferred = False
        self._composite.set_frames(None, None)
        self._composite.set_notice("")
        self._composite.set_block_state(
            np.zeros(1, np.float32), np.zeros(1, bool), None
        )
        self._composite.reset_zoom()
        self._hud.set_span(0, 0)
        self._hud.begin()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self.resubmit()

    @Slot()
    def _on_selection_changed(self) -> None:
        self._refresh_from_document()
        self.resubmit()
        if self.isVisible():
            self._record_visit()

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        self._playhead = index
        self._frame_image = image
        for plot in (self._scalogram, self._density, self._count, self._hud):
            plot.set_playhead(index)
        self._apply_block_state()
        self._refresh_composite()


def _row(label: str, *widgets: QWidget) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    tag = QLabel(label)
    tag.setStyleSheet(f"color: {DIM.name()};")
    layout.addWidget(tag)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch(1)
    return row
