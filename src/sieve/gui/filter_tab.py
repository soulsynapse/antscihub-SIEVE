"""The filter tab: the live chain on the right, where the signal is on the left.

Item 6's assembly (parity plan § 2). The left column is the block-heat panel,
the green windowed-count graph, and the detection window D row; the right
column is `ChainStackView` over one `LiveChain` value; the graphs live in the
card of the step that produces them. The cross-tab seeker stays outside every
tab (`main_window.py`), exactly as it does for the replicate tab.

**One value, replaced on every edit.** The tab holds the current `LiveChain`
and replaces it — knob edits rewrite node params, removals go through
`without`, Reset through `reset`. The stack is redrawn from the value, the
`Pipeline` handed to the runner is derived from the value, and the detector
maths read the value, so there is no second place a parameter lives (the plan's
"knob state lives in the tab", held to one attribute).

**Render plumbing is item 4's, used as designed.** Every chain change submits
the runnable prefix through `PreviewRunner.request_render` with a consumer
feeding one `SeriesCollector`; the runner's latest-wins submission and the
collector's revision check are what make a burst of knob edits compute one
final series with the last value — the tab adds no timer and no debounce of
its own, which is the whole point of `gui/coalescer.py`'s discipline living
in the runner.

**Two tiers, made visible at the signal boundary.** `band_changed` from any
plot is the cheap tier: re-derive from the retained band power, repaint, and
publish the interval against the `band_drag_repaint` budget. A frequency-band
*drag* moves only the handles and the snapped-band readout — the Morlet
re-sum is not cheap at every mouse-move — and its `band_committed` runs the
full derivation. Upstream knob changes re-run extraction through the runner
and are judged against `knob_to_graphs` from the last edit to the repaint.

**No reachable step, no graph.** The stack embeds a step's widgets only while
the step grades ok, so removing the temporal step takes the scalogram and
density plots out of the column; the count plot stays (it is the left
column's) and says why it is empty, and the detections summary reads "chain
incomplete — see the stack".
"""

from __future__ import annotations

from dataclasses import replace
from math import isfinite
from time import perf_counter

import numpy as np
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.wavelet import default_freqs, morlet_power
from sieve.filters.block_signal import resolve_block
from sieve.gui.band_plot import DIM
from sieve.gui.block_heat import BlockHeatPanel
from sieve.gui.chain_model import (
    SIGNAL_LABELS,
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
from sieve.gui.chain_stack import ChainStackView
from sieve.gui.count_plot import CountPlot
from sieve.gui.density_plot import DensityPlot
from sieve.gui.document import ReplicateDocument
from sieve.gui.graph_hud import GraphHud
from sieve.gui.param_form import param_rows
from sieve.gui.player import VideoPlayer
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.scalogram_plot import ScalogramPlot
from sieve.gui.series_collector import CollectedSeries, SeriesCollector
from sieve.gui.wizard import StepWizard, frame_to_qimage, last_image_node_id
from sieve.gui.wizard_model import catalog

#: The two interaction budgets this tab produces (ARCHITECTURE.md rows).
BAND_DRAG_BUDGET = "band_drag_repaint"
KNOB_BUDGET = "knob_to_graphs"

#: The high percentile of the window's band power that reads as full heat on
#: the block panel — fixed across the window so brightness holds its meaning.
_HEAT_PERCENTILE = 99.5

_CHAIN_INCOMPLETE = "chain incomplete — see the stack"
_DISARMED = "disarmed — place the count threshold"


class FilterTab(QWidget):
    """The live preprocessing chain and its detector, for one source video."""

    #: One line about what just happened, for the window's status bar.
    status_message = Signal(str)
    #: The detector graphs were rebuilt from a freshly collected series. A
    #: test's observable for "exactly one final recompute".
    graphs_updated = Signal()

    def __init__(
        self,
        player: VideoPlayer,
        document: ReplicateDocument,
        runner: PreviewRunner,
        parent: QWidget | None = None,
        *,
        metrics: MetricBus | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        self._runner = runner
        self._metrics = METRICS if metrics is None else metrics

        self._chain = parity_chain(30.0)
        self._defaults = parity_chain(30.0)
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._series: CollectedSeries | None = None
        self._series2d: np.ndarray | None = None
        self._grid: tuple[int, int] = (1, 1)
        self._update: DetectorUpdate | None = None
        self._pooled_power: np.ndarray | None = None
        self._playhead = 0
        #: When the last upstream knob was edited, or None when nothing is
        #: being timed — the `knob_to_graphs` arm, same shape as the runner's
        #: first-tick arm.
        self._knob_armed_at: float | None = None

        # The wizard (plan item 7). One at a time; the snapshot is what
        # Cancel restores, and the provisional id is what the stack dashes.
        self._wizard: StepWizard | None = None
        self._wizard_snapshot: LiveChain | None = None
        self._provisional_id: str | None = None
        #: One-slot mailbox for the wizard's video frame: the render thread
        #: drops the grabbed array in, `_on_render_finished` converts it on
        #: the GUI thread. A list because slot replacement is atomic enough
        #: under the lock the collector already provides for the series path.
        self._grab: list[np.ndarray] = []
        #: Card bodies for committed non-parity steps, built from the params
        #: model on first commit and persistent like the hand-built rows.
        self._extra_bodies: dict[str, QWidget] = {}
        #: The § 8 settlement: value bands are remembered per signal, because
        #: a Jtt-tuned band silently reinterpreted in LK units was the mockup
        #: cycle's clearest foot-gun (`mockups/tab --shot lk`).
        self._value_band_memory: dict[str, tuple[float, float]] = {}

        self._build_widgets()
        self._build_layout()
        self._connect()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()

    # ---- construction ----------------------------------------------------

    def _build_widgets(self) -> None:
        self._heat = BlockHeatPanel()
        self._count = CountPlot()
        self._scalogram = ScalogramPlot()
        self._scalogram.setMinimumHeight(160)
        self._density = DensityPlot()
        self._density.setMinimumHeight(160)
        self._stack = ChainStackView()
        self._hud = GraphHud()

        # The D row under the count graph.
        self._d_slider = QSlider(Qt.Orientation.Horizontal)
        self._d_slider.setRange(1, 600)
        self._d_label = QLabel()
        self._centered = QCheckBox("centered")
        self._summary = QLabel()

        # The persistent card bodies. Created once and borrowed by the stack;
        # a rebuild detaches them before their host card dies.
        self._downsample = QDoubleSpinBox()
        self._downsample.setRange(0.05, 1.0)
        self._downsample.setSingleStep(0.05)
        self._downsample.setDecimals(2)
        self._normalize = QComboBox()
        self._normalize.addItems(["off", "zscore"])
        self._block = QSpinBox()
        self._block.setRange(0, 256)
        self._signal_buttons: dict[str, QPushButton] = {}
        for signal_id, label in SIGNAL_LABELS.items():
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, s=signal_id: self._on_signal_switch(s))
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

        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(self._heat, 3)
        left.addWidget(self._count, 2)
        left.addLayout(d_row)
        left.addWidget(self._hud, 1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(10)
        layout.addLayout(left, 5)
        layout.addWidget(self._stack, 6)

    def _connect(self) -> None:
        self._player.frame_changed.connect(self._on_frame_changed)
        self._document.source_changed.connect(self._on_source_changed)
        self._document.clip_changed.connect(self.resubmit)
        self._runner.opened.connect(self.resubmit)
        self._runner.render_started.connect(self._collector_start)
        self._runner.render_started.connect(self._hud_begin)
        self._runner.frame_cost.connect(self._hud.add_cost)
        self._runner.render_finished.connect(self._on_render_finished)

        self._stack.reset_clicked.connect(self._on_reset)
        self._stack.remove_requested.connect(self._on_remove)
        self._stack.swap_requested.connect(self._on_swap_requested)
        self._stack.insert_requested.connect(self._on_insert_requested)

        # Knobs: every edit rewrites the chain value and rides the runner's
        # latest-wins submission. No timers here — see the module docstring.
        self._downsample.valueChanged.connect(self._on_downsample)
        self._normalize.currentTextChanged.connect(self._on_normalize)
        self._block.valueChanged.connect(self._on_block)

        # The gesture contract: handle drags in two tiers, everything else a
        # playhead the player owns.
        for plot in (self._scalogram, self._density, self._count, self._hud):
            plot.pressed.connect(self._player.seek)
            plot.scrubbed.connect(self._player.scrub)
            plot.committed.connect(self._player.seek)
        self._scalogram.band_changed.connect(self._on_freq_drag)
        self._scalogram.band_committed.connect(self._on_freq_commit)
        self._density.band_changed.connect(self._on_value_band)
        self._density.band_committed.connect(self._on_value_band)
        self._count.band_changed.connect(self._on_count_band)
        self._count.band_committed.connect(self._on_count_band)
        self._heat.solo_toggled.connect(self._on_solo)
        self._d_slider.valueChanged.connect(self._on_window_frames)
        self._centered.toggled.connect(self._on_centered)

    # ---- reading (for the window and for tests) --------------------------

    @property
    def chain(self) -> LiveChain:
        """The current chain value. Every edit replaces it."""
        return self._chain

    @property
    def stack(self) -> ChainStackView:
        """The stack view, for the window and for tests driving cards."""
        return self._stack

    @property
    def count_plot(self) -> CountPlot:
        """The left column's windowed-count graph."""
        return self._count

    @property
    def scalogram(self) -> ScalogramPlot:
        """The temporal step's embedded scalogram."""
        return self._scalogram

    @property
    def density(self) -> DensityPlot:
        """The temporal step's embedded band-power density graph."""
        return self._density

    @property
    def downsample_knob(self) -> QDoubleSpinBox:
        """The rescale card's spinbox — the knob tests drive bursts through."""
        return self._downsample

    @property
    def summary_text(self) -> str:
        """The detections summary under the count graph."""
        return self._summary.text()

    @property
    def hud(self) -> GraphHud:
        """The per-frame cost plot. The window connects the bus's samples to it."""
        return self._hud

    # ---- the chain value -------------------------------------------------

    def _fps(self) -> float:
        return self._document.source_fps or 30.0

    def _block_step(self):
        steps = self._chain.steps
        return next(
            (s for s in steps if s.node is not None and s.node.filter_id == "block_signal"),
            None,
        )

    def _block_node_id(self) -> str | None:
        step = self._block_step()
        return None if step is None or step.node is None else step.node.node_id

    def _set_node_params(self, filter_id: str, **params: object) -> None:
        """Rewrite one node's params in place, keeping its identity.

        The node id survives on purpose: it is what the collector watches and
        what gives cache reuse across knob wiggles, and a knob edit is not a
        new node.
        """
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

    # ---- rendering -------------------------------------------------------

    @Slot()
    def resubmit(self) -> None:
        """Render the chain's runnable prefix over the working window.

        Refused by the runner while nothing is open, exactly like the
        replicate preview — one place decides what is worth rendering.
        """
        window = self._document.window
        if window is None:
            return
        node_id = self._block_node_id()
        if node_id is not None and node_id != self._collector.node_id:
            self._collector = SeriesCollector(node_id)
        collector = self._collector
        replicates = self._document.all()
        replicate = replicates[0] if replicates else None
        # The submission the consumer belongs to is the next revision; read
        # on the GUI thread immediately before the submit, so nothing can
        # intervene. The consumer never runs for a superseded revision (the
        # worker checks before calling it), so a refused submit simply leaves
        # the closure dead.
        expected = self._runner.revision + 1
        grabber = self._grabber(self._chain) if self._wizard is not None else None

        def feed(result: object) -> None:
            collector.add(expected, result)  # type: ignore[arg-type]
            if grabber is not None:
                grabber(result)

        self._runner.request_render(self._chain.pipeline(), window, replicate, consumer=feed)

    def _grabber(self, chain: LiveChain):
        """A consumer that catches the wizard's video frame as it flies past.

        Runs on the render thread inside the window render the tab was
        submitting anyway — the wizard's video is one of the frames the
        graphs already paid for, not a second render.
        """
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
        self._collector.start(revision)

    @Slot(int)
    def _hud_begin(self, revision: int) -> None:
        """A new render replaces the HUD's series — the runner said so.

        The span is re-read from the document rather than from the request:
        the HUD's x axis is the working window, and a single-frame render (a
        wizard hover) is one dot at its place in that window, not a window of
        its own.
        """
        del revision
        window = self._document.window
        if window is not None:
            self._hud.set_span(window.start, window.frame_count)
        self._hud.begin()

    @Slot(object)
    def _on_render_finished(self, render: object) -> None:
        del render
        if self._wizard is not None and self._grab:
            self._wizard.show_frame(frame_to_qimage(self._grab.pop()))
        series = self._collector.take(self._runner.revision)
        if series is None:
            # A render whose prefix stopped above the extraction step — the
            # graphs have nothing new; `_apply` already says why.
            return
        self._series = series
        data = series.data
        self._grid = (int(data.shape[1]), int(data.shape[2]))
        self._series2d = data.reshape(data.shape[0], -1)
        freqs = default_freqs(self._fps())
        self._pooled_power = morlet_power(self._series2d.mean(axis=1), self._fps(), freqs)
        self._derive(reuse_band_power=False)
        if self._knob_armed_at is not None:
            self._metrics.publish(KNOB_BUDGET, (perf_counter() - self._knob_armed_at) * 1000.0)
            self._knob_armed_at = None
        self.graphs_updated.emit()

    # ---- derivation ------------------------------------------------------

    def _reachable(self) -> tuple[bool, bool]:
        """(temporal step ok, detection step ok) under the current grades."""
        temporal = False
        for step, grade in zip(self._chain.steps, self._chain.grades(), strict=True):
            if step.stage is Stage.TEMPORAL_FILTER and grade.status is Status.OK:
                temporal = True
        return temporal, self._chain.detection_reachable()

    def _derive(self, *, reuse_band_power: bool) -> None:
        """Recompute the detector over the collected series and repaint.

        `reuse_band_power` is the cheap tier: value band, count threshold, D,
        centered, and solo changes re-derive from the retained band power.
        Anything that moves the frequency band or the series discards it.
        """
        temporal_ok, _ = self._reachable()
        if self._series is None or self._series2d is None or not temporal_ok:
            self._update = None
            self._apply()
            return
        band_power = (
            self._update.band_power if reuse_band_power and self._update is not None else None
        )
        self._update = recompute(
            self._series2d,
            self._fps(),
            self._chain.detector,
            start_index=self._series.start_index,
            band_power=band_power,
        )
        self._apply()

    def _apply(self) -> None:
        """Repaint everything from the chain value and the last update."""
        detector = self._chain.detector
        fps = self._fps()
        temporal_ok, detection_ok = self._reachable()
        update = self._update

        seconds = detector.window_frames / fps if fps > 0 else 0.0
        self._d_label.setText(f"D {detector.window_frames} fr ({seconds:.2f} s)")

        if update is None or self._series is None:
            self._count.set_series(np.zeros(0, np.float32), region_blocks=1, armed=False)
            self._count.set_gate(None)
            if not temporal_ok:
                self._count.set_notice("no reachable temporal filter step")
            elif not detection_ok:
                self._count.set_notice("no reachable detection step")
            else:
                self._count.set_notice("no series yet — waiting for a render")
            self._heat.set_caption("")
            if not temporal_ok or not detection_ok:
                self._summary.setText(_CHAIN_INCOMPLETE)
            else:
                self._summary.setText("")
            self._push_wizard_state(None, 0, 0, temporal_ok, detection_ok)
            return

        start = self._series.start_index
        frames = self._series2d.shape[0] if self._series2d is not None else 0
        blocks = update.band_power.shape[1]
        signal = self._signal_label()

        freqs = default_freqs(fps)
        if self._pooled_power is not None:
            self._scalogram.set_power(self._pooled_power, freqs, fps)
        self._scalogram.set_span(start, frames)
        self._scalogram.set_playhead(self._playhead)
        self._scalogram.set_band(
            max(detector.freq_band[0], float(freqs[0])),
            min(detector.freq_band[1], float(freqs[-1])),
        )
        self._scalogram.set_readout(f"{snapped_band_label(detector.freq_band, fps)} · {signal}")

        solo = detector.solo_block
        solo_trace = update.band_power[:, solo] if solo is not None and solo < blocks else None
        self._density.set_series(update.band_power, solo_trace)
        self._density.set_span(start, frames)
        self._density.set_playhead(self._playhead)
        self._density.set_band(*detector.value_band)

        self._count.set_span(start, frames)
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
        self._heat.set_grid(ny, nx)
        self._heat.set_scale_max(float(np.percentile(update.band_power, _HEAT_PERCENTILE)))
        self._heat.set_caption(f"{signal} · {ny}x{nx} blocks")
        self._apply_heat_state()

        if not temporal_ok or not detection_ok:
            self._summary.setText(_CHAIN_INCOMPLETE)
        elif update.intervals is None:
            self._summary.setText(_DISARMED)
        else:
            gated = float(update.gate.sum()) / fps if update.gate is not None else 0.0
            self._summary.setText(f"{len(update.intervals)} detections · {gated:.1f} s")

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
        """The wizard's own plots repaint from the same derivation the tab's did.

        Shared state, separate views (plan learning 6): a band dragged on
        either copy lands here through the same handlers, and both copies
        repaint from the one `DetectorUpdate`.
        """
        if self._wizard is None:
            return
        self._wizard.apply_state(
            update=update,
            start=start,
            frames=frames,
            detector=self._chain.detector,
            fps=self._fps(),
            temporal_ok=temporal_ok,
            detection_ok=detection_ok,
            playhead=self._playhead,
        )

    def _apply_heat_state(self) -> None:
        """The heat panel's per-playhead row: fill, in-band mask, solo."""
        update = self._update
        if update is None or self._series is None:
            return
        row = self._playhead - self._series.start_index
        row = min(max(row, 0), update.band_power.shape[0] - 1)
        values = update.band_power[row]
        lo, hi = self._chain.detector.value_band
        in_band = (values >= lo) & (values <= hi)
        self._heat.set_state(values, in_band, self._chain.detector.solo_block)

    def _signal_label(self) -> str:
        step = self._block_step()
        if step is None or step.node is None:
            return ""
        signal = str(step.node.params.get("signal", ""))
        return SIGNAL_LABELS.get(signal, signal)

    # ---- the stack -------------------------------------------------------

    def _captions(self) -> dict[str, str]:
        fps = self._fps()
        return {
            step.step_id: caption_for(step, self._chain.detector, fps) for step in self._chain.steps
        }

    def _rebuild_stack(self) -> None:
        captions = self._captions()
        bodies: dict[str, tuple[QWidget, ...]] = {
            "rescale": (self._rescale_row,),
            "normalize": (self._normalize_row,),
            "block_signal": (self._block_row, self._signal_row),
            "morlet_band": (self._scalogram, self._density),
            "windowed_count": (self._detect_note,),
        }
        bodies.update({step_id: (body,) for step_id, body in self._extra_bodies.items()})
        self._stack.rebuild(
            self._chain.steps,
            self._chain.grades(),
            [captions[step.step_id] for step in self._chain.steps],
            bodies,
            provisional=self._provisional_id,
        )

    def _sync_widgets_from_chain(self) -> None:
        """Echo the chain value into the knobs without re-triggering edits."""
        knobs = (self._downsample, self._normalize, self._block, self._d_slider, self._centered)
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

    # ---- knob edits (upstream: re-run extraction) ------------------------

    def _knob_edited(self) -> None:
        """Common tail of every upstream edit: captions, arm, resubmit."""
        self._stack.update_captions(self._captions())
        self._knob_armed_at = perf_counter()
        self.resubmit()

    @Slot(float)
    def _on_downsample(self, scale: float) -> None:
        # Scale enters twice on purpose: rescale performs it, block_signal's
        # auto-block resolution and fps/scale bookkeeping depend on it.
        self._set_node_params("rescale", scale=scale)
        self._set_node_params("block_signal", scale=scale)
        self._block.setSpecialValueText(f"auto ({resolve_block(0, scale)})")
        self._knob_edited()

    @Slot(str)
    def _on_normalize(self, mode: str) -> None:
        self._set_node_params("normalize", mode=mode)
        self._knob_edited()

    @Slot(int)
    def _on_block(self, block: int) -> None:
        self._set_node_params("block_signal", block=block)
        self._knob_edited()

    def _on_signal_switch(self, signal_id: str) -> None:
        """The quick-switch: swap the extraction in place, value band per signal.

        The § 8 settlement: the frequency band is in Hz and carries over, but
        the value band is in the signal's own units — a Jtt-tuned threshold
        read in LK px/s is the mockup cycle's clearest silent misread — so
        each signal remembers its own and starts wide open the first time.
        """
        step = self._block_step()
        old_signal = (
            str(step.node.params.get("signal", "")) if step is not None and step.node else ""
        )
        for other_id, button in self._signal_buttons.items():
            button.setChecked(other_id == signal_id)
        detector = self._chain.detector
        if old_signal and old_signal != signal_id:
            self._value_band_memory[old_signal] = detector.value_band
            restored = self._value_band_memory.get(signal_id, DetectorState().value_band)
            self._set_detector(replace(detector, value_band=restored))
        self._set_node_params("block_signal", signal=signal_id)
        self.status_message.emit(
            f"signal → {SIGNAL_LABELS[signal_id]} (value band remembered per signal)"
        )
        self._knob_edited()

    # ---- detector edits (tab-side: pure recompute) -----------------------

    def _cheap_retune(self, detector: DetectorState) -> None:
        """The cheap tier: replace the detector, re-derive, judge the budget."""
        self._set_detector(detector)
        started = perf_counter()
        self._derive(reuse_band_power=True)
        self._metrics.publish(BAND_DRAG_BUDGET, (perf_counter() - started) * 1000.0)

    def _on_freq_drag(self, lo: float, hi: float) -> None:
        """A frequency drag moves handles and the readout; the transform waits.

        The Morlet re-sum is the one band edit that is not cheap per
        mouse-move, so the drag tier shows the snapped truth and the commit
        tier recomputes (plan § 2's two-tier rule applied to its one
        expensive band).
        """
        detector = replace(self._chain.detector, freq_band=(lo, hi))
        self._set_detector(detector)
        fps = self._fps()
        self._scalogram.set_readout(
            f"{snapped_band_label(detector.freq_band, fps)} · {self._signal_label()}"
        )
        self._stack.update_captions(self._captions())

    def _on_freq_commit(self, lo: float, hi: float) -> None:
        self._set_detector(replace(self._chain.detector, freq_band=(lo, hi)))
        self._derive(reuse_band_power=False)

    def _on_value_band(self, lo: float, hi: float) -> None:
        self._cheap_retune(replace(self._chain.detector, value_band=(lo, hi)))

    def _on_count_band(self, lo: float, hi: float) -> None:
        """Counts from the plot, a fraction into the state — the one crossing.

        The first drag on the parked handles is what arms the detector; there
        is no separate control (plot contracts, § 2).
        """
        update = self._update
        if update is None:
            return
        blocks = update.band_power.shape[1]
        frac = (
            lo / blocks if isfinite(lo) else max(lo, 0.0),
            hi / blocks if isfinite(hi) else hi,
        )
        self._cheap_retune(replace(self._chain.detector, count_frac=frac))

    def _on_solo(self, block: object) -> None:
        solo = block if isinstance(block, int) else None
        self._cheap_retune(replace(self._chain.detector, solo_block=solo))

    @Slot(int)
    def _on_window_frames(self, frames: int) -> None:
        self._cheap_retune(replace(self._chain.detector, window_frames=max(frames, 1)))

    @Slot(bool)
    def _on_centered(self, centered: bool) -> None:
        self._cheap_retune(replace(self._chain.detector, centered=centered))

    # ---- structure -------------------------------------------------------

    @Slot(str)
    def _on_swap_requested(self, step_id: str) -> None:
        self._open_wizard(step_id)

    @Slot(int)
    def _on_insert_requested(self, seam: int) -> None:
        self._open_wizard(seam)

    # ---- the wizard --------------------------------------------------------

    @property
    def wizard(self) -> StepWizard | None:
        """The open wizard, None otherwise. For the window and for tests."""
        return self._wizard

    def _open_wizard(self, target: int | str) -> None:
        """Open the inset helper over this tab for `target` (seam or step id).

        The snapshot taken here is the whole Cancel mechanism: `LiveChain` is
        frozen all the way down, so restoring it *is* restoring the chain,
        the detector, and everything the plots render from them.
        """
        if self._wizard is not None:
            return
        self._wizard_snapshot = self._chain
        wizard = StepWizard(self._chain, target, parent=self)
        self._wizard = wizard

        wizard.chain_proposed.connect(self._on_chain_proposed)
        wizard.hover_preview.connect(self._on_hover_preview)
        wizard.hover_ended.connect(self._on_hover_ended)
        wizard.accepted.connect(self._on_wizard_accepted)
        wizard.cancelled.connect(self._on_wizard_cancelled)

        # The wizard's own plot instances speak the same signals to the same
        # handlers as the tab's — that is what "bound to shared state" means.
        for plot in (wizard.density, wizard.count):
            plot.pressed.connect(self._player.seek)
            plot.scrubbed.connect(self._player.scrub)
            plot.committed.connect(self._player.seek)
        wizard.density.band_changed.connect(self._on_value_band)
        wizard.density.band_committed.connect(self._on_value_band)
        wizard.count.band_changed.connect(self._on_count_band)
        wizard.count.band_committed.connect(self._on_count_band)
        wizard.d_slider.valueChanged.connect(self._on_window_frames)
        wizard.centered.toggled.connect(self._on_centered)

        wizard.setGeometry(self.rect())
        wizard.show()
        wizard.raise_()
        wizard.setFocus()
        wizard.start()

    def _on_chain_proposed(self, chain: LiveChain, step_id: str) -> None:
        """The expensive tier: adopt the provisional chain and render it.

        The provisional step is really in the chain — dashed card, real
        render, real graphs — which is what makes the preview honest and the
        Add button a formality rather than a leap.
        """
        self._chain = chain
        self._provisional_id = step_id
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self._knob_armed_at = perf_counter()
        self.resubmit()

    def _on_hover_preview(self, chain: LiveChain) -> None:
        """The cheap tier: one frame of a hypothetical, video pane only."""
        window = self._document.window
        if window is None:
            return
        grab = self._grabber(chain)
        if grab is None:
            return
        want = min(max(self._playhead, window.start), window.end - 1)
        replicates = self._document.all()
        replicate = replicates[0] if replicates else None
        self._runner.request_frame(chain.pipeline(), want, replicate, consumer=grab)

    def _on_hover_ended(self) -> None:
        """The pointer left the candidates: the video returns to the selection."""
        if self._wizard is None:
            return
        self._on_hover_preview(self._chain)

    def _on_wizard_accepted(self) -> None:
        """Add: the provisional step solidifies; the chain is already rendered."""
        step_id = self._provisional_id
        self._close_wizard()
        if step_id is not None:
            self._ensure_body(step_id)
            self.status_message.emit(f"added '{step_id}'")
        self._rebuild_stack()

    def _on_wizard_cancelled(self) -> None:
        """Cancel/Esc: everything exactly as it was, from the snapshot value."""
        snapshot = self._wizard_snapshot
        self._close_wizard()
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
        self._provisional_id = None
        self._grab.clear()
        if wizard is not None:
            wizard.hide()
            wizard.deleteLater()

    def _ensure_body(self, step_id: str) -> None:
        """A committed non-parity step gets a card body built from its model.

        The parity five have hand-built bodies; anything else the wizard can
        insert gets `param_form` rows so its parameters live in its card like
        every other step's (plan § 2). Persistent like the hand-built rows —
        created once, borrowed by every rebuild after.
        """
        step = next((s for s in self._chain.steps if s.step_id == step_id), None)
        if step is None or step.node is None or step_id in self._extra_bodies:
            return
        if step_id in ("rescale", "normalize", "block_signal", "morlet_band", "windowed_count"):
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
        """A committed extra step's card edit: same tail as every upstream knob."""
        steps = tuple(
            replace(s, node=s.node.model_copy(update={"params": {**s.node.params, name: value}}))
            if s.step_id == step_id and s.node is not None
            else s
            for s in self._chain.steps
        )
        self._chain = replace(self._chain, steps=steps)
        self._knob_edited()

    @Slot(str)
    def _on_remove(self, step_id: str) -> None:
        self._chain = self._chain.without(step_id)
        self.status_message.emit(f"removed '{step_id}'")
        self._rebuild_stack()
        self._derive(reuse_band_power=True)
        self.resubmit()

    @Slot()
    def _on_reset(self) -> None:
        """Parameters-not-structure: knobs and detector back, the chain stays."""
        self._chain = self._chain.reset(self._defaults)
        self._value_band_memory.clear()
        self._sync_widgets_from_chain()
        self._scalogram.clear_band()
        self._density.set_band(*self._chain.detector.value_band)
        self._count.clear_band()
        self._rebuild_stack()
        self.status_message.emit(
            "reset — parameters to defaults, bands cleared, disarmed; the chain is kept"
        )
        self._knob_edited()

    # ---- source lifecycle ------------------------------------------------

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        if self._wizard is not None:
            self._wizard.setGeometry(self.rect())

    @Slot()
    def _on_source_changed(self) -> None:
        """A new source: fresh chain at its frame rate, everything cleared."""
        if self._wizard is not None:
            self._close_wizard()
        self._value_band_memory.clear()
        fps = self._fps()
        self._chain = parity_chain(fps)
        self._defaults = parity_chain(fps)
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._series = None
        self._series2d = None
        self._update = None
        self._pooled_power = None
        self._playhead = 0
        self._knob_armed_at = None
        self._heat.set_frame(None)
        self._hud.set_span(0, 0)
        self._hud.begin()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self.resubmit()

    @Slot(int, QImage)
    def _on_frame_changed(self, index: int, image: QImage) -> None:
        self._playhead = index
        self._heat.set_frame(image)
        for plot in (self._scalogram, self._density, self._count, self._hud):
            plot.set_playhead(index)
        self._apply_heat_state()


def _row(label: str, *widgets: QWidget) -> QWidget:
    """One caption-labelled parameter row, persistent across stack rebuilds."""
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
