"""The filter tab: the live chain on the right, where the signal is on the left.

Item 6's assembly (parity plan § 2). The left column is the step composite —
which also carries the block grid overlay, since the composite absorbed the
block-heat panel — the green windowed-count graph, and the detection
window D row; the right column is `ChainStackView` over one `LiveChain`
value; the graphs live in the card of the step that produces them. The
cross-tab seeker stays outside every tab (`main_window.py`), exactly as it
does for the replicate tab.

**The composite follows the stack's selection.** Clicking a card selects the
step, and the composite pane shows that step's output over its input at one
opacity — the deepest node-backed ok step at or before the selection, since a
tab-side step has no rendered frame of its own. Its pair rides window renders
for free and is otherwise refreshed by a single-frame request at the
playhead, suppressed while a window render the graphs need is outstanding so
the refresh stream can never displace it from the runner's pending slot.

**One value, replaced on every edit — and the document is where tuning lives.**
The tab holds the current `LiveChain` and replaces it, but since replicates
remember their settings the chain is the *resolved view* of what the selected
arena runs with, not the store: a knob edit goes down to the document as a
two-write command (`edit_params`/`edit_detector` — baseline moved, diff pinned
on the selected replicate) and comes back through `tuning_changed`/
`detector_changed`, where `_refresh_from_document` re-resolves the chain. The
stack is redrawn from the value, the `Pipeline` handed to the runner is derived
from the value, and the detector maths read the value — one attribute still,
one owner underneath it. Structure stays tab-owned and reaches the document
through `sync_structure`; drags and the soloed block stay tab-local (the drag
tier repaints, the release commits; soloing is looking, not tuning).

**Render plumbing is item 4's, used as designed.** Every chain change submits
the runnable prefix through `PreviewRunner.request_render` with a consumer
feeding one `SeriesCollector`; the runner's latest-wins submission and the
collector's revision check are what make a burst of knob edits compute one
final series with the last value — the tab adds no timer and no debounce of
its own, which is the whole point of `gui/transport/coalescer.py`'s discipline living
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

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from itertools import count
from math import isfinite
from time import perf_counter
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRect, Qt, Signal, Slot
from PySide6.QtGui import QHideEvent, QImage, QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.ops.wavelet import default_freqs
from sieve.core.pipeline_model import ClipRange, Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import WallTime
from sieve.filters.block_signal import BlockSignalParams, resolve_block
from sieve.filters.block_signal import Signal as BlockSignal
from sieve.filters.detect import gate_to
from sieve.gui.band_plot import DIM
from sieve.gui.block_spin import BlockSpinBox
from sieve.gui.chain_model import (
    BLOCK_SIGNAL_ELEMENT_NAMES,
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
from sieve.gui.chain_stack import ChainStackView
from sieve.gui.commit_combo import CommitCombo
from sieve.gui.composite_view import StepCompositeView
from sieve.gui.concurrency import resolve_worker_split
from sieve.gui.count_plot import CountPlot
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
from sieve.gui.materialize_worker import MaterializeRunner
from sieve.gui.param_form import param_rows
from sieve.gui.preferences import Preferences
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.rescale_cost import (
    RescaleCostHistory,
    RescaleCostSample,
    format_rescale_cost,
)
from sieve.gui.scalogram_plot import ScalogramPlot
from sieve.gui.source_boundary import SourceBoundary
from sieve.gui.transport.player import VideoPlayer
from sieve.gui.wizard import StepWizard, frame_to_qimage
from sieve.gui.wizard_lifecycle import WizardAccepted, WizardCancelled, WizardLifecycle
from sieve.gui.wizard_model import catalog, chain_from_pipeline
from sieve.mutual.pool_meter import PoolMeter
from sieve.pipeline.preview import PreviewRender
from sieve.pipeline.series_collector import SeriesCollector

#: The two interaction budgets this tab produces (ARCHITECTURE.md rows).
BAND_DRAG_BUDGET = "band_drag_repaint"
KNOB_BUDGET = "knob_to_graphs"
#: The other end of the same arm: when the graphs *started* filling, which
#: since the detector derives partial passes is the latency a user actually
#: waits through before there is something to read.
FIRST_PARTIAL_BUDGET = "knob_to_first_partial"
#: The rebuild of the density surface, inside both of the above. The only
#: budget a *control* is derived from — `gui/block_spin.py` refuses block sizes
#: whose implied block count exceeds the B this ceiling is pinned at.
DENSITY_BUDGET = "density_rebuild"

#: The high percentile of the window's band power that reads as full heat on
#: the block grid — fixed across the window so a cell's colour holds its
#: meaning at every playhead position.
_HEAT_PERCENTILE = 99.5


@dataclass(frozen=True, slots=True)
class _RescaleCostRun:
    """A window render whose wall clock should become one cost sample."""

    scale: float
    frames: int
    context: str
    started_at: float | None = None


def _block_signal_label(signal_id: str) -> str:
    return BlockSignalParams.spec().param_value_labels.get("signal", {}).get(signal_id, signal_id)


_CHAIN_INCOMPLETE = "chain incomplete — see the stack"
_DISARMED = "disarmed — place the count threshold"

#: The playback-speed cycle, in click order. Wall-clock playback throughout —
#: a higher rate scales the clock and drops more frames, it does not decode
#: faster — so 5x is a skim of the window, not a demand the decoder can miss.
PLAYBACK_RATES = (1.0, 2.0, 5.0)


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
        preferences: Preferences | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._document = document
        self._runner = runner
        self._metrics = METRICS if metrics is None else metrics
        # The gray toggle persists its manual half here. The window passes its
        # store; a tab built bare (tests, mostly) gets a default one, exactly
        # as `MainWindow` itself does when none is injected.
        self._preferences = preferences if preferences is not None else Preferences(parent=self)

        self._chain = parity_chain(30.0)
        self._defaults = parity_chain(30.0)
        self._collector = SeriesCollector(self._block_node_id() or "")
        #: Source index of `_series2d[0]`. Only the origin is kept — the
        #: arrays themselves arrive with each derivation, paired with the
        #: update derived from them.
        self._series_start: int | None = None
        self._series2d: np.ndarray | None = None
        self._grid: tuple[int, int] = (1, 1)
        self._update: DetectorUpdate | None = None
        self._pooled_power: np.ndarray | None = None
        #: The density picture the worker binned for `_update.band_power`, held
        #: so every repaint hands the plot the same one. None only before the
        #: first derivation — never as a way of asking the widget to bin.
        self._density_surface: DensitySurface | None = None
        #: Why the newest derivation did not land, or None. Held in state
        #: rather than written straight to the plot because `_apply` rebuilds
        #: every notice from the chain on each repaint: a notice set from the
        #: failure slot alone would survive exactly until the next mouse-move.
        self._derive_failure: str | None = None
        self._playhead = 0
        #: Derives the detector off the GUI thread so the graphs can fill while
        #: the render is still producing frames. Owns a thread; `shutdown` is
        #: required, and the window calls it from `closeEvent`.
        self._detector = DetectorRunner(self)
        self._detector.ready.connect(self._on_detector_ready)
        self._detector.failed.connect(self._on_detector_failed)
        #: The x axis the plots are drawn against while a render fills it: the
        #: whole working window, set once when the render is submitted. An axis
        #: that grew with the data would slide every curve leftward on each
        #: partial pass and make a filling graph read as a moving one.
        self._span: tuple[int, int] = (0, 0)
        #: Frames of the span the collected series covers, and how many of
        #: those are final. Both are the whole span once a render finishes.
        self._filled = 0
        self._settled = 0
        #: Whether the series backing `_update` came from a finished render.
        #: The summary says "filling" until it does, and the cheap tier reads
        #: it to know whether the frontier it recomputes is still moving.
        self._series_final = False
        self._rescale_costs = RescaleCostHistory()
        self._rescale_cost_runs: dict[int, _RescaleCostRun] = {}
        #: When the last upstream knob was edited, or None when nothing is
        #: being timed — the `knob_to_graphs` arm, same shape as the runner's
        #: first-tick arm.
        self._knob_armed_at: float | None = None
        #: Whether this arm already published `knob_to_first_partial`. One per
        #: arm: the budget names the *first* readable graph, and republishing
        #: it on every later pass would turn a latency into a throughput.
        self._partial_published = False
        #: The composite's heat ceiling, and the exact `band_power` it was taken
        #: over. Cached because it is a percentile across the largest array the
        #: tab holds — ~29 ms at (600, 8040), against ~0.01 ms for the prefix-sum
        #: that is all a D step actually changes — and the cheap tier's whole
        #: premise is that `band_power` is the thing it did *not* recompute.
        #: Identity, not equality: two arrays that compare equal still cost a
        #: full pass to find that out, which is the cost being avoided.
        self._heat_source: NDArray[np.float32] | None = None
        self._heat_max = 0.0

        # The step composite's state. The selection is sticky by id and falls
        # back to the tail — "a chain stack that always has a selected step"
        # is what lets full-current-state be a selection rather than a mode.
        self._selected_step: str | None = None
        #: The player's raw frame at the playhead — the first step's input.
        self._frame_image: QImage | None = None
        #: One-slot mailbox for the composite pair, the wizard grab's twin:
        #: the render thread drops `(input array | None, output array,
        #: is block grid)` in, `_on_render_finished` converts on the GUI
        #: thread.
        self._composite_grab: list[tuple[np.ndarray | None, np.ndarray, bool]] = []
        #: Revisions submitted purely to refresh the composite. The HUD keeps
        #: its window series through these — one frame at the playhead is an
        #: update to one index, not a new render worth clearing for.
        self._composite_revisions: set[int] = set()
        #: A window render the graphs are waiting on has been submitted and
        #: has not reported back. While true, playhead-driven composite
        #: refreshes are suppressed — a stream of single-frame requests would
        #: displace the window render from the runner's pending slot and the
        #: series would never arrive.
        self._series_pending = False
        #: The single-frame render the composite is waiting on, or None. One at
        #: a time, because a second submission declares a newer revision and the
        #: runner abandons the first at its next frame boundary — and a
        #: single-frame render's only frame boundary is *before* its one
        #: delivery. Playback submits one refresh per playhead move, so without
        #: this slot a chain whose frame costs more than a playback tick abandons
        #: every render it starts: the pane never repaints at all, while the
        #: graphs the last window render filled keep looking healthy.
        self._composite_outstanding: int | None = None
        #: A playhead moved while that render was outstanding. The refresh is
        #: re-issued when it reports, so pausing lands the pane on the frame the
        #: user stopped at rather than on the one before it.
        self._composite_deferred = False

        #: The wizard lifecycle: open inset, rollback state, and preview-frame
        #: mailbox. Its signals are the boundary; the tab keeps rendering and
        #: document writes.
        self._wizard_lifecycle = WizardLifecycle()
        #: Card bodies for committed non-parity steps, built from the params
        #: model on first commit and persistent like the hand-built rows.
        self._extra_bodies: dict[str, QWidget] = {}
        #: The § 8 settlement: value bands are remembered per signal, because
        #: a Jtt-tuned band silently reinterpreted in LK units was the mockup
        #: cycle's clearest foot-gun (`mockups/tab --shot lk`).
        self._value_band_memory: dict[str, tuple[float, float]] = {}
        #: Gesture tokens for the D slider, `SetReplicateROI`'s discipline:
        #: one token per press, so a drag across detents merges to one undo
        #: entry and two separate drags stay two.
        self._gestures = count(1)
        self._d_gesture: int | None = None

        self._build_widgets()
        self._build_layout()
        #: The source boundary — the card above the stack, the write pass behind
        #: it, and the four states in between. Owned here rather than by the
        #: window because the gesture is the source card's and the card is the
        #: stack's, and because holding the preview around a write is a
        #: statement about this tab's render, which nothing else submits.
        self._boundary = SourceBoundary(document, self._stack.source_card, self)
        self._connect()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self._refresh_rescale_cost()

    # ---- construction ----------------------------------------------------

    def _build_widgets(self) -> None:
        # The tab's top-right corner: how fast the transport runs, and what
        # format the pane decodes — the two controls over how the picture
        # arrives, next to each other because they trade against the same
        # scarce decode bandwidth.
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
        self._rescale_cost_label = QLabel("cost: timing pending")
        self._rescale_cost_label.setObjectName("rescale-cost")
        self._rescale_cost_label.setStyleSheet(f"color: {DIM.name()}; font-size: 11px;")
        self._rescale_cost_label.setToolTip(
            "Measured from completed window renders in this source, window, replicate, "
            "and chain context. A numeric cost and knee need at least two scales."
        )
        self._normalize = CommitCombo()
        self._normalize.addItems(["off", "zscore"])
        self._block = BlockSpinBox()
        self._block.setRange(0, 256)
        self._signal_buttons: dict[str, QPushButton] = {}
        for signal in BlockSignal:
            signal_id = signal.value
            label = _block_signal_label(signal_id)
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, s=signal_id: self._on_signal_switch(s))
            self._signal_buttons[signal_id] = button
        self._detect_note = QLabel("graph and detection window D live under the video")
        self._detect_note.setStyleSheet(f"color: {DIM.name()};")

        self._rescale_row = _row("Downsample", self._downsample, self._rescale_cost_label)
        self._normalize_row = _row("Normalize", self._normalize)
        self._block_row = _row("Block", self._block)
        self._signal_row = _row("Signal", *self._signal_buttons.values())

    def _build_layout(self) -> None:
        d_row = QHBoxLayout()
        d_row.addWidget(self._d_label)
        d_row.addWidget(self._d_slider, 1)
        d_row.addWidget(self._centered)
        d_row.addWidget(self._summary)

        # Top-right of the *player*, not of the tab: a corner row spanning the
        # whole tab puts these over the chain stack, which they say nothing
        # about. They govern the pane that stutters, so they sit on it.
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
        # The toggle decides the format, the player obeys it, and the runner
        # feeds the automatic half — but only while this tab is on screen.
        # Gray is the tuning loop's tradeoff; on the replicate tab colour is
        # what identifies an arena, so the format follows the tab
        # (`showEvent`/`hideEvent`) rather than being pushed unconditionally.
        self._gray_toggle.luma_changed.connect(self._on_luma_changed)
        self._runner.window_render_changed.connect(self._gray_toggle.set_rendering)

        self._player.frame_changed.connect(self._on_frame_changed)
        self._document.source_changed.connect(self._on_source_changed)
        self._document.clip_changed.connect(self.resubmit)
        # A replicate change invalidates exactly as a window move does: the
        # render goes through the runner's latest-wins submission unchanged.
        self._document.selection_changed.connect(self._on_selection_changed)
        # ...and so does a geometry or pin edit on the arena being tuned, which
        # is what `replicate_changed` carries — including the one an undo makes.
        self._document.replicate_changed.connect(self._on_replicate_changed)
        # The document is where tuning lives now; every edit — from this tab,
        # from Ctrl+Z, from a future panel — comes back through these three,
        # and the tab re-resolves what the selected replicate runs with.
        self._document.tuning_changed.connect(self._on_tuning_changed)
        self._document.detector_changed.connect(self._on_detector_changed)
        self._document.pipeline_changed.connect(self._on_pipeline_changed)
        self._runner.opened.connect(self.resubmit)
        self._runner.render_started.connect(self._on_render_started)
        self._runner.render_started.connect(self._collector_start)
        self._runner.render_started.connect(self._hud_begin)
        self._runner.frame_cost.connect(self._on_frame_cost)
        self._runner.render_finished.connect(self._on_render_finished)
        self._runner.render_failed.connect(self._on_render_failed)

        # The source boundary, at its three-signal seam. Direct connections, and
        # `_on_boundary_hold` says what breaks if that ever changes.
        self._boundary.render_hold.connect(self._on_boundary_hold)
        self._boundary.render_stale.connect(self.resubmit)
        self._boundary.status_message.connect(self.status_message)

        lifecycle = self._wizard_lifecycle
        lifecycle.chain_proposed.connect(self._adopt_wizard_chain)
        lifecycle.hover_preview_requested.connect(self._request_wizard_hover_preview)
        lifecycle.hover_ended.connect(self._restore_wizard_hover_preview)
        lifecycle.accepted.connect(self._commit_wizard)
        lifecycle.cancelled.connect(self._restore_wizard_cancel)
        lifecycle.seek_requested.connect(self._player.seek)
        lifecycle.scrub_requested.connect(self._player.scrub)
        lifecycle.value_band_changed.connect(self._on_value_drag)
        lifecycle.value_band_committed.connect(self._on_value_band)
        lifecycle.count_band_changed.connect(self._on_count_drag)
        lifecycle.count_band_committed.connect(self._on_count_band)
        lifecycle.d_pressed.connect(self._on_d_pressed)
        lifecycle.d_released.connect(self._on_d_released)
        lifecycle.window_frames_changed.connect(self._on_window_frames)
        lifecycle.centered_toggled.connect(self._on_centered)

        self._stack.reset_clicked.connect(self._on_reset)
        self._stack.select_requested.connect(self._on_step_selected)
        self._stack.remove_requested.connect(self._on_remove)
        self._stack.swap_requested.connect(self._on_swap_requested)
        self._stack.insert_requested.connect(self._on_insert_requested)

        # Knobs: every edit rewrites the chain value and rides the runner's
        # latest-wins submission. No timers here — see the module docstring.
        self._downsample.valueChanged.connect(self._on_downsample)
        # The mode combo commits on selection only (`gui/commit_combo.py`), so
        # arrowing or scrolling past `zscore` is not a normalisation the
        # document records and re-renders.
        self._normalize.textActivated.connect(self._on_normalize)
        self._block.valueChanged.connect(self._on_block)

        # The gesture contract: handle drags in two tiers, everything else a
        # playhead the player owns.
        for plot in (self._scalogram, self._density, self._count, self._hud):
            plot.pressed.connect(self._player.seek)
            plot.scrubbed.connect(self._player.scrub)
            plot.committed.connect(self._player.seek)
        self._scalogram.band_changed.connect(self._on_freq_drag)
        self._scalogram.band_committed.connect(self._on_freq_commit)
        # Drag and commit are different tiers *and* different stores now: a
        # drag repaints from the tab's local value, the release is what the
        # document records — one undo entry per placed band, none per twitch.
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
        """Stop the detector thread. Call before the application exits.

        The same obligation `PreviewRunner.shutdown` and `VideoPlayer.shutdown`
        carry, for the same reason: a `QThread` still running when Qt tears the
        widget tree down is a crash rather than a leak.
        """
        self._wizard_lifecycle.close()
        self._detector.shutdown()
        self._boundary.shutdown()

    @Slot(bool)
    def _on_boundary_hold(self, held: bool) -> None:
        """Take the render's decode bandwidth and file handles, or give them back.

        Both halves under one signal because the discard needs them in this
        order and needs the release to have *happened* before its next
        statement: pausing bumps the revision so the render in flight abandons
        at its next frame boundary, and `release_files` is a blocking call that
        would otherwise wait out a whole window render. A queued connection here
        would let the unlink race the release, and the gesture would regress to
        doing nothing with no error anywhere.

        A materialize therefore also releases, which it did not before. That
        costs one reader rebuild on the resume — free on the success path, where
        a registered record re-roots resolution anyway — and it is what makes
        the hold mean one thing rather than two the caller must sequence.
        """
        self._runner.set_paused(held)
        if held:
            self._runner.release_files()

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
    def rescale_cost_text(self) -> str:
        """The measured cost readout beside the rescale knob."""
        return self._rescale_cost_label.text()

    @property
    def summary_text(self) -> str:
        """The detections summary under the count graph."""
        return self._summary.text()

    @property
    def hud(self) -> GraphHud:
        """The per-frame cost plot. The window connects the bus's samples to it."""
        return self._hud

    @property
    def detector_meter(self) -> PoolMeter:
        """The detector pool's counters, for `gui/resource_probe.py` to read."""
        return self._detector.meter

    @property
    def composite(self) -> StepCompositeView:
        """The step composite pane, for the window and for tests."""
        return self._composite

    @property
    def materializer(self) -> MaterializeRunner:
        """The write pass. Exposed for the window's shutdown order and for tests."""
        return self._boundary.materializer

    @property
    def selected_step(self) -> str | None:
        """The selected step's id — what the composite is showing."""
        return self._selected_step

    @property
    def gray_toggle(self) -> GrayToggle:
        """The decode-format control in the tab's top-right corner."""
        return self._gray_toggle

    @property
    def speed_button(self) -> QToolButton:
        """The playback-rate cycler beside it."""
        return self._speed

    # ---- the corner controls ---------------------------------------------

    @Slot()
    def _on_speed_clicked(self) -> None:
        """Rotate the transport through the named rates, and say which holds.

        The label is written from the rate actually adopted, not from the
        click count, so the button can never claim a speed the player is not
        running at.
        """
        current = self._player.playback_rate
        index = PLAYBACK_RATES.index(current) if current in PLAYBACK_RATES else 0
        rate = PLAYBACK_RATES[(index + 1) % len(PLAYBACK_RATES)]
        self._player.set_playback_rate(rate)
        self._speed.setText(f"{self._player.playback_rate:g}x")

    @Slot(bool)
    def _on_luma_changed(self, enabled: bool) -> None:
        """The toggle's answer reaches the decode thread only while shown."""
        if self.isVisible():
            self._player.set_viewport_luma(enabled)

    def showEvent(self, event: QShowEvent) -> None:
        """This tab owns the pane's format from the moment it is the page."""
        super().showEvent(event)
        self._player.set_viewport_luma(self._gray_toggle.effective_luma)
        self._record_visit()

    def _record_visit(self) -> None:
        """Note that the selected arena has been opened for tuning.

        This tab *is* the trigger of the geometry lock — "opened in the filter
        tab" is the condition, and being the page is the whole of it. Recorded
        on becoming visible and on every selection change while visible, which
        between them cover both ways an arena arrives here: the user walked
        over to it, or it arrived under them.

        Deliberately not conditioned on a render finishing. A frame that never
        arrived is still an arena the user chose and looked at, and a lock that
        engaged only on success would leave the slowest footage — the footage
        most worth not re-rendering — unprotected.
        """
        index = self._document.selected_index
        if index is not None:
            self._document.mark_visited(index)

    def hideEvent(self, event: QHideEvent) -> None:
        """Leaving the tab hands the pane back in colour, whatever made it gray.

        The toggle's state is untouched — a manual preference or a pin
        survives the excursion and reapplies on return.
        """
        super().hideEvent(event)
        self._player.set_viewport_luma(False)

    # ---- the chain value -------------------------------------------------

    def _fps(self) -> float:
        """The chain's rate, as the `float` a filter's params field holds.

        The one place the source's exact rational meets that `float`, and
        deliberately the only one: `block_signal`, `motion_history` and
        `temporal_baseline` each hash an `fps` into `canonical_json`, so
        retyping the field would re-key every entry those filters ever cached
        — for a kernel that multiplies a window by a number and wants nothing
        exact. `float(Fraction(30000, 1001))` is the same double `CAP_PROP_FPS`
        handed over before this conversion existed, so no key moves;
        `tests/integration/test_decode.py` is where that is asserted rather
        than assumed.
        """
        return float(self._document.source_fps) or 30.0

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

    # ---- the document round trip -----------------------------------------
    # Tuning lives on the document: an edit goes down as a two-write command
    # (baseline moved, diff pinned on the selected replicate), and the tab
    # hears the change back through `tuning_changed` / `detector_changed` and
    # re-resolves. One path whether the edit came from a knob, Ctrl+Z, or a
    # replicate switch — the chain value is the *view* of what the selected
    # arena runs with, never a second store of it.

    def _node_id_for(self, filter_id: str) -> str | None:
        for step in self._chain.steps:
            if step.node is not None and step.node.filter_id == filter_id:
                return step.node.node_id
        return None

    def _submit_params(self, changes_by_filter: dict[str, dict[str, object]], text: str) -> None:
        """Route a knob edit through the document, or locally while it cannot land.

        The local fallback covers a chain the document has not adopted — a
        provisional wizard step, or a session with nothing open — where the
        same edit is a plain rewrite of the tab's value, exactly as before
        the document owned tuning.
        """
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
            # A no-op edit pushed nothing and nothing will re-render, so the
            # armed budget clock must not survive to time the next render.
            self._knob_armed_at = None

    def _submit_detector(
        self, changes: dict[str, object], text: str, *, gesture: int | None = None
    ) -> None:
        """Route a committed detector edit through the document, or keep it local.

        The wizard's edits take this same path — tuning is tuning wherever
        the slider lives, and a wizard that kept its own provisional copy left
        the tab's widgets displaying stale values after Add. Cancel's restore
        is `_restore_wizard_cancel` rolling the session's entries back off the
        undo stack. Local only while there is no pipeline in the document,
        where there is no baseline for an edit to move.
        """
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
        """One replicate was rewritten: crop, pins, anything `Replicate` holds.

        Only the selected one is on screen here, so a row nobody is tuning
        costs nothing. When it *is* the selected one, the arena's geometry or
        its pinned overrides moved underneath the render, and that invalidates
        exactly as a selection change does — re-resolve, then resubmit. This is
        the path a Ctrl+Z on a crop takes, which is why the composite used to
        keep the pre-undo aspect: `SetReplicateROI`'s undo writes through
        `apply_replace` and emits nothing this tab was listening for.
        """
        if index != self._document.selected_index:
            return
        self._refresh_from_document()
        self.resubmit()

    @Slot()
    def _on_tuning_changed(self) -> None:
        """Node baselines or pins moved: re-resolve, then re-run extraction."""
        self._refresh_from_document()
        self.resubmit()

    @Slot()
    def _on_detector_changed(self) -> None:
        """The detector moved: re-resolve, re-derive at the cheapest honest tier."""
        previous = self._chain.detector
        resolved = DetectorState.from_settings(
            self._document.resolved_detector_for_selection(),
            solo_block=previous.solo_block,
        )
        if resolved == previous:
            # Equal chain does not mean synced knobs. The wizard's sliders are
            # separate widget instances sharing this tab's handlers, and its
            # edits write the chain live — so by the time Add lands the edit in
            # the document, this echo compares equal and used to return before
            # the sync below. The document then held the tuned value, the
            # captions showed it, and the tab's own slider displayed the
            # pre-wizard number indefinitely.
            self._sync_widgets_from_chain()
            return
        self._set_detector(resolved)
        self._sync_widgets_from_chain()
        self._stack.update_captions(self._captions())
        self._derive(reuse_band_power=resolved.freq_band == previous.freq_band)

    @Slot()
    def _on_pipeline_changed(self) -> None:
        """The document's graph was replaced — a load, or an edit echoed back.

        The echo case is identified by identity: a structure the tab itself
        just synced carries the tab's own node ids, and rebuilding around
        them would only discard the tab-side state it already has. A loaded
        graph carries ids this chain has never held, and the stack regrows
        around it — steps, bodies, collector, everything.
        """
        document_ids = [node.node_id for node in self._document.pipeline.nodes]
        chain_ids = [step.node.node_id for step in self._chain.steps if step.node is not None]
        if document_ids == chain_ids:
            return
        try:
            rebuilt = chain_from_pipeline(self._document.pipeline, self._fps())
        except Exception as error:
            # Refused, and said so, rather than drawn wrong — and the
            # document's graph is left alone: the tab only writes structure
            # on its own structural edits, so what was loaded stays loadable.
            # `Exception`, not `ValueError`: a narrower catch let anything
            # else a loaded graph raised abort this rebuild *silently*, before
            # the `resubmit` at the tail — a tab that then believed nothing
            # needed rendering, with no message saying why.
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
        """Re-resolve every tuned value for the selected replicate into the chain.

        Parameters through `resolved_node_params`, the detector through
        `resolved_detector_for_selection` — the core definitions, so the
        knobs, the captions, and the render can never disagree with what a
        batch run of this arena would use. The soloed block survives because
        it is looking, not tuning, and lives only here.
        """
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

    # ---- rescale cost ----------------------------------------------------

    def _queue_rescale_cost_run(
        self, revision: int, pipeline: Pipeline, window: ClipRange, replicate: Replicate | None
    ) -> None:
        """Remember the context a window render is about to measure."""
        context = self._rescale_context(pipeline, window, replicate)
        self._rescale_costs.prepare(context)
        self._rescale_cost_runs = {
            revision: _RescaleCostRun(
                scale=self._rescale_scale(pipeline),
                frames=window.frame_count,
                context=context,
            )
        }
        self._refresh_rescale_cost()

    def _rescale_context(
        self, pipeline: Pipeline, window: ClipRange, replicate: Replicate | None
    ) -> str:
        """Everything except the rescale value that makes two samples comparable."""
        home = self._document.source_home
        roi = replicate.roi if replicate is not None else None
        source_size = self._document.source_size
        payload: dict[str, Any] = {
            "source": (
                home.identity
                if home is not None
                else {
                    "size": source_size,
                    "frames": self._document.source_frames,
                    "fps": str(self._document.source_fps),
                }
            ),
            "window": [window.start, window.end],
            "replicate": None if roi is None else [roi.x, roi.y, roi.width, roi.height],
            "pipeline": [self._cost_node(node) for node in pipeline.nodes],
            "edges": [edge.model_dump(mode="json") for edge in pipeline.edges],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    def _cost_node(self, node: Node) -> dict[str, Any]:
        """Node identity plus non-scale params, so only the rescale lever varies."""
        params = {
            name: value
            for name, value in sorted(node.params.items())
            if not (name == "scale" and node.filter_id in {"rescale", "block_signal"})
        }
        return {
            "node_id": node.node_id,
            "filter_id": node.filter_id,
            "version": node.version,
            "params": params,
        }

    def _rescale_scale(self, pipeline: Pipeline) -> float:
        """The runnable prefix's rescale factor, or 1.0 when absent."""
        for node in pipeline.nodes:
            if node.filter_id == "rescale":
                try:
                    return float(node.params.get("scale", 1.0))
                except (TypeError, ValueError):
                    return 1.0
        return 1.0

    def _refresh_rescale_cost(self) -> None:
        """Show only measured multi-scale costs; provisional fits stay textual."""
        fit = self._rescale_costs.fit
        scale = self._rescale_scale(self._chain.pipeline())
        self._rescale_cost_label.setText(format_rescale_cost(fit, scale))
        if fit is None:
            self._rescale_cost_label.setToolTip(
                "No completed window render has been timed for this source, window, "
                "replicate, and chain context yet."
            )
        elif fit.provisional is not None:
            # The refusal carries its own reason so the label and the tooltip
            # cannot drift into disagreeing about why no curve is shown.
            self._rescale_cost_label.setToolTip(fit.provisional.detail)
        else:
            knee = fit.knee_scale()
            knee_text = (
                "no knee inside the legal scale range"
                if knee is None
                else f"knee at {knee:.2f}; below it, less resolution buys less time"
            )
            standing = (
                "Two scales fit the two parameters exactly, so nothing yet tests "
                "the curve; a third scale would."
                if not fit.validated
                else "A third scale left a residual the curve had to survive."
            )
            self._rescale_cost_label.setToolTip(
                f"Fitted from {fit.n_samples} completed window renders on this machine "
                f"and this footage: fixed {fit.fixed_per_frame.milliseconds:.1f} ms/frame, "
                f"scale-sensitive {fit.per_pixel_per_frame.milliseconds:.1f} ms/frame at "
                f"scale 1.0, {knee_text}. {standing}"
            )

    @Slot(int)
    def _on_render_started(self, revision: int) -> None:
        run = self._rescale_cost_runs.get(revision)
        if run is not None:
            self._rescale_cost_runs[revision] = replace(run, started_at=perf_counter())

    def _record_rescale_cost(self, render: object) -> None:
        run = self._rescale_cost_runs.pop(self._runner.revision, None)
        if run is None or run.started_at is None:
            return
        reuse = getattr(render, "reuse", None)
        if not isinstance(reuse, float):
            # A render that cannot say how much of the chain it served from the
            # store is not a timing of any particular amount of work. Dropping
            # it keeps the sample set comparable rather than silently widening
            # the reuse spread the fit is allowed to ignore.
            return
        frames = (
            render.frames if isinstance(render, PreviewRender) and render.frames > 0 else run.frames
        )
        self._rescale_costs.add(
            RescaleCostSample(
                scale=run.scale,
                frames=frames,
                wall=WallTime(perf_counter() - run.started_at),
                context=run.context,
                reuse=reuse,
            )
        )
        self._refresh_rescale_cost()

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
        replicate = self._document.selected_replicate
        # The submission the consumer belongs to is the next revision; read
        # on the GUI thread immediately before the submit, so nothing can
        # intervene. The consumer never runs for a superseded revision (the
        # worker checks before calling it), so a refused submit simply leaves
        # the closure dead.
        expected = self._runner.revision + 1
        pipeline = self._chain.pipeline()
        grabber = self._wizard_lifecycle.grabber(self._chain, window, self._playhead)
        composite = self._composite_grabber()

        def feed(result: object) -> None:
            collector.add(expected, result)  # type: ignore[arg-type]
            if grabber is not None:
                grabber(result)
            if composite is not None:
                composite(result)

        self._queue_rescale_cost_run(expected, pipeline, window, replicate)
        if self._runner.request_render(pipeline, window, replicate, consumer=feed):
            self._series_pending = True
            # This render displaces any outstanding refresh, which is abandoned
            # without reporting: holding the slot for it would suppress every
            # later refresh for the rest of the session. Nothing is deferred —
            # this render's consumer grabs the playhead pair on its way past.
            self._composite_outstanding = None
            self._composite_deferred = False
            # The axis is the window, from now until the render is replaced.
            # Set here rather than on the first partial so that an empty plot
            # already has the right x extent and the first curve to arrive
            # lands where it will stay.
            self._span = (window.start, window.frame_count)
            self._filled = 0
            self._settled = 0
            self._series_final = False
        else:
            self._rescale_cost_runs.pop(expected, None)

    @Slot(int)
    def _collector_start(self, revision: int) -> None:
        # A single-frame refresh (composite repaint, wizard hover) is not a
        # new series: restarting the collector for one would erase the window
        # render's rows, and re-stamping the detector would drop its in-flight
        # derivation on arrival — under playback, the graphs would fill and
        # then silently never finish, because the first playhead move after
        # `render_finished` assassinated the final pass. The same exemption
        # `_hud_begin` and `_on_frame_cost` already grant.
        if revision in self._composite_revisions:
            return
        self._collector.start(revision)
        # Same stamp, both sides: a partial pass still deriving for the render
        # this one replaces is finished but never painted.
        self._detector.set_revision(revision)

    @Slot(int)
    def _hud_begin(self, revision: int) -> None:
        """A new render replaces the HUD's series — the runner said so.

        The span is re-read from the document rather than from the request:
        the HUD's x axis is the working window, and a single-frame render (a
        wizard hover) is one dot at its place in that window, not a window of
        its own.

        A composite refresh does not clear at all: playback issues one frame
        request per playhead move, and a HUD that emptied on each would never
        show the window series again. `add_cost` updates that one index in
        place instead. Revisions below the one starting can never start —
        latest-wins displaced them — so they are dropped here.
        """
        self._composite_revisions = {r for r in self._composite_revisions if r >= revision}
        if revision in self._composite_revisions:
            return
        window = self._document.window
        if window is not None:
            self._hud.set_span(window.start, window.frame_count)
        self._hud.begin()

    @Slot(int, float)
    def _on_frame_cost(self, index: int, elapsed_ms: float) -> None:
        """Forward a frame's cost to the HUD, unless it is a composite refresh.

        A composite frame is served almost entirely from the store, and its
        near-zero cost overwriting the render's real cost at that index would
        turn playback into an eraser for the HUD's series.

        The frame mailboxes are drained here too, not only at
        `render_finished`: the consumers fill them the moment the playhead
        frame passes, which for a window render is usually its first frame —
        and a first composite that waited for the window's last frame would
        leave the pane blank for the whole first render of every source.
        """
        self._wizard_lifecycle.show_grabbed_frame()
        if self._composite_grab:
            self._apply_composite(*self._composite_grab.pop())
        if self._runner.revision in self._composite_revisions:
            return
        self._hud.add_cost(index, elapsed_ms)
        self._kick_partial()

    def _kick_partial(self, *, final: bool = False) -> None:
        """Derive the graphs over the prefix collected so far, if worth doing.

        The pacing loop, and deliberately not a timer: a pass is submitted only
        when the detector thread is idle, so the partial rate settles at
        `render_time / recompute_time` with no interval for anyone to tune. A
        cheap chain nearly streams, an expensive one steps, and neither can
        spend more than half its wall clock deriving. A fixed cadence would
        have to be wrong in one of those two directions.

        A pass is skipped when no new frames have arrived since the last one:
        the same prefix would produce the same graph, and a `frame_cost` for a
        node above the watched one delivers no rows at all.
        """
        if not final and (self._detector.busy or not self._series_pending):
            return
        # The unstacked snapshot: the stack is O(frames x blocks) and runs in
        # `derive` on the detector thread, so a kick costs the GUI thread a
        # pointer copy rather than a copy of the whole series so far.
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
        """A render reported back, so the composite may ask for another.

        Any report frees the slot, not only a composite refresh's: the runner
        reports for the current revision only, so a report at all means nothing
        older is still running — including the refresh a window render or a
        hover displaced, which is abandoned silently and would otherwise hold
        the slot for the rest of the session.
        """
        self._composite_outstanding = None
        if self._composite_deferred:
            self._composite_deferred = False
            self._refresh_composite()

    @Slot(object)
    def _on_render_finished(self, render: object) -> None:
        self._record_rescale_cost(render)
        self._series_pending = False
        self._wizard_lifecycle.show_grabbed_frame()
        if self._composite_grab:
            self._apply_composite(*self._composite_grab.pop())
        if self._collector.snapshot_rows(self._runner.revision) is not None:
            # The final derivation goes through the same worker as every partial
            # one rather than being computed here. Two paths producing the graphs
            # would be two places for the frontier arithmetic to disagree, and the
            # last pass is exactly a partial pass that is allowed to claim the
            # whole record — which is what `final` says. A prefix that stopped
            # above the extraction step has nothing new; `_apply` already says why.
            self._kick_partial(final=True)
        # Last, because the deferred refresh submits and so moves the runner's
        # revision — the number `_kick_partial` above stamps its series with.
        self._release_composite_slot()

    @Slot(object)
    def _on_detector_ready(self, result: DetectorResult) -> None:
        """One derivation landed. Repaint, and publish whichever budget it ends.

        The runner has already dropped anything for a superseded revision, so
        arriving here means this is the newest chain's graph. A partial and a
        final result are applied identically apart from what they may claim —
        the whole point of routing both through one path.
        """
        self._derive_failure = None
        self._series_start = result.start_index
        self._series2d = result.series2d
        self._grid = result.grid
        self._update = result.update
        self._pooled_power = result.pooled_power
        self._density_surface = result.density
        # Measured on the detector thread, published here: the budget is the
        # binning, and moving it off the GUI thread changed where it runs, not
        # what it costs. Publishing the GUI-side wrap instead would report a
        # number nothing waits on and show a met budget for work nobody timed.
        self._metrics.publish(
            DENSITY_BUDGET, result.density_ms, detail=f"B = {result.density.blocks:,}"
        )
        self._filled = result.frames
        self._settled = result.settled
        self._series_final = result.final

        if self._knob_armed_at is not None:
            elapsed = (perf_counter() - self._knob_armed_at) * 1000.0
            # The first partial ends "when could I start reading it"; the final
            # one ends "when was it complete". Two real intervals, two rows —
            # see the note on `knob_to_first_partial` in `bench/budgets.py`.
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
            # More frames have almost certainly landed while this pass ran.
            # Kicking from here rather than only from `frame_cost` is what
            # keeps the loop turning when the render outpaces the derivation:
            # otherwise the next kick would find the worker busy, be skipped,
            # and nothing would restart it.
            self._kick_partial()

    @Slot(object)
    def _on_detector_failed(self, failure: DetectorFailure) -> None:
        """A derivation raised: say so on the graph, and leave the curve alone.

        Two halves of rule 6, and they pull in opposite directions. The curve
        already drawn is not overwritten — it is what the last successful pass
        derived, and blanking it would claim the record was empty. But it is no
        longer *current*, and a plot that said nothing would read as the graph
        having caught up. So the last honest picture stays and the notice on
        top of it says the newest pass did not land.

        Cleared by the next result through `_on_detector_ready`, which is the
        only thing that can honestly clear it.
        """
        self._derive_failure = failure.message
        self._apply()

    @Slot(str)
    def _on_render_failed(self, message: str) -> None:
        """A refused render is not one the graphs are still waiting on.

        Without this, the first failed window render would leave
        `_series_pending` true forever and the composite would never refresh
        again for the whole source.
        """
        del message
        self._rescale_cost_runs.pop(self._runner.revision, None)
        self._series_pending = False
        self._release_composite_slot()

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
        if self._series_start is None or self._series2d is None or not temporal_ok:
            self._update = None
            self._apply()
            return
        band_power = (
            self._update.band_power if reuse_band_power and self._update is not None else None
        )
        # The detector's resolved share, not every core: this runs on the GUI
        # thread beside the player's decode thread and the preview's pool, so
        # inheriting the whole machine here is the fourth consumer
        # `mutual/shares.py` forbids. The cheap tier reuses `band_power` and
        # runs no transform at all, so this only bites on a frequency commit —
        # which is also the one that used to take every core. Capping it
        # lengthens the stall rather than removing it; routing this through
        # `detector_worker.py` is the real fix.
        update = recompute(
            self._series2d,
            self._fps(),
            self._chain.detector,
            start_index=self._series_start,
            band_power=band_power,
            workers=resolve_worker_split().detector,
        )
        # The frontier is recomputed, not remembered: a D drag over a partial
        # series moves it. Widening a centered window pulls it back, and a tab
        # that kept the worker's last frontier would paint a gate over frames
        # the wider window no longer settles.
        self._settled = settled_for(
            self._filled, self._fps(), self._chain.detector, final=self._series_final
        )
        self._update = gate_to(update, self._settled, self._series_start)
        self._apply()

    def _heat_scale(self, band_power: NDArray[np.float32]) -> float:
        """The composite's heat ceiling over `band_power`, recomputed only when it moves.

        `recompute` hands the previous `band_power` straight back on the cheap
        tier — that is what "no transform at all" means — so during a D or
        threshold drag this is the same array object every pass, and the
        percentile is the same number arrived at the expensive way. The ceiling
        must still follow a real change: a frequency commit or a new render
        builds a fresh array and this misses, which is exactly when the scale
        is owed a recount.
        """
        if band_power is not self._heat_source:
            self._heat_source = band_power
            self._heat_max = float(np.percentile(band_power, _HEAT_PERCENTILE))
        return self._heat_max

    def _apply(self) -> None:
        """Repaint everything from the chain value and the last update."""
        detector = self._chain.detector
        fps = self._fps()
        temporal_ok, detection_ok = self._reachable()
        update = self._update

        seconds = detector.window_frames / fps if fps > 0 else 0.0
        self._d_label.setText(f"D {detector.window_frames} fr ({seconds:.2f} s)")

        if update is None or self._series_start is None:
            self._count.set_series(
                np.zeros(0, np.float32),
                region_elements=1,
                element_names=BLOCK_SIGNAL_ELEMENT_NAMES,
                armed=False,
            )
            self._count.set_gate(None)
            if self._derive_failure is not None:
                self._count.set_notice(f"the graphs did not derive — {self._derive_failure}")
            elif not temporal_ok:
                self._count.set_notice("no reachable temporal filter step")
            elif not detection_ok:
                self._count.set_notice("no reachable detection step")
            else:
                self._count.set_notice("no series yet — waiting for a render")
            self._composite.set_grid_caption("")
            self._composite.set_block_state(np.zeros(1, np.float32), np.zeros(1, bool), None)
            if not temporal_ok or not detection_ok:
                self._summary.setText(_CHAIN_INCOMPLETE)
            else:
                self._summary.setText("")
            self._push_wizard_state(None, 0, 0, temporal_ok, detection_ok)
            return

        # The axis is the working window; the data is a prefix of it. Falling
        # back to the collected extent keeps every path that sets no span —
        # a test driving `_apply` directly, a render that predates one — on
        # the behaviour they had when the two were always equal.
        start, span = self._span if self._span[1] > 0 else (self._series_start, self._filled)
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
        self._scalogram.set_readout(f"{snapped_band_label(detector.freq_band, fps)} · {signal}")

        solo = detector.solo_block
        solo_trace = update.band_power[:, solo] if solo is not None and solo < blocks else None
        # The surface came from the detector thread with this update, so what
        # is left here is a `QImage` wrap on the first call and nothing at all
        # on a cheap-tier repaint, where the identity check hits. The producer
        # for `density_rebuild` moved with the work, to `_on_detector_ready`.
        self._density.set_series(update.band_power, solo_trace, surface=self._density_surface)
        self._density.set_span(start, span)
        self._density.set_filled(frames, self._settled)
        self._density.set_playhead(self._playhead)
        self._density.set_band(*detector.value_band)

        self._count.set_span(start, span)
        self._count.set_filled(frames, self._settled)
        self._count.set_playhead(self._playhead)
        self._count.set_series(
            update.windowed,
            region_elements=blocks,
            element_names=BLOCK_SIGNAL_ELEMENT_NAMES,
            armed=detector.armed and detection_ok,
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
        self._composite.set_grid_caption(f"{signal} · {ny}x{nx} blocks · hover solos, click pins")
        self._apply_block_state()

        if not temporal_ok or not detection_ok:
            self._summary.setText(_CHAIN_INCOMPLETE)
        elif update.intervals is None:
            self._summary.setText(_DISARMED)
        else:
            gated = float(update.gate.sum()) / fps if update.gate is not None else 0.0
            # "so far" while the frontier is still moving. The count only ever
            # grows — the gate stops at the settled frontier, so an interval
            # here is one that will still be there when the render finishes —
            # but a bare number would read as the whole answer.
            suffix = "" if self._series_final else " · filling"
            self._summary.setText(f"{len(update.intervals)} detections · {gated:.1f} s{suffix}")

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
        # The wizard's density plot is a second view of the same array, so it
        # gets the same surface rather than binning its own — otherwise opening
        # the wizard doubles the one cost this item exists to move.
        self._wizard_lifecycle.apply_state(
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
        """The grid overlay's per-playhead row: values, in-band mask, solo."""
        update = self._update
        if update is None or self._series_start is None:
            return
        row = self._playhead - self._series_start
        row = min(max(row, 0), update.band_power.shape[0] - 1)
        values = update.band_power[row]
        lo, hi = self._chain.detector.value_band
        in_band = (values >= lo) & (values <= hi)
        self._composite.set_block_state(values, in_band, self._chain.detector.solo_block)

    def _signal_label(self) -> str:
        step = self._block_step()
        if step is None or step.node is None:
            return ""
        signal = str(step.node.params.get("signal", ""))
        return _block_signal_label(signal)

    # ---- the stack -------------------------------------------------------

    def _captions(self) -> dict[str, str]:
        fps = self._fps()
        return {
            step.step_id: caption_for(step, self._chain.detector, fps) for step in self._chain.steps
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
        bodies.update({step_id: (body,) for step_id, body in self._extra_bodies.items()})
        self._stack.rebuild(
            self._chain.steps,
            self._chain.grades(),
            [captions[step.step_id] for step in self._chain.steps],
            bodies,
            provisional=self._wizard_lifecycle.provisional_step_id,
            selected=self._selected_step,
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
        # The readout depends on the scale just echoed, but changes no document value.
        self._refresh_rescale_cost()

    # ---- the step composite ----------------------------------------------

    @Slot(str)
    def _on_step_selected(self, step_id: str) -> None:
        """A card was clicked: the composite retargets to that step."""
        if step_id == self._selected_step:
            return
        self._selected_step = step_id
        self._stack.set_selected(step_id)
        self._update_composite_caption()
        self._refresh_composite()

    def _ensure_selection(self) -> None:
        """Keep the selection pointing at a step that still exists.

        Sticky by id across rebuilds; when the selected step is gone — or
        nothing was ever selected — it falls to the tail, the last ok step,
        which is what makes the default view the full current state.
        """
        ids = {step.step_id for step in self._chain.steps}
        if self._selected_step in ids:
            return
        last_ok = None
        for step, step_grade in zip(self._chain.steps, self._chain.grades(), strict=True):
            if step_grade.status is Status.OK:
                last_ok = step.step_id
        self._selected_step = last_ok

    def _composite_target(self) -> tuple[str | None, ChainStep] | None:
        """`(input node id, target step)` the composite composes, or None.

        The target is the deepest node-backed ok step at or before the
        selection: a tab-side step (morlet, windowed count) has no rendered
        output to show, so selecting one shows the deepest frame the render
        actually produced. The input id is the node before the target, or
        None when the target is first and its input is the source itself.
        """
        steps = self._chain.steps
        ids = [step.step_id for step in steps]
        limit = ids.index(self._selected_step) if self._selected_step in ids else len(steps) - 1
        target: ChainStep | None = None
        upstream: str | None = None
        for index, (step, step_grade) in enumerate(zip(steps, self._chain.grades(), strict=True)):
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
        """A consumer that catches the composite pair as frames fly past.

        The wizard grabber's twin: it runs on the render thread inside a
        render that was happening anyway, indexes the `FrameResult` for two
        nodes, and never feeds anything back into the graph
        (`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`).
        """
        window = self._document.window
        target = self._composite_target()
        if window is None or target is None:
            return None
        upstream, step = target
        if step.node is None:
            return None
        node_id = step.node.node_id
        is_grid = step.kind_out is ChainKind.BLOCK_SERIES
        # A first step has no upstream node and the fallback base is the
        # player's frame — decoded through the scrub proxy, so blending it
        # under a full-resolution output reads as a quality slider the graph
        # does not have. When the first step is an identity rescale its
        # output *is* its input, bit for bit (`rescale_cpu`'s no-op path),
        # so the output is the honest base and the blend is honestly a no-op.
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
        """One frame at the playhead for the composite, when nothing bigger is due.

        Suppressed while a window render the graphs need is outstanding: the
        runner holds one pending request, and a stream of playhead frames
        would displace the window render from it — the graphs would then show
        a stale series until the next edit. Nothing is lost by waiting: the
        outstanding render's consumer grabs the same pair on its way past.

        Suppressed the same way while a refresh of its own is outstanding, and
        for a sharper reason: superseding a *single-frame* render kills it
        before its only delivery, so a refresh per playhead move at a rate the
        chain cannot render at delivers nothing at all rather than delivering
        late. One at a time makes the pane follow playback at whatever rate the
        chain can actually render, which is the honest ceiling.
        """
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
        # Recorded before the submit, not on its return: an idle runner emits
        # `render_started` synchronously inside `request_frame`, so an entry
        # added afterwards would miss `_hud_begin`'s check and the refresh
        # would clear the series it exists to leave alone.
        self._composite_revisions.add(expected)
        if self._runner.request_frame(self._chain.pipeline(), want, replicate, consumer=grab):
            self._composite_outstanding = expected
            self._composite_deferred = False
        else:
            self._composite_revisions.discard(expected)

    def _apply_composite(self, base: np.ndarray | None, over: np.ndarray, is_grid: bool) -> None:
        """Convert the grabbed pair on the GUI thread and hand it to the pane.

        A block-grid output has no image to overlay: the pane draws the grid
        itself, vectorially, from the detector state `_apply_block_state`
        feeds it — so here the grid case is just the base frame and a flag.
        """
        base_image = self._cropped_player_frame() if base is None else frame_to_qimage(base)
        over_image = None if is_grid else frame_to_qimage(over)
        self._composite.set_frames(base_image, over_image)
        self._composite.set_grid_visible(is_grid)

    def _cropped_player_frame(self) -> QImage | None:
        """The player's frame as the first step's input: replicate-cropped.

        The graph runs over the selected replicate's crop when one exists, so
        the source the composite shows under the first step's output must be
        the same region — otherwise the overlay would sit on footage the graph
        never saw. The ROI is in source pixels and the player's image may be a
        proxy, so the rectangle scales by the image's actual size.
        """
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
        self._block.setSpecialValueText(f"auto ({resolve_block(0, scale)})")
        self._submit_params(
            {"rescale": {"scale": scale}, "block_signal": {"scale": scale}}, "Set Downsample"
        )
        # After the submit, which is what moves the chain the floor reads. A
        # smaller working frame is fewer blocks at the same block size, so this
        # direction *lowers* the floor as often as it raises it.

    @Slot(str)
    def _on_normalize(self, mode: str) -> None:
        self._submit_params({"normalize": {"mode": mode}}, "Set Normalize")

    @Slot(int)
    def _on_block(self, block: int) -> None:
        self._submit_params({"block_signal": {"block": block}}, "Set Block Size")

    def _on_signal_switch(self, signal_id: str) -> None:
        """The quick-switch: swap the extraction in place, value band per signal.

        The § 8 settlement: the frequency band is in Hz and carries over, but
        the value band is in the signal's own units — a Jtt-tuned threshold
        read in LK px/s is the mockup cycle's clearest silent misread — so
        each signal remembers its own and starts wide open the first time.

        One macro, because it is one gesture that lawfully writes two things
        — the signal parameter and the restored value band — and Ctrl+Z
        returning the signal while leaving the other signal's band in place
        would recreate exactly the misread the memory exists to prevent.
        """
        step = self._block_step()
        old_signal = (
            str(step.node.params.get("signal", "")) if step is not None and step.node else ""
        )
        for other_id, button in self._signal_buttons.items():
            button.setChecked(other_id == signal_id)
        if old_signal == signal_id:
            return
        detector = self._chain.detector
        restored = detector.value_band
        if old_signal:
            self._value_band_memory[old_signal] = detector.value_band
            restored = self._value_band_memory.get(signal_id, DetectorState().value_band)
        node_id = self._node_id_for("block_signal")
        if (
            node_id is not None
            and node_id in self._document.pipeline
            and not self._wizard_lifecycle.is_open
        ):
            stack = self._document.undo_stack
            stack.beginMacro(f"Switch Signal to {_block_signal_label(signal_id)}")
            try:
                if restored != detector.value_band:
                    self._document.edit_detector({"value_band": restored}, "Set Value Band")
                self._knob_armed_at = perf_counter()
                self._document.edit_params({node_id: {"signal": signal_id}}, "Set Signal")
            finally:
                stack.endMacro()
        else:
            if restored != detector.value_band:
                self._set_detector(replace(detector, value_band=restored))
            self._set_node_params("block_signal", signal=signal_id)
            self._knob_edited()
        self.status_message.emit(
            f"signal → {_block_signal_label(signal_id)} (value band remembered per signal)"
        )

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
        # The drag tier has usually written this band into the chain already
        # (handles move live), so the document echo compares equal and skips —
        # correctly, except that the *transform* has not run for it. When the
        # echo cannot see the change, the full derivation is owed here.
        already = self._chain.detector.freq_band == (lo, hi)
        self._submit_detector({"freq_band": (lo, hi)}, "Set Frequency Band")
        if already:
            self._derive(reuse_band_power=False)

    def _on_value_drag(self, lo: float, hi: float) -> None:
        """The drag tier: live repaint from the local value, no history."""
        self._cheap_retune(replace(self._chain.detector, value_band=(lo, hi)))

    def _on_value_band(self, lo: float, hi: float) -> None:
        self._submit_detector({"value_band": (lo, hi)}, "Set Value Band")

    def _count_frac_for(self, lo: float, hi: float) -> tuple[float, float] | None:
        """Counts from the plot as fractions of the region — the one crossing.

        The first drag on the parked handles is what arms the detector; there
        is no separate control (plot contracts, § 2).
        """
        update = self._update
        if update is None:
            return None
        blocks = update.band_power.shape[1]
        return (
            lo / blocks if isfinite(lo) else max(lo, 0.0),
            hi / blocks if isfinite(hi) else hi,
        )

    def _on_count_drag(self, lo: float, hi: float) -> None:
        """The drag tier of the count threshold, `_on_value_drag`'s twin."""
        frac = self._count_frac_for(lo, hi)
        if frac is not None:
            self._cheap_retune(replace(self._chain.detector, count_frac=frac))

    def _on_count_band(self, lo: float, hi: float) -> None:
        frac = self._count_frac_for(lo, hi)
        if frac is not None:
            self._submit_detector({"count_frac": frac}, "Set Count Threshold")

    def _on_solo(self, block: object) -> None:
        """Solo is a repaint, not a re-derive — which is what makes it hoverable.

        Looking, not tuning: solo never reaches the document or a save. It also
        never reaches `recompute`, which does not read `solo_block` at all — the
        soloed block picks which column of the retained `band_power` the density
        plot overlays, and that choice is made in `_apply`. Routing it through
        `_cheap_retune` therefore spent a full in-band count and windowed mean
        over the whole series to arrive at a bit-identical update. That was
        affordable at one click per block and is not at one crossing per pointer
        move, which is what the gesture now costs (`composite_view`: hover
        solos, click pins).

        Published under `band_drag_repaint` all the same: it is the same
        continuously-emitted gesture the two-tier drag discipline exists for,
        and rule 4 wants the miss visible on screen if this ever stops being
        the cheap thing this docstring claims it is.
        """
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
        """The commit tier: one entry for the drag, at the value it ended on.

        The value is read back off the chain rather than off a slider, because
        both the tab's D slider and the wizard's share these three handlers and
        the drag tier has already written the live value there.
        """
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
        """Two tiers, the same split every other drag in this tab already has.

        D was the one control that wrote to the document on every step and
        leaned on `EditDetector.mergeWith` to fold the history back up
        afterwards. Merging fixes the undo stack; it does not make the work go
        away. Each step still pushed a command, moved the baseline, re-pinned
        the diff on the replicate, emitted `detector_changed`, re-resolved the
        detector through the pin chain, re-synced the knobs, and rebuilt every
        card caption — all before reaching the derive that is the only part the
        user is dragging for. That is why D was dead in the tab and merely slow
        in the wizard, which routes to `_cheap_retune` and skips every line of
        it: the asymmetry was the document round trip, not the arithmetic.

        So the drag repaints from the local value and the release is what the
        document records, exactly as `_on_value_drag` / `_on_value_band` do.
        A step arriving outside a gesture — keyboard, wheel, `setValue` — still
        commits immediately, because there is no release coming to commit it.
        """
        frames = max(frames, 1)
        if self._d_gesture is not None:
            self._cheap_retune(replace(self._chain.detector, window_frames=frames))
            return
        self._submit_detector({"window_frames": frames}, "Set Detection Window")

    @Slot(bool)
    def _on_centered(self, centered: bool) -> None:
        self._submit_detector({"centered": centered}, "Set Centered")

    # ---- structure -------------------------------------------------------

    @Slot(str)
    def _on_swap_requested(self, step_id: str) -> None:
        self._wizard_lifecycle.open(
            step_id,
            chain=self._chain,
            undo_index=self._document.undo_stack.index(),
            host=self,
            geometry=self.rect(),
        )

    @Slot(int)
    def _on_insert_requested(self, seam: int) -> None:
        self._wizard_lifecycle.open(
            seam,
            chain=self._chain,
            undo_index=self._document.undo_stack.index(),
            host=self,
            geometry=self.rect(),
        )

    # ---- the wizard --------------------------------------------------------

    @property
    def wizard(self) -> StepWizard | None:
        """The open wizard, None otherwise. For the window and for tests."""
        return self._wizard_lifecycle.wizard

    @Slot(object, str)
    def _adopt_wizard_chain(self, chain: LiveChain, step_id: str) -> None:
        """The expensive tier: adopt the provisional chain and render it.

        The provisional step is really in the chain — dashed card, real
        render, real graphs — which is what makes the preview honest and the
        Add button a formality rather than a leap.
        """
        del step_id
        self._chain = chain
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self._knob_armed_at = perf_counter()
        self.resubmit()

    @Slot(object)
    def _request_wizard_hover_preview(self, chain: LiveChain) -> None:
        """The cheap tier: one frame of a hypothetical, video pane only."""
        window = self._document.window
        if window is None:
            return
        grab = self._wizard_lifecycle.grabber(chain, window, self._playhead)
        if grab is None:
            return
        want = min(max(self._playhead, window.start), window.end - 1)
        replicate = self._document.selected_replicate
        # A hover is a single-frame look, not a render the graphs wait on.
        # Registered like a composite refresh so `_collector_start` and
        # `_hud_begin` leave the window series and the HUD alone.
        expected = self._runner.revision + 1
        self._composite_revisions.add(expected)
        # A hover takes the composite's slot rather than queueing behind it: it
        # is a gesture the pointer is still making, and the refresh it displaces
        # is a playhead the user is not looking at. Taking the slot is also what
        # keeps it accounted for — the displaced refresh never reports back.
        if self._runner.request_frame(chain.pipeline(), want, replicate, consumer=grab):
            self._composite_outstanding = expected
            self._composite_deferred = False
        else:
            self._composite_revisions.discard(expected)

    @Slot()
    def _restore_wizard_hover_preview(self) -> None:
        """The pointer left the candidates: the video returns to the selection."""
        if not self._wizard_lifecycle.is_open:
            return
        self._request_wizard_hover_preview(self._chain)

    @Slot(object)
    def _commit_wizard(self, event: WizardAccepted) -> None:
        """Add: the provisional step solidifies; the chain is already rendered.

        Only the structure lands here in the ordinary case. The session's
        tuning went through the document live, edit by edit, exactly as the
        tab's own — the one thing the document has not seen is the
        provisional step, whose minted parameters become its baseline through
        `sync_structure`. The net-diff write below is for the one session the
        live path cannot serve: a wizard opened before any pipeline reached
        the document, whose detector edits stayed local; when the edits went
        through live it compares equal and writes nothing.
        """
        step_id = event.step_id
        snapshot = event.snapshot
        if step_id is not None:
            self._ensure_body(step_id)
            self.status_message.emit(f"added '{step_id}'")
        self._document.sync_structure(self._chain.pipeline())
        if snapshot is not None and len(self._document.pipeline.nodes):
            before = snapshot.detector.as_settings_changes()
            after = self._chain.detector.as_settings_changes()
            changes = {name: value for name, value in after.items() if before[name] != value}
            if changes:
                self._document.edit_detector(changes, "Tune Detection")
        # The chain must end this handler as the resolved view of what the
        # document now holds — `sync_structure` kept the document's own
        # baselines for every pre-existing node, and a chain still carrying
        # the wizard's copies would show values a save does not.
        self._refresh_from_document()
        self._rebuild_stack()

    @Slot(object)
    def _restore_wizard_cancel(self, event: WizardCancelled) -> None:
        """Cancel/Esc: everything exactly as it was — stack rollback plus snapshot.

        Two restores because the session writes to two places: detector (and
        any committed-step param) edits went through the document as ordinary
        undoable commands and are rolled back off the stack; the provisional
        step and its params never reached the document and come back with the
        chain snapshot.
        """
        snapshot = event.snapshot
        undo_index = event.undo_index
        if undo_index is not None:
            self._document.undo_stack.setIndex(undo_index)
        if snapshot is not None and snapshot is not self._chain:
            self._chain = snapshot
            self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self.status_message.emit("wizard cancelled — chain restored")
        self.resubmit()

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
        """A committed extra step's card edit: same route as every upstream knob."""
        step = next((s for s in self._chain.steps if s.step_id == step_id), None)
        if step is None or step.node is None:
            return
        if step.node.node_id in self._document.pipeline:
            index = self._document.undo_stack.index()
            self._knob_armed_at = perf_counter()
            self._document.edit_params({step.node.node_id: {name: value}}, f"Set {name}")
            if self._document.undo_stack.index() == index:
                self._knob_armed_at = None
            return
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
        self._document.sync_structure(self._chain.pipeline())
        self.status_message.emit(f"removed '{step_id}'")
        self._rebuild_stack()
        self._derive(reuse_band_power=True)
        self.resubmit()

    @Slot()
    def _on_reset(self) -> None:
        """Parameters-not-structure: knobs and detector back, the chain stays.

        Through the document as one undo entry, so a reset that unpinned
        twelve arenas comes back with one Ctrl+Z. The nodes named are the
        ones the defaults chain knows; an inserted step keeps its parameters,
        exactly as the local reset always treated it.
        """
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

    # ---- source lifecycle ------------------------------------------------

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
        self._wizard_lifecycle.set_geometry(self.rect())

    @Slot()
    def _on_source_changed(self) -> None:
        """A new source: fresh chain at its frame rate, everything cleared."""
        self._wizard_lifecycle.close()
        self._value_band_memory.clear()
        fps = self._fps()
        self._chain = parity_chain(fps)
        self._defaults = parity_chain(fps)
        # Seed the fresh graph into the document so the first knob edit has a
        # baseline to move — this is what makes a save carry the chain even
        # when nothing was ever tuned. The echo returns with the tab's own
        # node ids and `_on_pipeline_changed` recognizes and skips it.
        self._document.sync_structure(self._chain.pipeline())
        self._collector = SeriesCollector(self._block_node_id() or "")
        self._series_start = None
        self._series2d = None
        self._update = None
        self._pooled_power = None
        self._density_surface = None
        # Dropped with the rest, so a new source cannot be scaled against the
        # old one's ceiling and the previous band power is not held alive by a
        # cache key nothing will ever match again.
        self._heat_source = None
        self._heat_max = 0.0
        self._playhead = 0
        self._knob_armed_at = None
        self._selected_step = None
        self._frame_image = None
        # A failure is a fact about the chain that raised it, and this is a
        # different one — carrying it over would blame the new replicate.
        self._derive_failure = None
        self._composite_grab.clear()
        self._composite_revisions.clear()
        self._series_pending = False
        self._composite_outstanding = None
        self._composite_deferred = False
        self._composite.set_frames(None, None)
        self._composite.set_notice("")
        self._composite.set_block_state(np.zeros(1, np.float32), np.zeros(1, bool), None)
        # A magnification is a view of *this* footage and does not carry to the
        # next one, exactly as the replicate viewport's does not.
        self._composite.reset_zoom()
        self._hud.set_span(0, 0)
        self._hud.begin()
        self._sync_widgets_from_chain()
        self._rebuild_stack()
        self._apply()
        self.resubmit()

    @Slot()
    def _on_selection_changed(self) -> None:
        """A different arena is under tuning: its settings return with it.

        Re-resolve first, then render — the knobs, captions, and bands must
        already show what *this* replicate runs with when its first frame
        arrives, or the screen would briefly claim the old arena's tuning
        over the new arena's footage. The render itself invalidates like a
        window move and rides the runner's latest-wins submission.
        """
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
