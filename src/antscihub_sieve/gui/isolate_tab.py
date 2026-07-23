from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from antscihub_sieve.application.active_asset import (
    ActiveAsset,
    ActiveAssetController,
)
from antscihub_sieve.application.working_grid import (
    BlockIntent,
    ResolvedWorkingGrid,
    WorkingGridSettings,
    resolve_working_grid,
)
from antscihub_sieve.gui.isolate_player import IsolatePlayer
from antscihub_sieve.gui.isolate_session import IsolateSession
from antscihub_sieve.gui.isolate_timeline import IsolateTimeline


class IsolateTab(QWidget):
    def __init__(self, controller: ActiveAssetController) -> None:
        super().__init__()
        self._controller = controller
        self.session = IsolateSession()
        self._active_asset: ActiveAsset | None = None
        self.grid_settings = WorkingGridSettings()
        self.resolved_grid: ResolvedWorkingGrid | None = None
        self._build_ui()
        self._connect()
        self._resolve_grid()
        self._refresh()
        controller.active_asset_changed.connect(self._active_asset_changed)
        if controller.active_asset is not None:
            self._active_asset_changed(controller.active_asset)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.player = IsolatePlayer()
        self.channels = QWidget()
        self.channels.setMinimumWidth(220)
        channels_layout = QVBoxLayout(self.channels)
        channels_heading = QLabel("Channels")
        channels_heading.setStyleSheet("font-size: 17px; font-weight: 600;")
        self.channels_empty = QLabel("No channels added yet.")
        self.channels_empty.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        channels_layout.addWidget(channels_heading)
        channels_layout.addWidget(self.channels_empty)
        channels_layout.addStretch()
        self.splitter.addWidget(self.player)
        self.splitter.addWidget(self.channels)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([1000, 260])
        root.addWidget(self.splitter, 1)

        self.grid_panel = QWidget()
        grid_panel_layout = QVBoxLayout(self.grid_panel)
        grid_panel_layout.setContentsMargins(0, 0, 0, 0)
        grid_controls = QHBoxLayout()
        grid_heading = QLabel("Working grid")
        grid_heading.setStyleSheet("font-weight: 600;")
        grid_controls.addWidget(grid_heading)
        grid_controls.addWidget(QLabel("Downsample"))
        self.downsample_spin = QDoubleSpinBox()
        self.downsample_spin.setRange(0.001, 1.0)
        self.downsample_spin.setDecimals(3)
        self.downsample_spin.setSingleStep(0.05)
        self.downsample_spin.setValue(1.0)
        self.downsample_spin.setKeyboardTracking(False)
        self.downsample_spin.setToolTip(
            "Downsampling can remove spatial evidence that may be needed "
            "to detect behavior."
        )
        grid_controls.addWidget(self.downsample_spin)
        grid_controls.addWidget(QLabel("Block"))
        self.block_intent_combo = QComboBox()
        self.block_intent_combo.addItem("Auto", BlockIntent.AUTO.value)
        self.block_intent_combo.addItem(
            "Explicit", BlockIntent.EXPLICIT.value
        )
        grid_controls.addWidget(self.block_intent_combo)
        self.block_size_spin = QSpinBox()
        self.block_size_spin.setRange(1, 2_147_483_647)
        self.block_size_spin.setValue(64)
        self.block_size_spin.setSuffix(" working px")
        self.block_size_spin.setKeyboardTracking(False)
        self.block_size_spin.setEnabled(False)
        grid_controls.addWidget(self.block_size_spin)
        self.show_grid_check = QCheckBox("Show grid")
        grid_controls.addWidget(self.show_grid_check)
        grid_controls.addStretch()
        grid_panel_layout.addLayout(grid_controls)
        self.grid_readout = QLabel("Open an asset to resolve spatial geometry.")
        self.grid_readout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.grid_readout.setWordWrap(True)
        self.grid_readout.setToolTip(
            "Geometry only. No frames have been processed."
        )
        grid_panel_layout.addWidget(self.grid_readout)
        root.addWidget(self.grid_panel)

        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setMinimumWidth(84)
        transport.addWidget(self.play_button)
        controls = QFormLayout()
        controls.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.start_spin = self._time_spinbox()
        self.length_spin = self._time_spinbox()
        controls.addRow("Window start", self.start_spin)
        controls.addRow("Length", self.length_spin)
        transport.addLayout(controls)
        transport.addStretch()
        self.current_label = QLabel("00:00.000 · frame 0")
        transport.addWidget(self.current_label)
        root.addLayout(transport)

        self.timeline = IsolateTimeline()
        root.addWidget(self.timeline)
        self.status_label = QLabel(
            "Open footage in Replicates or use File > Open to begin."
        )
        root.addWidget(self.status_label)

    @staticmethod
    def _time_spinbox() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setSuffix(" s")
        spin.setKeyboardTracking(False)
        spin.setSingleStep(0.1)
        return spin

    def _connect(self) -> None:
        self.play_button.clicked.connect(self.session.toggle_play)
        self.start_spin.valueChanged.connect(self._start_changed)
        self.length_spin.valueChanged.connect(self._length_changed)
        self.timeline.frame_clicked.connect(self.session.timeline_scrub)
        self.timeline.scrub_finished.connect(
            self.session.settle_timeline_scrub
        )
        self.downsample_spin.valueChanged.connect(
            self._grid_controls_changed
        )
        self.block_intent_combo.currentIndexChanged.connect(
            self._grid_controls_changed
        )
        self.block_size_spin.valueChanged.connect(
            self._grid_controls_changed
        )
        self.show_grid_check.toggled.connect(self._show_grid_changed)
        self.session.state_changed.connect(self._refresh)
        self.session.frame_ready.connect(self._frame_ready)
        self.session.error_changed.connect(self.status_label.setText)

    def _active_asset_changed(self, asset: ActiveAsset) -> None:
        self._active_asset = asset
        self.player.clear()
        self._resolve_grid()
        self.status_label.setText("Loading video...")
        self.session.open_asset(asset)

    def _grid_controls_changed(self, _value: object = None) -> None:
        intent = BlockIntent(self.block_intent_combo.currentData())
        self.block_size_spin.setVisible(intent is BlockIntent.EXPLICIT)
        self.block_size_spin.setEnabled(
            self._active_asset is not None
            and intent is BlockIntent.EXPLICIT
        )
        self.grid_settings = WorkingGridSettings(
            downsample=self.downsample_spin.value(),
            block_intent=intent,
            explicit_block_size=(
                self.block_size_spin.value()
                if intent is BlockIntent.EXPLICIT
                else None
            ),
        )
        self._resolve_grid()

    def _show_grid_changed(self, visible: bool) -> None:
        self.player.set_working_grid(self.resolved_grid, visible=visible)

    def _resolve_grid(self) -> None:
        asset = self._active_asset
        enabled = asset is not None
        self.downsample_spin.setEnabled(enabled)
        self.block_intent_combo.setEnabled(enabled)
        self.show_grid_check.setEnabled(enabled)
        self.block_size_spin.setVisible(
            self.grid_settings.block_intent is BlockIntent.EXPLICIT
        )
        self.block_size_spin.setEnabled(
            enabled
            and self.grid_settings.block_intent is BlockIntent.EXPLICIT
        )
        if asset is None:
            self.resolved_grid = None
            self.grid_readout.setText(
                "Open an asset to resolve spatial geometry."
            )
        else:
            self.resolved_grid = resolve_working_grid(
                asset.width,
                asset.height,
                self.grid_settings,
            )
            self.grid_readout.setText(
                self._grid_readout_text(self.resolved_grid)
            )
        self.player.set_working_grid(
            self.resolved_grid,
            visible=self.show_grid_check.isChecked(),
        )

    @staticmethod
    def _grid_readout_text(grid: ResolvedWorkingGrid) -> str:
        if grid.block_intent is BlockIntent.AUTO:
            block = (
                f"auto ({grid.resolved_block_size} working px; "
                f"about {grid.base_source_block} source px)"
            )
        else:
            block = f"{grid.resolved_block_size} working px"
        edges: list[str] = []
        if grid.right_edge_width < grid.resolved_block_size:
            edges.append(f"right {grid.right_edge_width} px")
        if grid.bottom_edge_height < grid.resolved_block_size:
            edges.append(f"bottom {grid.bottom_edge_height} px")
        edge_text = ", ".join(edges) if edges else "full edge cells"
        return (
            f"Source {grid.source_width} x {grid.source_height} px -> "
            f"Working {grid.work_width} x {grid.work_height} px; "
            f"Block {block}; Grid {grid.rows} rows x {grid.columns} columns; "
            f"{edge_text}"
        )

    def _start_changed(self, seconds: float) -> None:
        self.session.set_window_start(
            self.session.frame_at_seconds(seconds)
        )

    def _length_changed(self, seconds: float) -> None:
        self.session.set_window_length(
            self.session.frames_for_seconds(seconds)
        )

    def _frame_ready(
        self, frame: int, raw: bytes, width: int, height: int
    ) -> None:
        self.player.set_frame(raw, width, height)
        self.status_label.setText("Ready")

    def _refresh(self) -> None:
        loaded = self.session.loaded
        can_loop = self.session.can_loop
        self.play_button.setEnabled(can_loop)
        self.start_spin.setEnabled(can_loop)
        self.length_spin.setEnabled(can_loop)
        self.play_button.setText("Pause" if self.session.playing else "Play")
        if not loaded:
            self.timeline.set_state(0, 0, 0, 0)
            if not self.session.error_text:
                self.current_label.setText("00:00.000 · frame 0")
            return

        total_seconds = self.session.seconds_for_frame(
            self.session.frame_count
        )
        minimum_seconds = self.session.seconds_for_frame(
            self.session.ui_minimum_length()
        )
        maximum_seconds = self.session.seconds_for_frame(
            self.session.ui_maximum_length()
        )
        self.start_spin.blockSignals(True)
        self.length_spin.blockSignals(True)
        self.start_spin.setRange(
            0.0,
            self.session.seconds_for_frame(
                self.session.frame_count - self.session.window_length
            ),
        )
        self.length_spin.setRange(minimum_seconds, maximum_seconds)
        self.start_spin.setValue(
            self.session.seconds_for_frame(self.session.window_start)
        )
        self.length_spin.setValue(
            self.session.seconds_for_frame(self.session.window_length)
        )
        self.start_spin.setToolTip(
            f"Frame {self.session.window_start} of {self.session.frame_count - 1}"
        )
        self.length_spin.setToolTip(
            f"{self.session.window_length} frames; asset duration {total_seconds:.3f} s"
        )
        self.start_spin.blockSignals(False)
        self.length_spin.blockSignals(False)
        current_seconds = self.session.seconds_for_frame(
            self.session.current_frame
        )
        self.current_label.setText(
            f"{current_seconds:09.3f} s · frame "
            f"{self.session.current_frame} / {self.session.frame_count - 1}"
            f"{' (extent estimated)' if self.session.extent_is_estimated else ''}"
        )
        self.timeline.setToolTip(
            "Navigable extent is estimated from available media metadata."
            if self.session.extent_is_estimated
            else "Navigable extent is verified."
        )
        self.timeline.set_state(
            self.session.frame_count,
            self.session.window_start,
            self.session.window_stop,
            self.session.current_frame,
        )
        if self.session.frame_count < 2:
            self.status_label.setText(
                "A looping time window requires at least two decodable frames."
            )

    def handle_shortcut(self, command: str) -> None:
        if command == "toggle":
            self.session.toggle_play()
        elif command == "left":
            self.session.step(-1)
        elif command == "right":
            self.session.step(1)
        elif command == "shift_left":
            self.session.step(-self.session.frames_for_seconds(1.0))
        elif command == "shift_right":
            self.session.step(self.session.frames_for_seconds(1.0))
        elif command == "home":
            self.session.seek_home()
        elif command == "end":
            self.session.seek_end()

    def shutdown(self) -> None:
        self.session.close()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.shutdown()
        super().closeEvent(event)
