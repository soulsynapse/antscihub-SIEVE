from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QFileDialog,
                             QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QMainWindow, QMessageBox, QPushButton, QTabWidget,
                             QVBoxLayout, QWidget, QWidgetAction)

from antscihub_sieve.application.active_asset import ActiveAsset, ActiveAssetController
from antscihub_sieve.errors import SieveError
from antscihub_sieve.gui.isolate_tab import IsolateTab
from antscihub_sieve.gui.replicate_workspace import ReplicateWorkspace


def default_settings() -> QSettings:
    return QSettings("Ant Science Hub", "SIEVE")


class MainWindow(QMainWindow):
    RECENT_FILES_KEY = "file/recent"
    MAX_RECENT_FILES = 30
    VISIBLE_RECENT_FILES = 8

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.setWindowTitle("SIEVE")
        self.settings = settings or default_settings()
        self.controller = ActiveAssetController()

        central = QWidget()
        root = QVBoxLayout(central)

        parent_row = QHBoxLayout()
        self.parent_label = QLabel("Parent: —")
        self.open_parent_button = QPushButton("Open parent")
        self.locate_parent_button = QPushButton("Locate parent…")
        parent_row.addWidget(self.parent_label)
        parent_row.addWidget(self.open_parent_button)
        parent_row.addWidget(self.locate_parent_button)
        parent_row.addStretch()
        root.addLayout(parent_row)

        self.tabs = QTabWidget()
        self.replicates_tab = ReplicateWorkspace(self.controller)
        self.isolate_tab = IsolateTab(self.controller)
        self.tabs.addTab(self.replicates_tab, "Replicates")
        self.tabs.addTab(self.isolate_tab, "Isolate")
        root.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self._build_workflow_shortcuts()

        self.menuBar().setStyleSheet("""
            QMenuBar { padding: 3px 6px; spacing: 3px; }
            QMenuBar::item { padding: 5px 10px; border-radius: 4px; }
            QMenuBar::item:selected { background: palette(midlight); }
            QMenu { padding: 4px; }
            QMenu::item { padding: 5px 28px 5px 10px; border-radius: 4px; }
            QMenu::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
            QMenu::item:disabled { color: palette(mid); }
            QMenu::separator {
                height: 1px;
                background: palette(mid);
                margin: 4px 7px;
            }
        """)

        self.file_menu = self.menuBar().addMenu("&File")
        self.open_action = QAction("&Open…", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setStatusTip("Open a video or asset")
        self.open_action.triggered.connect(self.choose_open)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addSeparator()

        self.open_last_action = QAction("Open &Last", self)
        self.open_last_action.triggered.connect(self.open_last)
        self.file_menu.addAction(self.open_last_action)

        self.recent_menu = self.file_menu.addMenu("Open &Recent")
        self.recent_list = QListWidget()
        self.recent_list.setAccessibleName("Recent files")
        self.recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.recent_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_list.setMinimumWidth(480)
        self.recent_list.setStyleSheet("""
            QListWidget { border: 0; padding: 1px; }
            QListWidget::item { padding: 3px 8px; border-radius: 4px; }
            QListWidget::item:selected {
                background: palette(highlight);
                color: palette(highlighted-text);
            }
        """)
        self.recent_list.itemClicked.connect(self._recent_item_clicked)
        self.recent_widget_action = QWidgetAction(self.recent_menu)
        self.recent_widget_action.setDefaultWidget(self.recent_list)
        self.recent_menu.addAction(self.recent_widget_action)
        self.recent_menu.addSeparator()
        self.clear_recent_action = QAction("&Clear Recent Files", self)
        self.clear_recent_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(self.clear_recent_action)
        self._refresh_recent_menu()

        edit_menu = self.menuBar().addMenu("&Edit")
        self.undo_action = self.replicates_tab.undo_stack.createUndoAction(self, "&Undo")
        self.redo_action = self.replicates_tab.undo_stack.createRedoAction(self, "&Redo")
        self.undo_action.setShortcuts(QKeySequence.StandardKey.Undo)
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)

        self.open_parent_button.clicked.connect(self.open_parent)
        self.locate_parent_button.clicked.connect(self.locate_parent)
        self.controller.active_asset_changed.connect(self._active_asset_changed)
        self._active_asset_changed(None)
        self.resize(1280, 780)

    def _build_workflow_shortcuts(self) -> None:
        sequences = {
            "toggle": QKeySequence(Qt.Key.Key_Space),
            "left": QKeySequence(Qt.Key.Key_Left),
            "right": QKeySequence(Qt.Key.Key_Right),
            "shift_left": QKeySequence("Shift+Left"),
            "shift_right": QKeySequence("Shift+Right"),
            "home": QKeySequence(Qt.Key.Key_Home),
            "end": QKeySequence(Qt.Key.Key_End),
        }
        self.workflow_shortcuts: dict[str, QShortcut] = {}
        for command, sequence in sequences.items():
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(
                lambda command=command: self._dispatch_workflow_shortcut(command)
            )
            self.workflow_shortcuts[command] = shortcut
        self.replicates_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        self.isolate_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        self.replicates_shortcut.activated.connect(
            lambda: self.tabs.setCurrentWidget(self.replicates_tab)
        )
        self.isolate_shortcut.activated.connect(
            lambda: self.tabs.setCurrentWidget(self.isolate_tab)
        )

    def _dispatch_workflow_shortcut(self, command: str) -> None:
        if isinstance(self.focusWidget(), QAbstractSpinBox):
            return
        active_tab = self.tabs.currentWidget()
        handler = getattr(active_tab, "handle_shortcut", None)
        if handler is not None:
            handler(command)

    def choose_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open video or asset", "",
            "Videos and assets (*.asset.json *.mp4 *.MP4 *.mkv *.avi *.mov);;All files (*)",
        )
        if path:
            self.open_asset(path)

    def open_asset(self, reference: str | Path) -> None:
        try:
            self.controller.open_asset(reference)
        except SieveError as exc:
            QMessageBox.critical(self, "Could not open asset", f"{exc.code}: {exc.message}")

    @staticmethod
    def _display_path(reference: str | Path) -> str:
        return "/".join(Path(reference).parts[-3:])

    def _recent_files(self) -> list[str]:
        stored = self.settings.value(self.RECENT_FILES_KEY, [])
        if isinstance(stored, str):
            stored = [stored]
        return [str(path) for path in stored if str(path).strip()]

    def _remember_recent(self, reference: str | Path) -> None:
        resolved = str(Path(reference).expanduser().resolve())
        normalized = os.path.normcase(resolved)
        recents = [
            path for path in self._recent_files()
            if os.path.normcase(str(Path(path).expanduser().resolve())) != normalized
        ]
        self.settings.setValue(self.RECENT_FILES_KEY, [resolved, *recents][:self.MAX_RECENT_FILES])
        self.settings.sync()
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        recents = self._recent_files()
        self.recent_list.clear()
        if recents:
            for path in recents:
                item = QListWidgetItem(self._display_path(path))
                item.setSizeHint(QSize(0, 26))
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                self.recent_list.addItem(item)
        else:
            item = QListWidgetItem("No recent files")
            item.setSizeHint(QSize(0, 26))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent_list.addItem(item)

        visible_rows = min(max(1, self.recent_list.count()), self.VISIBLE_RECENT_FILES)
        self.recent_list.setFixedHeight(
            visible_rows * 26 + self.recent_list.frameWidth() * 2 + 2
        )
        self.open_last_action.setEnabled(bool(recents))
        self.open_last_action.setText(
            f"Open &Last — {self._display_path(recents[0])}" if recents else "Open &Last — No recent file"
        )
        self.open_last_action.setToolTip(recents[0] if recents else "")
        self.clear_recent_action.setEnabled(bool(recents))

    def _open_recent_path(self, path: str) -> None:
        if not Path(path).exists():
            QMessageBox.warning(self, "Recent file not found", f"This recent file no longer exists:\n{path}")
            remaining = [item for item in self._recent_files() if os.path.normcase(item) != os.path.normcase(path)]
            self.settings.setValue(self.RECENT_FILES_KEY, remaining)
            self.settings.sync()
            self._refresh_recent_menu()
            return
        self.open_asset(path)

    def _recent_item_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        self.recent_menu.close()
        self.file_menu.close()
        self._open_recent_path(str(path))

    def open_last(self) -> None:
        recents = self._recent_files()
        if recents:
            self._open_recent_path(recents[0])

    def clear_recent_files(self) -> None:
        self.settings.remove(self.RECENT_FILES_KEY)
        self.settings.sync()
        self._refresh_recent_menu()

    def _active_asset_changed(self, asset: ActiveAsset | None) -> None:
        if asset is None:
            self.setWindowTitle("SIEVE")
            self.parent_label.setText("Parent: —")
            self.open_parent_button.setEnabled(False)
            self.locate_parent_button.setEnabled(False)
            return
        path = Path(asset.video_path)
        self._remember_recent(path)
        self.setWindowTitle(
            f"SIEVE - {self._display_path(path)} · "
            f"{asset.width}×{asset.height} · {asset.fps:.3f} fps · "
            f"{asset.duration_seconds:.3f}s"
        )
        if asset.parent is None:
            self.parent_label.setText("Parent: none recorded")
            self.open_parent_button.setEnabled(False)
            self.locate_parent_button.setEnabled(False)
        else:
            self.parent_label.setText(f"Parent: {asset.parent.label} · {asset.parent.status}")
            self.open_parent_button.setEnabled(asset.parent.resolved_sidecar_path is not None)
            self.locate_parent_button.setEnabled(True)

    def open_parent(self) -> None:
        active = self.controller.active_asset
        if active and active.parent and active.parent.resolved_sidecar_path:
            self.open_asset(active.parent.resolved_sidecar_path)

    def locate_parent(self) -> None:
        active = self.controller.active_asset
        if not active or not active.parent:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Locate parent asset", "", "Asset sidecar (*.asset.json)")
        if not path:
            return
        try:
            self.controller.locate_parent(path)
        except SieveError as exc:
            QMessageBox.critical(self, "Wrong parent", f"{exc.code}: {exc.message}")

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.isolate_tab.shutdown()
        self.replicates_tab.close()
        super().closeEvent(event)
