"""The Preferences pane.

Applies on change rather than on OK. Every setting here alters how the video
on screen behaves, so the user needs to see the effect while the pane is open
— dragging the proxy width and then hunting for a Close button to find out
what it did is the wrong loop. There is consequently no Cancel; Restore
Defaults is the way back.

The pane is small because the store is small, and the store is small because
`preferences.py` only holds settings something reads. Growing this beyond one
screen is a signal to reconsider whether the new setting is really a decision
the user should be making.
"""

from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from sieve.gui.preferences import (
    MAX_COARSE_INTERVAL_SECONDS,
    MAX_PROXY_WIDTH,
    MIN_COARSE_INTERVAL_SECONDS,
    MIN_PROXY_WIDTH,
    Preferences,
)

_ADAPTIVE_LABEL = "Switch to coarse seeking when scrubbing falls behind"
_ADAPTIVE_HELP = (
    "A seek into high-resolution footage costs more than a frame of scrubbing "
    "has to spare, and no amount of tuning changes that. When SIEVE notices "
    "scrubbing is not keeping up it starts showing the nearest frame on a "
    "coarse grid while you drag, which is instant, and decodes the exact frame "
    "when you let go. Turn this off to always decode the exact frame — "
    "accurate while dragging, but it will lag on slower machines."
)
_INTERVAL_HELP = "How far apart the coarse grid's frames are while you drag."
_RENDER_FED_LABEL = "Show the graph render's frames during playback"
_RENDER_FED_HELP = (
    "While the graphs are computing, SIEVE has already decoded every frame it "
    "needs — playback reuses them instead of decoding the file a second time, "
    "which is what makes the picture keep moving during a render. Playback "
    "loops over the part of the window that has been rendered so far. Turn "
    "this off to always decode independently: full wall-clock coverage of the "
    "window, at the cost of stuttering while renders fill."
)
_PROXY_HELP = (
    "Frames are decoded down to this width for display only. Lower is faster "
    "to scrub; higher shows more detail. Never affects analysis output."
)


class PreferencesDialog(QDialog):
    """Edits a `Preferences` store in place."""

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SIEVE Preferences")
        self.setModal(False)
        self._preferences = preferences

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_scrubbing_group())
        layout.addWidget(self._build_playback_group())
        layout.addWidget(self._build_display_group())
        layout.addStretch(1)

        buttons = QDialogButtonBox()
        self._restore_button = buttons.addButton(QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        self._restore_button.clicked.connect(self._on_restore_defaults)
        layout.addWidget(buttons)

        # The store can change from elsewhere — a restore, or a future second
        # window — so the pane follows it rather than assuming it is the only
        # writer.
        self._preferences.changed.connect(self._load)
        self._load()

    # ---- construction ----------------------------------------------------

    def _build_scrubbing_group(self) -> QGroupBox:
        group = QGroupBox("Scrubbing")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._adaptive_check = QCheckBox(_ADAPTIVE_LABEL)
        self._adaptive_check.setToolTip(_ADAPTIVE_HELP)
        self._adaptive_check.toggled.connect(self._on_adaptive_toggled)
        form.addRow(self._adaptive_check)
        form.addRow(_help_label(_ADAPTIVE_HELP))

        self._interval_spin = QDoubleSpinBox()
        self._interval_spin.setRange(MIN_COARSE_INTERVAL_SECONDS, MAX_COARSE_INTERVAL_SECONDS)
        self._interval_spin.setSingleStep(0.25)
        self._interval_spin.setDecimals(2)
        self._interval_spin.setSuffix(" s")
        self._interval_spin.setToolTip(_INTERVAL_HELP)
        self._interval_spin.valueChanged.connect(self._on_interval_changed)
        form.addRow("Coarse grid spacing:", self._interval_spin)

        return group

    def _build_playback_group(self) -> QGroupBox:
        group = QGroupBox("Playback")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._render_fed_check = QCheckBox(_RENDER_FED_LABEL)
        self._render_fed_check.setToolTip(_RENDER_FED_HELP)
        self._render_fed_check.toggled.connect(self._on_render_fed_toggled)
        form.addRow(self._render_fed_check)
        form.addRow(_help_label(_RENDER_FED_HELP))

        return group

    def _build_display_group(self) -> QGroupBox:
        group = QGroupBox("Display")
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._proxy_spin = QSpinBox()
        self._proxy_spin.setRange(MIN_PROXY_WIDTH, MAX_PROXY_WIDTH)
        self._proxy_spin.setSingleStep(160)
        self._proxy_spin.setSuffix(" px")
        self._proxy_spin.setToolTip(_PROXY_HELP)
        self._proxy_spin.valueChanged.connect(self._on_proxy_width_changed)
        form.addRow("Preview decode width:", self._proxy_spin)
        form.addRow(_help_label(_PROXY_HELP))

        return group

    # ---- store <-> widgets ------------------------------------------------

    @Slot()
    def _load(self) -> None:
        """Pull every value from the store without re-emitting changes."""
        widgets = (
            self._adaptive_check,
            self._interval_spin,
            self._render_fed_check,
            self._proxy_spin,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        self._adaptive_check.setChecked(self._preferences.adaptive_scrub)
        self._interval_spin.setValue(self._preferences.coarse_interval_seconds)
        self._render_fed_check.setChecked(self._preferences.render_fed_playback)
        self._proxy_spin.setValue(self._preferences.proxy_width)
        del blockers
        self._interval_spin.setEnabled(self._adaptive_check.isChecked())

    @Slot(bool)
    def _on_adaptive_toggled(self, enabled: bool) -> None:
        self._preferences.adaptive_scrub = enabled
        # The grid spacing only means anything when the grid can be used.
        self._interval_spin.setEnabled(enabled)

    @Slot(bool)
    def _on_render_fed_toggled(self, enabled: bool) -> None:
        self._preferences.render_fed_playback = enabled

    @Slot(float)
    def _on_interval_changed(self, seconds: float) -> None:
        self._preferences.coarse_interval_seconds = seconds

    @Slot(int)
    def _on_proxy_width_changed(self, width: int) -> None:
        self._preferences.proxy_width = width

    @Slot()
    def _on_restore_defaults(self) -> None:
        self._preferences.restore_defaults()


def _help_label(text: str) -> QLabel:
    """Wrapped, de-emphasised explanatory text under a control."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setEnabled(False)
    return label
