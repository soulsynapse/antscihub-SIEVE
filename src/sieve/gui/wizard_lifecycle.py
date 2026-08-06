"""The wizard lifecycle: the open inset, session rollback, and preview mailbox.

`StepWizard` is the widget that proposes a provisional chain. This controller
owns when that widget exists, what Cancel restores, and the one-frame mailbox
that feeds its video pane; it does not call back into the tab that hosts it.

The crossing signals are `chain_proposed`, `hover_preview_requested`,
`hover_ended`, `accepted`, `cancelled`, `seek_requested`, `scrub_requested`,
`value_band_changed`, `value_band_committed`, `count_band_changed`,
`count_band_committed`, `d_pressed`, `d_released`, `window_frames_changed`, and
`centered_toggled`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, QRect, Signal, Slot
from PySide6.QtWidgets import QWidget

from sieve.core.pipeline_model import ClipRange
from sieve.gui.chain_model import DetectorState, DetectorUpdate, LiveChain
from sieve.gui.density_plot import DensitySurface
from sieve.gui.wizard import StepWizard, frame_to_qimage, last_image_node_id

WIZARD_LIFECYCLE_SIGNALS = (
    "chain_proposed",
    "hover_preview_requested",
    "hover_ended",
    "accepted",
    "cancelled",
    "seek_requested",
    "scrub_requested",
    "value_band_changed",
    "value_band_committed",
    "count_band_changed",
    "count_band_committed",
    "d_pressed",
    "d_released",
    "window_frames_changed",
    "centered_toggled",
)

FrameConsumer = Callable[[object], None]


@dataclass(frozen=True, slots=True)
class WizardAccepted:
    """The session facts the tab needs to commit the accepted wizard."""

    snapshot: LiveChain | None
    step_id: str | None


@dataclass(frozen=True, slots=True)
class WizardCancelled:
    """The session facts the tab needs to roll the wizard back."""

    snapshot: LiveChain | None
    undo_index: int | None


class WizardLifecycle(QObject):
    """Own the wizard session and relay every tab-owned action as a signal."""

    #: Adopt this provisional chain and render it as the current truth.
    chain_proposed = Signal(object, str)
    #: Render a single hypothetical frame into the wizard's video pane.
    hover_preview_requested = Signal(object)
    #: Return the video pane to the selected provisional chain.
    hover_ended = Signal()
    #: The user accepted the provisional session.
    accepted = Signal(object)
    #: The user cancelled the provisional session.
    cancelled = Signal(object)
    #: Timeline gestures from the wizard's plot instances.
    seek_requested = Signal(int)
    scrub_requested = Signal(int)
    #: Detector graph gestures from the wizard's plot instances.
    value_band_changed = Signal(float, float)
    value_band_committed = Signal(float, float)
    count_band_changed = Signal(float, float)
    count_band_committed = Signal(float, float)
    #: Detector controls from the wizard's own D row.
    d_pressed = Signal()
    d_released = Signal()
    window_frames_changed = Signal(int)
    centered_toggled = Signal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._wizard: StepWizard | None = None
        self._snapshot: LiveChain | None = None
        self._undo_index: int | None = None
        self._provisional_id: str | None = None
        #: One-slot mailbox for the wizard's video frame. The render thread
        #: writes the array; the GUI thread converts it when frame cost or
        #: render completion reports that the frame passed.
        self._grab: list[np.ndarray] = []

    @property
    def is_open(self) -> bool:
        """Whether a wizard session is currently open."""
        return self._wizard is not None

    @property
    def wizard(self) -> StepWizard | None:
        """The open widget, None otherwise. Exposed for the window and tests."""
        return self._wizard

    @property
    def provisional_step_id(self) -> str | None:
        """The dashed card's step id while a provisional session is open."""
        return self._provisional_id

    def open(
        self,
        target: int | str,
        *,
        chain: LiveChain,
        undo_index: int,
        host: QWidget,
        geometry: QRect,
    ) -> None:
        """Open the inset helper for a seam index or a step id."""
        if self._wizard is not None:
            return
        self._snapshot = chain
        self._undo_index = undo_index
        wizard = StepWizard(chain, target, parent=host)
        self._wizard = wizard
        self._connect_wizard(wizard)
        wizard.setGeometry(geometry)
        wizard.show()
        wizard.raise_()
        wizard.setFocus()
        wizard.start()

    def _connect_wizard(self, wizard: StepWizard) -> None:
        wizard.chain_proposed.connect(self._on_chain_proposed)
        wizard.hover_preview.connect(self.hover_preview_requested)
        wizard.hover_ended.connect(self._on_hover_ended)
        wizard.accepted.connect(self._on_accepted)
        wizard.cancelled.connect(self._on_cancelled)

        for plot in (wizard.density, wizard.count):
            plot.pressed.connect(self.seek_requested)
            plot.scrubbed.connect(self.scrub_requested)
            plot.committed.connect(self.seek_requested)
        wizard.density.band_changed.connect(self.value_band_changed)
        wizard.density.band_committed.connect(self.value_band_committed)
        wizard.count.band_changed.connect(self.count_band_changed)
        wizard.count.band_committed.connect(self.count_band_committed)
        wizard.d_slider.sliderPressed.connect(self.d_pressed)
        wizard.d_slider.sliderReleased.connect(self.d_released)
        wizard.d_slider.valueChanged.connect(self.window_frames_changed)
        wizard.centered.toggled.connect(self.centered_toggled)

    @Slot(object, str)
    def _on_chain_proposed(self, chain: LiveChain, step_id: str) -> None:
        self._provisional_id = step_id
        self.chain_proposed.emit(chain, step_id)

    @Slot()
    def _on_hover_ended(self) -> None:
        if self._wizard is not None:
            self.hover_ended.emit()

    @Slot()
    def _on_accepted(self) -> None:
        event = WizardAccepted(snapshot=self._snapshot, step_id=self._provisional_id)
        self.close()
        self.accepted.emit(event)

    @Slot()
    def _on_cancelled(self) -> None:
        event = WizardCancelled(snapshot=self._snapshot, undo_index=self._undo_index)
        self.close()
        self.cancelled.emit(event)

    def close(self) -> None:
        """Close the widget without declaring either acceptance or cancellation."""
        wizard = self._wizard
        self._wizard = None
        self._snapshot = None
        self._undo_index = None
        self._provisional_id = None
        self._grab.clear()
        if wizard is not None:
            wizard.hide()
            wizard.deleteLater()

    def set_geometry(self, geometry: QRect) -> None:
        """Keep the inset fitted to the host widget while it is open."""
        if self._wizard is not None:
            self._wizard.setGeometry(geometry)

    def grabber(
        self,
        chain: LiveChain,
        window: ClipRange | None,
        playhead: int,
    ) -> FrameConsumer | None:
        """A render consumer that catches the wizard's video frame."""
        if self._wizard is None:
            return None
        node_id = last_image_node_id(chain)
        if window is None or node_id is None:
            return None
        want = min(max(playhead, window.start), window.end - 1)
        slot = self._grab

        def grab(result: object) -> None:
            frame = getattr(result, "outputs", {}).get(node_id)
            if frame is not None and getattr(result, "index", None) == want:
                slot[:] = [np.asarray(frame.data)]

        return grab

    def show_grabbed_frame(self) -> None:
        """Convert the newest grabbed frame on the GUI thread and show it."""
        if self._wizard is not None and self._grab:
            self._wizard.show_frame(frame_to_qimage(self._grab.pop()))

    def apply_state(
        self,
        *,
        update: DetectorUpdate | None,
        surface: DensitySurface | None,
        start: int,
        frames: int,
        detector: DetectorState,
        fps: float,
        temporal_ok: bool,
        detection_ok: bool,
        playhead: int,
    ) -> None:
        """Repaint the wizard's own plot instances from the tab's derivation."""
        if self._wizard is None:
            return
        self._wizard.apply_state(
            update=update,
            surface=surface,
            start=start,
            frames=frames,
            detector=detector,
            fps=fps,
            temporal_ok=temporal_ok,
            detection_ok=detection_ok,
            playhead=playhead,
        )
