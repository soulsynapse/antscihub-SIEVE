from __future__ import annotations

import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QEvent, QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QKeySequence, QShortcut, QUndoCommand, QUndoStack
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QAbstractItemView, QFrame, QHeaderView, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QInputDialog, QSlider, QSplitter, QStyle, QTableWidget,
    QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from antscihub_sieve.application.active_asset import ActiveAsset, ActiveAssetController
from antscihub_sieve.application.assets import AssetService
from antscihub_sieve.application.derivation import DerivationService
from antscihub_sieve.application.layouts import LayoutService
from antscihub_sieve.errors import SieveError
from antscihub_sieve.gui.frame_view import FrameView
from antscihub_sieve.media.session import MediaSession


class DecodeThread(QThread):
    frame_ready = pyqtSignal(int, bytes)
    decode_error = pyqtSignal(str)

    def __init__(self, session: MediaSession) -> None:
        super().__init__(); self.session = session; self._condition = threading.Condition(); self._requested: int | None = None; self._stopping = False

    def request(self, frame: int) -> None:
        with self._condition: self._requested = frame; self._condition.notify()

    def stop(self) -> None:
        with self._condition: self._stopping = True; self._condition.notify()
        self.session.interrupt()

    def run(self) -> None:
        while True:
            with self._condition:
                while self._requested is None and not self._stopping: self._condition.wait()
                if self._stopping: return
                frame = self._requested; self._requested = None
            try:
                raw = self.session.read_frame_rgb(frame)
                with self._condition:
                    if self._requested is not None: continue
                self.frame_ready.emit(frame, raw)
            except SieveError as exc:
                if self._stopping: return
                self.decode_error.emit(f"{exc.code}: {exc.message}")


class DeriveThread(QThread):
    progress = pyqtSignal(dict); finished_result = pyqtSignal(dict); failed = pyqtSignal(str)

    def __init__(self, service: DerivationService, parent: str, output: str, profile: str, region_ids: list[str]) -> None:
        super().__init__(); self.service = service; self.parent = parent; self.output = output; self.profile = profile; self.region_ids = region_ids

    def run(self) -> None:
        try: self.finished_result.emit(self.service.run(self.parent, out=self.output, profile=self.profile, region_ids=self.region_ids, progress=self.progress.emit))
        except Exception as exc: self.failed.emit(str(exc))

    def cancel(self) -> None: self.service.cancel()


class PlanThread(QThread):
    planned = pyqtSignal(dict); failed = pyqtSignal(str)

    def __init__(self, service: DerivationService, parent: str, output: str, profile: str, region_ids: list[str]) -> None:
        super().__init__(); self.service = service; self.parent = parent; self.output = output; self.profile = profile; self.region_ids = region_ids

    def run(self) -> None:
        try: self.planned.emit(self.service.plan(self.parent, out=self.output, profile=self.profile, region_ids=self.region_ids))
        except SieveError as exc: self.failed.emit(f"{exc.code}: {exc.message}")
        except Exception as exc: self.failed.emit(str(exc))


class LayoutSnapshotCommand(QUndoCommand):
    def __init__(
        self,
        workspace: "ReplicateWorkspace",
        text: str,
        before: dict[str, Any],
        after: dict[str, Any],
        selected_before: str | None,
        selected_after: str | None,
    ) -> None:
        super().__init__(text)
        self.workspace = workspace
        self.before = deepcopy(before)
        self.after = deepcopy(after)
        self.selected_before = selected_before
        self.selected_after = selected_after

    def undo(self) -> None:
        self.workspace._apply_layout_snapshot(self.before, self.selected_before)

    def redo(self) -> None:
        self.workspace._apply_layout_snapshot(self.after, self.selected_after)


class DeriveDialog(QDialog):
    def __init__(self, drafts: list[dict[str, Any]], parent: str, service: DerivationService) -> None:
        super().__init__(); self.setWindowTitle("Create child replicates"); layout = QVBoxLayout(self)
        self.drafts = drafts; self.parent = parent; self.service = service
        layout.addWidget(QLabel("Selected draft regions")); self.listing = QListWidget()
        for region in drafts:
            x0, y0, x1, y1 = region["box_xyxy"]; item = QListWidgetItem(f"{region['label']} — [{x0}, {y0}, {x1}, {y1}] — {x1-x0}×{y1-y0}"); item.setData(Qt.ItemDataRole.UserRole, region["region_id"]); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Checked); self.listing.addItem(item)
        layout.addWidget(self.listing); self.output = QLineEdit(str(Path(parent).parent / "replicates")); browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse); output_row = QHBoxLayout(); output_row.addWidget(self.output); output_row.addWidget(browse)
        self.profile = QComboBox(); self.profile.addItems(["lossless", "high-quality", "compact"]); form = QFormLayout(); form.addRow("Output root", output_row); form.addRow("Encoding profile", self.profile); layout.addLayout(form)
        self.warning = QLabel(""); layout.addWidget(self.warning); self.plan_progress = QProgressBar(); self.plan_progress.setRange(0, 0); self.plan_progress.setTextVisible(False); self.plan_progress.hide(); layout.addWidget(self.plan_progress)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); self.start_button = buttons.button(QDialogButtonBox.StandardButton.Ok); self.start_button.setText("Start")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons); self.resize(620, 420)
        self._plan_thread: PlanThread | None = None; self._plan_dirty = False
        self.output.textChanged.connect(self._refresh_plan); self.profile.currentTextChanged.connect(self._refresh_plan); self.listing.itemChanged.connect(self._refresh_plan); self._refresh_plan()

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output root", self.output.text())
        if path: self.output.setText(path)

    def _refresh_plan(self, *_: object) -> None:
        if not self.output.text().strip(): self.start_button.setEnabled(False); self.warning.setText("Choose an output root."); return
        selected = self.selected_ids()
        if not selected: self.start_button.setEnabled(False); self.warning.setText("Select at least one draft region."); return
        if self._plan_thread is not None:
            self._plan_dirty = True; return
        self.start_button.setEnabled(False); self.warning.setText("Checking output plan…"); self.plan_progress.show()
        thread = PlanThread(self.service, self.parent, self.output.text(), self.profile.currentText(), selected); self._plan_thread = thread
        thread.planned.connect(self._plan_ready); thread.failed.connect(self._plan_failed); thread.finished.connect(self._plan_finished); thread.start()

    def _plan_ready(self, plan: dict[str, Any]) -> None:
        collisions = [item for item in plan["regions"] if item["collision"]]
        self.warning.setText(f"Planned: {len(plan['regions'])} portable child package(s)." + (f" {len(collisions)} output collision(s)." if collisions else " No output collisions."))
        self.start_button.setEnabled(not collisions and not self._plan_dirty)
        self.listing.blockSignals(True)
        try:
            outputs = {item["region_id"]: item["output_directory"] for item in plan["regions"]}
            for row in range(self.listing.count()):
                item = self.listing.item(row); item.setToolTip(outputs.get(item.data(Qt.ItemDataRole.UserRole), ""))
        finally:
            self.listing.blockSignals(False)

    def _plan_failed(self, message: str) -> None:
        self.warning.setText(message); self.start_button.setEnabled(False)

    def _plan_finished(self) -> None:
        thread = self._plan_thread; self._plan_thread = None
        if thread: thread.deleteLater()
        self.plan_progress.hide()
        if self._plan_dirty:
            self._plan_dirty = False; self._refresh_plan()

    def done(self, result: int) -> None:
        if self._plan_thread is not None:
            self._plan_thread.wait()
        super().done(result)

    def selected_ids(self) -> list[str]:
        return [self.listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.listing.count()) if self.listing.item(i).checkState() == Qt.CheckState.Checked]


class ReplicateWorkspace(QWidget):
    def __init__(self, controller: ActiveAssetController | None = None) -> None:
        super().__init__(); self.controller = controller or ActiveAssetController(); self.assets = AssetService(); self.layouts = LayoutService(self.assets)
        self.undo_stack = QUndoStack(self)
        self.asset_info: dict[str, Any] | None = None; self.layout_doc: dict[str, Any] | None = None; self.session: MediaSession | None = None; self.decoder: DecodeThread | None = None
        self.current_frame = 0; self.requested_frame = 0; self.playing = False; self.derive_thread: DeriveThread | None = None
        self._derive_region_ids: list[str] = []; self._derive_parent: str | None = None
        self._build_ui(); self._connect(); self._show_empty()
        self.controller.active_asset_changed.connect(self._active_asset_changed)
        if self.controller.active_asset is not None: self._active_asset_changed(self.controller.active_asset)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.splitter = QSplitter(); self.view = FrameView(); self.inspector = QWidget(); inspector_layout = QVBoxLayout(self.inspector); inspector_layout.setContentsMargins(6, 0, 0, 0)
        self.busy_overlay = QFrame(); self.busy_overlay.setObjectName("extractionProgress"); self.busy_overlay.setStyleSheet("#extractionProgress { background: #eff6ff; border: 1px solid #60a5fa; border-radius: 7px; }")
        progress_layout = QVBoxLayout(self.busy_overlay); progress_layout.setContentsMargins(12, 9, 12, 9); progress_layout.setSpacing(5); progress_heading = QHBoxLayout(); title = QLabel("Creating child replicates"); title.setStyleSheet("font-weight: 600;"); self.cancel_button = QPushButton("Cancel"); progress_heading.addWidget(title); progress_heading.addStretch(); progress_heading.addWidget(self.cancel_button); progress_layout.addLayout(progress_heading)
        self.progress_detail = QLabel("Preparing encoding plan…"); self.progress_detail.setWordWrap(True); progress_layout.addWidget(self.progress_detail); self.progress = QProgressBar(); progress_layout.addWidget(self.progress); self.busy_overlay.hide(); inspector_layout.addWidget(self.busy_overlay)
        self.replicate_table = QTableWidget(0, 4); self.replicate_table.setHorizontalHeaderLabels(["Replicate", "State", "Children", ""])
        self.replicate_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.replicate_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.replicate_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.replicate_table.verticalHeader().hide(); self.replicate_table.setShowGrid(False); self.replicate_table.setAlternatingRowColors(True)
        header = self.replicate_table.horizontalHeader(); header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        inspector_layout.addWidget(self.replicate_table, 1)
        edit_buttons = QHBoxLayout(); self.rename_button = QPushButton("Rename"); self.delete_button = QPushButton("Delete"); self.clear_button = QPushButton("Clear drafts")
        for button in (self.rename_button, self.delete_button, self.clear_button): edit_buttons.addWidget(button)
        inspector_layout.addLayout(edit_buttons)
        child_buttons = QHBoxLayout(); self.open_child_button = QPushButton("Open"); self.locate_child_button = QPushButton("Locate")
        for button in (self.open_child_button, self.locate_child_button): child_buttons.addWidget(button)
        inspector_layout.addLayout(child_buttons)
        self.summary_box = QFrame(); self.summary_box.setFrameShape(QFrame.Shape.StyledPanel); summary_layout = QVBoxLayout(self.summary_box); summary_layout.setContentsMargins(10, 7, 10, 7); summary_layout.setSpacing(2); summary_layout.addWidget(QLabel("Status")); self.summary_label = QLabel("0 replicates\nNo replicates yet"); summary_layout.addWidget(self.summary_label); inspector_layout.addWidget(self.summary_box)
        self.splitter.addWidget(self.view); self.splitter.addWidget(self.inspector)
        self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 1); self.splitter.setSizes([1000, 1000])
        root.addWidget(self.splitter, 1)
        transport = QHBoxLayout(); self.play_button = QPushButton("Play"); self.slider = QSlider(Qt.Orientation.Horizontal); self.frame_label = QLabel("00:00.000 / 00:00.000 · frame 0 / 0")
        transport.addWidget(self.play_button); transport.addWidget(self.slider, 1); transport.addWidget(self.frame_label); root.addLayout(transport)
        tools = QHBoxLayout(); self.draw_check = QCheckBox("Draw boxes"); self.draw_check.setChecked(True); self.stamp_check = QCheckBox("Fixed-size stamp"); self.stamp_check.setChecked(True); self.view.stamp_enabled = True; self.import_button = QPushButton("Import template…"); self.export_button = QPushButton("Export template…"); self.derive_button = QPushButton("Create child replicates…")
        for widget in (self.draw_check, self.stamp_check, self.import_button, self.export_button): tools.addWidget(widget)
        tools.addStretch(); self.derive_button.setMinimumSize(250, 46); self.derive_button.setCursor(Qt.CursorShape.PointingHandCursor); self.derive_button.setStyleSheet("QPushButton { background: #2563eb; color: white; border: 1px solid #1d4ed8; border-radius: 6px; font-size: 15px; font-weight: 600; padding: 8px 18px; } QPushButton:hover { background: #1d4ed8; } QPushButton:pressed { background: #1e40af; } QPushButton:disabled { background: #94a3b8; border-color: #94a3b8; }"); tools.addWidget(self.derive_button); root.addLayout(tools)
        status = QHBoxLayout(); self.status_label = QLabel("Ready"); status.addWidget(self.status_label, 1); root.addLayout(status)
        self.play_timer = QTimer(self); self.scrub_timer = QTimer(self); self.scrub_timer.setSingleShot(True); self.scrub_timer.setInterval(80)
        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self); self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)

    def _connect(self) -> None:
        self.view.installEventFilter(self); self.replicate_table.installEventFilter(self)
        self.play_button.clicked.connect(self.toggle_play); self.play_timer.timeout.connect(self._play_tick); self.slider.valueChanged.connect(self._slider_changed); self.scrub_timer.timeout.connect(self._request_current)
        self.delete_shortcut.activated.connect(self.delete_region); self.backspace_shortcut.activated.connect(self.delete_region)
        self.view.region_created.connect(self._add_region); self.view.region_moved.connect(self._move_region); self.view.selection_changed.connect(self._view_selection); self.view.child_open_requested.connect(self.open_child_index); self.view.back_requested.connect(self.open_parent)
        self.replicate_table.currentCellChanged.connect(self._table_selection); self.replicate_table.cellClicked.connect(self._focus_selected); self.replicate_table.cellDoubleClicked.connect(lambda *_: self.open_selected_child()); self.rename_button.clicked.connect(self.rename_region); self.delete_button.clicked.connect(self.delete_region); self.clear_button.clicked.connect(self.clear_regions)
        self.open_child_button.clicked.connect(self.open_selected_child); self.locate_child_button.clicked.connect(self.locate_child)
        self.draw_check.toggled.connect(lambda v: setattr(self.view, "draw_enabled", v)); self.stamp_check.toggled.connect(lambda v: setattr(self.view, "stamp_enabled", v))
        self.import_button.clicked.connect(self.import_template); self.export_button.clicked.connect(self.export_template); self.derive_button.clicked.connect(self.start_derivation); self.cancel_button.clicked.connect(self.cancel_derivation)

    def eventFilter(self, watched: object, event: object) -> bool:
        if watched in {self.view, self.replicate_table} and isinstance(event, QEvent) and event.type() == QEvent.Type.KeyPress and event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}:  # type: ignore[attr-defined]
            self.delete_region(); return True
        return super().eventFilter(watched, event)

    def _show_empty(self) -> None:
        for widget in (self.play_button, self.slider, self.rename_button, self.delete_button, self.clear_button, self.open_child_button, self.locate_child_button, self.import_button, self.export_button, self.derive_button): widget.setEnabled(False)

    def open_asset(self, reference: str) -> None:
        """Request an application-level asset change (kept as a convenience API)."""
        try:
            self.controller.open_asset(reference)
        except SieveError as exc: QMessageBox.critical(self, "Could not open asset", f"{exc.code}: {exc.message}"); self.status_label.setText(f"{exc.code}: {exc.message}")

    def _active_asset_changed(self, active: ActiveAsset) -> None:
        self.undo_stack.clear()
        try:
            inspected = self.assets.inspect(active.sidecar_path)
            self._close_session(); session = MediaSession(Path(inspected["media_path"])); self.asset_info = inspected; self.session = session
            try:
                loaded = self.layouts.load(inspected["media_path"], create=True)
                active_parent = self._derive_parent and Path(self._derive_parent).resolve() == Path(inspected["media_path"]).resolve()
                if not active_parent:
                    recovery = self.layouts.recover_interrupted(inspected["media_path"]); loaded = recovery
                    if recovery["recovered_count"]:
                        self.status_label.setText(f"Recovered {recovery['recovered_count']} interrupted extraction(s) as canceled")
            except SieveError as exc:
                answer = QMessageBox.question(self, "Layout could not be loaded", f"{exc.code}: {exc.message}\n\nStart a new empty layout?")
                if answer != QMessageBox.StandardButton.Yes: loaded = {"layout": None}
                else:
                    old = Path(inspected["media_path"]).with_suffix(".replicate-layout.json"); old.rename(old.with_suffix(old.suffix + ".invalid")); loaded = self.layouts.create(inspected["media_path"])
            self.layout_doc = loaded["layout"]; self.current_frame = self.requested_frame = 0
            self.decoder = DecodeThread(session); self.decoder.frame_ready.connect(self._frame_ready); self.decoder.decode_error.connect(self.status_label.setText); self.decoder.start()
            self._refresh_asset(); self._refresh_layout(); self._request_frame(0)
        except SieveError as exc: QMessageBox.critical(self, "Could not open asset", f"{exc.code}: {exc.message}"); self.status_label.setText(f"{exc.code}: {exc.message}")

    def _close_session(self) -> None:
        self.playing = False; self.play_timer.stop()
        if self.decoder: self.decoder.stop(); self.decoder.wait(3000); self.decoder = None
        if self.session: self.session.close(); self.session = None

    def _refresh_asset(self) -> None:
        assert self.asset_info and self.session
        meta = self.session.metadata
        self.slider.setRange(0, self.session.frame_count - 1); self.play_timer.setInterval(max(1, round(1000 * meta["fps_den"] / meta["fps_num"])))
        for widget in (self.play_button, self.slider, self.import_button, self.export_button): widget.setEnabled(True)

    def _refresh_layout(self) -> None:
        drafts = self.layout_doc["draft_regions"] if self.layout_doc else []; children = self.layout_doc["created_children"] if self.layout_doc else []
        previous = self._selected_record(); selected_key = previous.get("key") if previous else (("draft", self.view.selected_id) if self.view.selected_id else None)
        rows: list[dict[str, Any]] = []
        for region in drafts:
            x0, y0, x1, y1 = region["box_xyxy"]; state = region["state"]
            error = region.get("last_error"); details = [f"Size: {x1-x0} × {y1-y0}", f"Coordinates: [{x0}, {y0}, {x1}, {y1}]", f"Region id: {region['region_id']}"]
            if error: details += [f"Error: {error.get('code', 'FAILED')}", str(error.get("message", ""))]
            rows.append({"key": ("draft", region["region_id"]), "type": "draft", "region_id": region["region_id"], "label": region["label"], "color": region["color"], "state": state.title(), "children": "—", "tooltip": "\n".join(details), "created_utc": region.get("created_utc", "")})
        for index, child in enumerate(children):
            snap, identity = child["region_snapshot"], child["child"]; x0, y0, x1, y1 = snap["box_xyxy"]
            child_path = self._lightweight_child_path(index); state = "Ready" if child_path else "Missing"; direct_count: int | None = None
            if child_path:
                try:
                    child_layout = self.layouts.load(child_path)["layout"]
                    direct_count = 0 if child_layout is None else len(child_layout["draft_regions"]) + len(child_layout["created_children"])
                except SieveError: direct_count = None
            details = [f"Size: {x1-x0} × {y1-y0}", f"Coordinates: [{x0}, {y0}, {x1}, {y1}]", f"Asset id: {identity['asset_id']}"]
            if child_path: details.append(f"Path: {child_path}")
            else: details += ["Child asset is not currently reachable.", *[f"Location hint: {hint}" for hint in identity.get("location_hints", [])]]
            rows.append({"key": ("child", index), "type": "child", "child_index": index, "region_id": snap["region_id"], "label": snap["label"], "color": snap["color"], "state": state, "children": str(direct_count) if direct_count is not None else "—", "tooltip": "\n".join(details), "created_utc": child.get("created_utc", "")})
        rows.sort(key=lambda row: (row["created_utc"], row["label"].casefold()))
        self.replicate_table.blockSignals(True); self.replicate_table.setRowCount(len(rows)); selected_row = -1
        for row_index, row in enumerate(rows):
            label_item = QTableWidgetItem(row["label"]); label_item.setForeground(QColor(row["color"])); label_item.setData(Qt.ItemDataRole.UserRole, row)
            state_item = QTableWidgetItem(row["state"]); children_item = QTableWidgetItem(row["children"]); children_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for item in (label_item, state_item, children_item): item.setToolTip(row["tooltip"])
            self.replicate_table.setItem(row_index, 0, label_item); self.replicate_table.setItem(row_index, 1, state_item); self.replicate_table.setItem(row_index, 2, children_item)
            folder_button = QToolButton(); folder_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)); folder_button.setAutoRaise(True)
            folder_button.setAccessibleName(f"Open {row['label']} folder"); folder_button.setToolTip("Open replicate folder in Explorer")
            if row["type"] == "child" and row["state"] == "Ready":
                folder_button.setCursor(Qt.CursorShape.PointingHandCursor)
                folder_button.clicked.connect(lambda _checked=False, index=row["child_index"]: self.open_child_folder(index))
            else:
                folder_button.setEnabled(False)
            self.replicate_table.setCellWidget(row_index, 3, folder_button)
            if row["key"] == selected_key: selected_row = row_index
        if selected_row >= 0: self.replicate_table.selectRow(selected_row); self.replicate_table.setCurrentCell(selected_row, 0)
        else: self.replicate_table.clearSelection(); self.replicate_table.setCurrentCell(-1, -1)
        self.replicate_table.blockSignals(False); self.view.set_layout(drafts, children, self.view.selected_id)
        self._update_summary(rows); self._update_action_buttons()

    def _lightweight_child_path(self, index: int) -> Path | None:
        if not self.layout_doc or not self.asset_info: return None
        child = self.layout_doc["created_children"][index]["child"]; layout_path = Path(self.asset_info["media_path"]).with_suffix(".replicate-layout.json")
        for hint in child.get("location_hints", []):
            path = Path(hint); candidate = path if path.is_absolute() else (layout_path.parent / path).resolve()
            try:
                found = self.assets.inspect(candidate)
                if not found["registered"]: continue
                asset = found["asset"]
                media = Path(found["media_path"])
                if (media.is_file() and media.stat().st_size == asset["media"]["size_bytes"]
                        and asset["asset_id"] == child["asset_id"]
                        and asset["media"]["content_sha256"] == child["content_sha256"]):
                    return Path(found["sidecar_path"])
            except SieveError: pass
        return None

    def _selected_record(self) -> dict[str, Any] | None:
        row = self.replicate_table.currentRow(); item = self.replicate_table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_summary(self, rows: list[dict[str, Any]]) -> None:
        counts: dict[str, int] = {}
        for row in rows: counts[row["state"].lower()] = counts.get(row["state"].lower(), 0) + 1
        parts = []
        for state in ("ready", "draft", "extracting", "verifying", "failed", "canceled", "missing"):
            count = counts.get(state, 0)
            if count: parts.append(f"{count} {'drafts' if state == 'draft' and count != 1 else state}")
        total = len(rows); self.summary_label.setText(f"{total} {'replicate' if total == 1 else 'replicates'}\n" + (" · ".join(parts) if parts else "No replicates yet"))

    def _update_action_buttons(self) -> None:
        selected = self._selected_record(); active = self.derive_thread is not None
        is_draft = bool(selected and selected["type"] == "draft"); is_child = bool(selected and selected["type"] == "child")
        can_delete = is_draft or bool(is_child and selected["state"] == "Missing")
        self.rename_button.setEnabled(is_draft and not active); self.delete_button.setEnabled(can_delete and not active)
        self.clear_button.setEnabled(not active and bool(self.layout_doc and any(r["state"] == "draft" for r in self.layout_doc["draft_regions"])))
        self.open_child_button.setEnabled(is_child and selected["state"] == "Ready"); self.locate_child_button.setEnabled(is_child and not active)
        candidates = bool(self.layout_doc and any(r["state"] in {"draft", "failed", "canceled"} for r in self.layout_doc["draft_regions"]))
        self.derive_button.setEnabled(candidates and not active)

    def _request_frame(self, frame: int) -> None:
        if not self.decoder or not self.session: return
        self.requested_frame = min(max(0, frame), self.session.frame_count - 1); self.slider.blockSignals(True); self.slider.setValue(self.requested_frame); self.slider.blockSignals(False); self._update_time_label(self.requested_frame); self.decoder.request(self.requested_frame)

    def _request_current(self) -> None: self._request_frame(self.requested_frame)
    def _slider_changed(self, frame: int) -> None: self.requested_frame = frame; self._update_time_label(frame); self.scrub_timer.start()

    def _frame_ready(self, frame: int, raw: bytes) -> None:
        if frame != self.requested_frame or not self.session: return
        self.current_frame = frame; self.view.set_frame(raw, self.session.metadata["width"], self.session.metadata["height"]); self.status_label.setText("Ready")

    def _update_time_label(self, frame: int) -> None:
        if not self.session: return
        current = float(self.session.timestamp_for_frame(frame)); total = self.session.metadata["duration_seconds"]
        def stamp(value: float) -> str: return f"{int(value//60):02d}:{value%60:06.3f}"
        self.frame_label.setText(f"{stamp(current)} / {stamp(total)} · frame {frame} / {self.session.frame_count-1}")

    def toggle_play(self) -> None:
        if not self.session: return
        if not self.playing and self.current_frame >= self.session.frame_count - 1: self._request_frame(0)
        self.playing = not self.playing; self.play_button.setText("Pause" if self.playing else "Play")
        self.play_timer.start() if self.playing else self.play_timer.stop()

    def _play_tick(self) -> None:
        if not self.session: return
        # Do not let the playback clock outrun decoding. DecodeThread coalesces
        # random seeks by dropping stale results; continually advancing here
        # while one frame is in flight would make every result stale and leave
        # the display apparently frozen.
        if self.current_frame != self.requested_frame: return
        if self.requested_frame >= self.session.frame_count - 1: self.playing = False; self.play_timer.stop(); self.play_button.setText("Play"); return
        self._request_frame(self.requested_frame + 1)

    def step(self, delta: int) -> None:
        self.playing = False; self.play_timer.stop(); self.play_button.setText("Play"); self._request_frame(self.requested_frame + delta)

    def handle_shortcut(self, command: str) -> None:
        if command == "toggle":
            self.toggle_play()
        elif command == "left":
            self.step(-1)
        elif command == "right":
            self.step(1)
        elif command == "shift_left" and self.session:
            self.step(-max(1, round(self.session.metadata["fps_num"] / self.session.metadata["fps_den"])))
        elif command == "shift_right" and self.session:
            self.step(max(1, round(self.session.metadata["fps_num"] / self.session.metadata["fps_den"])))
        elif command == "home":
            self.step(-self.requested_frame)
        elif command == "end" and self.session:
            self.step(self.session.frame_count - 1 - self.requested_frame)

    def _reload(self) -> None:
        assert self.asset_info; self.layout_doc = self.layouts.load(self.asset_info["media_path"], create=True)["layout"]; self._refresh_layout()
    def _selected_draft_id(self) -> str | None:
        record = self._selected_record()
        return record["region_id"] if record and record["type"] == "draft" else None
    def _apply_layout_snapshot(self, layout: dict[str, Any], selected_id: str | None) -> None:
        if not self.asset_info: return
        self.layout_doc = self.layouts.save(self.asset_info["media_path"], deepcopy(layout))["layout"]
        self.view.selected_id = selected_id
        self._refresh_layout()
    def _record_layout_change(
        self,
        text: str,
        before: dict[str, Any],
        selected_before: str | None,
        selected_after: str | None,
    ) -> None:
        if not self.layout_doc: return
        self.undo_stack.push(LayoutSnapshotCommand(
            self, text, before, self.layout_doc, selected_before, selected_after,
        ))
    def _add_region(self, box: list[int]) -> None:
        if not self.asset_info: return
        before = deepcopy(self.layout_doc); selected_before = self._selected_draft_id()
        result = self.layouts.add(self.asset_info["media_path"], box); self.layout_doc = result["layout"]; self.view.selected_id = result["region"]["region_id"]; self._refresh_layout()
        if before: self._record_layout_change("Create replicate", before, selected_before, result["region"]["region_id"])
    def _move_region(self, region_id: str, box: list[int]) -> None:
        if self.asset_info:
            before = deepcopy(self.layout_doc); selected_before = self._selected_draft_id()
            self.layout_doc = self.layouts.update(self.asset_info["media_path"], region_id, box)["layout"]; self._refresh_layout()
            if before: self._record_layout_change("Move replicate", before, selected_before, region_id)
    def _view_selection(self, region_id: object) -> None:
        for row in range(self.replicate_table.rowCount()):
            record = self.replicate_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if record["region_id"] == region_id: self.replicate_table.selectRow(row); self.replicate_table.setCurrentCell(row, 0); break
        self._update_action_buttons()
    def _table_selection(self, current_row: int, current_column: int, previous_row: int, previous_column: int) -> None:
        record = self._selected_record(); self.view.select(record["region_id"] if record else None); self._update_action_buttons()
    def _focus_selected(self, row: int, column: int) -> None:
        record = self._selected_record()
        if record and record["type"] == "draft": self.view.select(record["region_id"], focus=True); self.status_label.setText("Replicate preview — coordinates remain in the current asset")
    def rename_region(self) -> None:
        record = self._selected_record()
        if not record or record["type"] != "draft" or not self.asset_info: return
        current = next(r for r in self.layout_doc["draft_regions"] if r["region_id"] == record["region_id"]); text, ok = QInputDialog.getText(self, "Rename replicate", "Label", text=current["label"])
        if ok and text.strip() and text.strip() != current["label"]:
            before = deepcopy(self.layout_doc)
            self.layout_doc = self.layouts.rename(self.asset_info["media_path"], current["region_id"], text)["layout"]; self._refresh_layout()
            self._record_layout_change("Rename replicate", before, current["region_id"], current["region_id"])
    def delete_region(self) -> None:
        record = self._selected_record()
        if self.derive_thread is not None: return
        if record and record["type"] == "draft" and self.asset_info and QMessageBox.question(self, "Remove replicate", "Remove this replicate record?") == QMessageBox.StandardButton.Yes:
            before = deepcopy(self.layout_doc)
            self.layout_doc = self.layouts.remove(self.asset_info["media_path"], record["region_id"])["layout"]; self.view.select(None); self._refresh_layout()
            self._record_layout_change("Delete replicate", before, record["region_id"], None)
        elif record and record["type"] == "child" and record["state"] == "Missing" and self.asset_info:
            answer = QMessageBox.question(
                self,
                "Remove missing replicate",
                "Remove this missing replicate from the list?\n\nNo files will be deleted. You will no longer be able to use Locate to reconnect it.",
            )
            if answer == QMessageBox.StandardButton.Yes:
                before = deepcopy(self.layout_doc)
                child = self.layout_doc["created_children"][record["child_index"]]["child"]
                self.layout_doc = self.layouts.remove_child_record(self.asset_info["media_path"], child["asset_id"])["layout"]
                self.view.select(None); self._refresh_layout()
                self._record_layout_change("Remove missing replicate", before, None, None)
    def clear_regions(self) -> None:
        if self.asset_info and QMessageBox.question(self, "Clear drafts", "Remove all draft regions? Created children are not affected.") == QMessageBox.StandardButton.Yes:
            before = deepcopy(self.layout_doc); selected_before = self._selected_draft_id()
            self.layout_doc = self.layouts.clear(self.asset_info["media_path"])["layout"]; self.view.select(None); self._refresh_layout()
            self._record_layout_change("Clear draft replicates", before, selected_before, None)

    def _child_path(self, index: int) -> Path | None:
        return self._lightweight_child_path(index)
    def open_child_index(self, index: int) -> None:
        path = self._child_path(index)
        if path: self.open_asset(str(path))
        else:
            for row in range(self.replicate_table.rowCount()):
                record = self.replicate_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if record["type"] == "child" and record["child_index"] == index: self.replicate_table.selectRow(row); self.replicate_table.setCurrentCell(row, 0); break
            self.locate_child()
    def open_selected_child(self) -> None:
        record = self._selected_record()
        if record and record["type"] == "child": self.open_child_index(record["child_index"])
    def open_child_folder(self, index: int) -> None:
        path = self._child_path(index)
        if not path: return
        folder = path.parent
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            QMessageBox.warning(self, "Could not open folder", f"Could not open this replicate folder:\n{folder}")
    def locate_child(self) -> None:
        record = self._selected_record()
        if not record or record["type"] != "child": return
        path, _ = QFileDialog.getOpenFileName(self, "Locate child asset", "", "Asset sidecar (*.asset.json)")
        if not path: return
        child = self.layout_doc["created_children"][record["child_index"]]["child"]
        try:
            found = self.assets.verify(path, level="quick")["asset"]
            if found["asset_id"] != child["asset_id"] or found["media"]["content_sha256"] != child["content_sha256"]: raise SieveError("ASSET_CONTENT_MISMATCH", "Selected asset is not this created child")
            layout_path = Path(self.asset_info["media_path"]).with_suffix(".replicate-layout.json"); child["location_hints"].insert(0, Path(os.path.relpath(path, layout_path.parent)).as_posix()); self.layouts.save(self.asset_info["media_path"], self.layout_doc); self.open_asset(path)
        except SieveError as exc: QMessageBox.critical(self, "Wrong child", f"{exc.code}: {exc.message}")
    def open_parent(self) -> None:
        active = self.controller.active_asset
        if active and active.parent and active.parent.resolved_sidecar_path:
            self.open_asset(str(active.parent.resolved_sidecar_path))
    def import_template(self) -> None:
        if not self.asset_info: return
        path, _ = QFileDialog.getOpenFileName(self, "Import layout template", "", "JSON (*.json)")
        if path:
            before = deepcopy(self.layout_doc); selected_before = self._selected_draft_id()
            self.layout_doc = self.layouts.import_template(self.asset_info["media_path"], path)["layout"]; self._refresh_layout()
            self._record_layout_change("Import replicate template", before, selected_before, None)
    def export_template(self) -> None:
        if not self.asset_info: return
        path, _ = QFileDialog.getSaveFileName(self, "Export layout template", "replicate-template.json", "JSON (*.json)")
        if path: self.layouts.export_template(self.asset_info["media_path"], path); self.status_label.setText(f"Template exported to {path}")

    def start_derivation(self) -> None:
        if not self.asset_info or not self.layout_doc: return
        candidates = [r for r in self.layout_doc["draft_regions"] if r["state"] in {"draft", "failed", "canceled"}]
        if not candidates: return
        dialog = DeriveDialog(candidates, self.asset_info["media_path"], DerivationService(self.assets, self.layouts))
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.output.text(): return
        self.undo_stack.clear()
        ids = dialog.selected_ids(); service = DerivationService(self.assets, self.layouts); self._derive_parent = self.asset_info["media_path"]; self.derive_thread = DeriveThread(service, self._derive_parent, dialog.output.text(), dialog.profile.currentText(), ids); self._derive_region_ids = ids
        self._set_mutations(False); self.progress.setRange(0, len(ids) * 100); self.progress.setValue(0); self.progress_detail.setText("Preparing encoding plan…"); self.cancel_button.setEnabled(True); self.busy_overlay.show()
        self.layout_doc = self.layouts.set_states(self.asset_info["media_path"], {region_id: ("extracting", None) for region_id in ids})["layout"]; self._refresh_layout()
        self.derive_thread.progress.connect(self._derive_progress); self.derive_thread.finished_result.connect(self._derive_finished); self.derive_thread.failed.connect(self._derive_failed); self.derive_thread.start()
    def _set_mutations(self, enabled: bool) -> None:
        self.import_button.setEnabled(enabled); self._update_action_buttons()
    def _derive_progress(self, record: dict[str, Any]) -> None:
        self.status_label.setText(f"{record['label']}: {record['phase']} — {record['message']}"); fraction = record.get("fraction")
        self.progress_detail.setText(f"{record['label']}: {record['message']}")
        phase = record["phase"]
        if phase in {"planning", "encoding"}: self._set_attempt_state(record["region_id"], "extracting")
        elif phase in {"verifying", "publishing"}: self._set_attempt_state(record["region_id"], "verifying")
        elif phase == "failed":
            error = record.get("error") or {}; state = "canceled" if error.get("code") == "DERIVATION_CANCELLED" else "failed"; self._set_attempt_state(record["region_id"], state, error)
        if fraction is not None and self.layout_doc:
            index = self._derive_region_ids.index(record["region_id"]) if record["region_id"] in self._derive_region_ids else 0; self.progress.setValue(round((index + fraction) * 100))
    def _set_attempt_state(self, region_id: str, state: str, error: dict[str, Any] | None = None) -> None:
        if not self.asset_info or not self._derive_parent: return
        if Path(self.asset_info["media_path"]).resolve() != Path(self._derive_parent).resolve(): return
        layout = self.layouts.load(self._derive_parent)["layout"]
        region = next((r for r in layout["draft_regions"] if r["region_id"] == region_id), None)
        if region is None: return
        self.layout_doc = layout; self._refresh_layout()
    def _derive_finished(self, result: dict[str, Any]) -> None:
        self.status_label.setText(f"Created {result['complete_count']} child replicate(s); {result['failed_count']} failed")
        self._finalize_attempt_states(result); thread = self.derive_thread
        if thread: thread.wait(1000)
        self.derive_thread = None; self._derive_region_ids = []; self._derive_parent = None; self.busy_overlay.hide(); self._set_mutations(True); self._reload()
    def _derive_failed(self, message: str) -> None:
        self.status_label.setText(f"Derivation failed: {message}"); thread = self.derive_thread
        if thread: thread.wait(1000)
        if self._derive_parent:
            loaded = self.layouts.load(self._derive_parent)["layout"]; remaining = {r["region_id"] for r in loaded["draft_regions"]}
            states = {region_id: ("failed", {"code": "ENCODE_FAILED", "message": message}) for region_id in self._derive_region_ids if region_id in remaining}
            if states: self.layouts.set_states(self._derive_parent, states)
        self.derive_thread = None; self._derive_region_ids = []; self._derive_parent = None; self.busy_overlay.hide(); self._set_mutations(True); self._reload()
    def _finalize_attempt_states(self, result: dict[str, Any]) -> None:
        if not self._derive_parent: return
        loaded = self.layouts.load(self._derive_parent)["layout"]; remaining = {r["region_id"] for r in loaded["draft_regions"]}; outcomes = {child["region_id"]: child for child in result.get("children", [])}
        states: dict[str, tuple[str, dict[str, Any] | None]] = {}
        for region_id in self._derive_region_ids:
            if region_id not in remaining: continue
            outcome = outcomes.get(region_id); error = outcome.get("error") if outcome else None
            canceled = result.get("cancelled") or (error and error.get("code") == "DERIVATION_CANCELLED")
            states[region_id] = ("canceled" if canceled else "failed", error or {"code": "DERIVATION_CANCELLED" if canceled else "ENCODE_FAILED", "message": "Extraction did not complete"})
        if states: self.layouts.set_states(self._derive_parent, states)
    def cancel_derivation(self) -> None:
        if self.derive_thread: self.status_label.setText("Cancelling after the active encoder stops…"); self.progress_detail.setText("Cancelling after the active encoder stops…"); self.cancel_button.setEnabled(False); self.derive_thread.cancel()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self.derive_thread: self.derive_thread.cancel(); self.derive_thread.wait()
        self._close_session(); super().closeEvent(event)
