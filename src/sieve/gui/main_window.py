from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from yaml import YAMLError

from sieve.core.pipeline_model import PROJECT_SUFFIX, Project, project_path_for
from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument, SourceHome
from sieve.gui.executor_adapter import ExecutorAdapter
from sieve.gui.filter_tab import FilterTab
from sieve.gui.history import SnapshotStore, history_directory
from sieve.gui.history_dialog import HistoryDialog
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preferences_dialog import PreferencesDialog
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.resource_probe import (
    MODE_IDLE,
    MODE_PLAYBACK,
    MODE_RENDER,
    MODE_RENDER_FED_PLAYBACK,
    ResourceProbe,
)
from sieve.gui.timeline_bar import TimelineBar
from sieve.gui.toast import Toast
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.preview import PreviewRender

VIDEO_FILTER = (
    "Video files (*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI *.mkv *.MKV *.m4v *.mpg *.mpeg *.wmv);;"
    "All files (*)"
)

PROJECT_FILTER = f"SIEVE projects (*{PROJECT_SUFFIX});;All files (*)"


COARSE_SCRUB_NOTICE = (
    "Switching to coarse seek to keep scrubbing snappy. You'll land on the "
    "exact frame when you release. If you never want SIEVE to do this, you "
    "can turn it off under Preferences."
)


HISTORY_FAILED = "History is not being kept: {error}"


RESTORED = "Rolled back to {text}  ·  Ctrl+Z to change your mind"


class MainWindow(QMainWindow):
    def __init__(
        self, preferences: Preferences | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SIEVE")
        self.resize(1280, 900)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        self._preferences = (
            preferences if preferences is not None else Preferences(parent=self)
        )
        self._preferences_dialog: PreferencesDialog | None = None
        self._player = VideoPlayer(self)
        self._document = ReplicateDocument(self)
        self._replicate_tab = ReplicateTab(self._player, self._document, self)
        self._timeline = TimelineBar(self._player, self._document, self)
        self._preview = PreviewRunner(self)
        self._player.set_render_feed(self._preview.ring)
        self._metrics = ExecutorAdapter(parent=self)
        self._filter_tab = FilterTab(
            self._player,
            self._document,
            self._preview,
            self,
            preferences=self._preferences,
        )
        self._project: Project | None = None
        self._project_path: Path | None = None
        self._pending_project: tuple[Project, Path] | None = None
        self._history: SnapshotStore | None = None
        self._history_timer = QTimer(self)
        self._history_timer.setInterval(0)
        self._history_timer.setSingleShot(True)
        self._history_timer.timeout.connect(self._write_snapshot)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._replicate_tab, "Replicate")
        self._tabs.addTab(self._filter_tab, "Filter")
        central = QWidget()
        stack = QVBoxLayout(central)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(0)
        stack.addWidget(self._tabs, 1)
        stack.addWidget(self._timeline)
        self.setCentralWidget(central)
        self._toast = Toast(self)
        self._build_menus()
        self._connect()
        self._player.apply_preferences(self._preferences)
        self.statusBar().showMessage("Open a video to begin  ·  Ctrl+O")

    @property
    def preferences(self) -> Preferences:
        return self._preferences

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self._open_action = QAction("&Open Video…", self)
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self.open_video_dialog)
        file_menu.addAction(self._open_action)
        self._open_project_action = QAction("Open &Project…", self)
        self._open_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        self._open_project_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(self._open_project_action)
        file_menu.addSeparator()
        self._save_action = QAction("&Save Project", self)
        self._save_action.setShortcut(QKeySequence.StandardKey.Save)
        self._save_action.setEnabled(False)
        self._save_action.triggered.connect(self.save_project)
        file_menu.addAction(self._save_action)
        self._save_as_action = QAction("Save Project &As…", self)
        self._save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self._save_as_action.setEnabled(False)
        self._save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(self._save_as_action)
        self._history_action = QAction("&History…", self)
        self._history_action.setEnabled(False)
        self._history_action.triggered.connect(self.show_history)
        file_menu.addAction(self._history_action)
        file_menu.addSeparator()
        self._close_action = QAction("&Close Video", self)
        self._close_action.setShortcut(QKeySequence.StandardKey.Close)
        self._close_action.setEnabled(False)
        self._close_action.triggered.connect(self.close_video)
        file_menu.addAction(self._close_action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        edit_menu = self.menuBar().addMenu("&Edit")
        stack: QUndoStack = self._document.undo_stack
        self._undo_action = stack.createUndoAction(self, "&Undo")
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(self._undo_action)
        self._redo_action = stack.createRedoAction(self, "&Redo")
        self._redo_action.setShortcuts(
            [QKeySequence(QKeySequence.StandardKey.Redo), QKeySequence("Ctrl+Y")]
        )
        edit_menu.addAction(self._redo_action)
        edit_menu.addSeparator()
        self._delete_action = QAction("&Delete Replicate", self)
        self._delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self._delete_action.triggered.connect(self._replicate_tab.delete_selected)
        edit_menu.addAction(self._delete_action)
        edit_menu.addSeparator()
        self._preferences_action = QAction("&Preferences…", self)
        self._preferences_action.setShortcut(QKeySequence.StandardKey.Preferences)
        self._preferences_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        self._preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(self._preferences_action)
        playback_menu = self.menuBar().addMenu("&Playback")
        self._play_action = QAction("&Play / Pause", self)
        self._play_action.setShortcut(QKeySequence(" "))
        self._play_action.setEnabled(False)
        self._play_action.triggered.connect(self._player.toggle_play)
        playback_menu.addAction(self._play_action)
        playback_menu.addSeparator()
        self._next_frame_action = QAction("&Next Frame", self)
        self._next_frame_action.setShortcut(QKeySequence("."))
        self._next_frame_action.setEnabled(False)
        self._next_frame_action.triggered.connect(lambda: self._player.step(1))
        playback_menu.addAction(self._next_frame_action)
        self._previous_frame_action = QAction("&Previous Frame", self)
        self._previous_frame_action.setShortcut(QKeySequence(","))
        self._previous_frame_action.setEnabled(False)
        self._previous_frame_action.triggered.connect(lambda: self._player.step(-1))
        playback_menu.addAction(self._previous_frame_action)
        self._start_action = QAction("Go to &Start", self)
        self._start_action.setShortcut(QKeySequence.StandardKey.MoveToStartOfDocument)
        self._start_action.setEnabled(False)
        self._start_action.triggered.connect(lambda: self._player.seek(0))
        playback_menu.addAction(self._start_action)
        playback_menu.addSeparator()
        self._mark_in_action = QAction("Mark Clip &In", self)
        self._mark_in_action.setShortcut(QKeySequence("I"))
        self._mark_in_action.setEnabled(False)
        self._mark_in_action.triggered.connect(self.move_window_to_playhead)
        playback_menu.addAction(self._mark_in_action)
        self._mark_out_action = QAction("Mark Clip &Out", self)
        self._mark_out_action.setShortcut(QKeySequence("O"))
        self._mark_out_action.setEnabled(False)
        self._mark_out_action.triggered.connect(self.end_window_at_playhead)
        playback_menu.addAction(self._mark_out_action)
        self._clear_clip_action = QAction("&Clear Clip", self)
        self._clear_clip_action.setEnabled(False)
        self._clear_clip_action.triggered.connect(self._document.clear_clip)
        playback_menu.addAction(self._clear_clip_action)

    def _connect(self) -> None:
        self._player.opened.connect(self._on_opened)
        self._player.failed.connect(self._on_failed)
        self._player.scrub_degraded.connect(self._on_scrub_degraded)
        self._replicate_tab.editing_changed.connect(self._on_editing_changed)
        self._replicate_tab.replicate_accepted.connect(self._on_replicate_accepted)
        self._preferences.changed.connect(self._on_preferences_changed)
        self._document.clip_changed.connect(self._on_clip_changed)
        self._document.crops_changed.connect(self._on_crops_changed)
        self._document.edit_refused.connect(self._toast.show_message)
        self._preview.open_failed.connect(self._on_preview_unavailable)
        self._preview.render_finished.connect(self._on_render_finished)
        self._preview.render_failed.connect(self._on_render_failed)
        self._preview.window_render_changed.connect(self._player.set_render_filling)
        self._filter_tab.status_message.connect(self.statusBar().showMessage)
        self._metrics.sample.connect(self._filter_tab.hud.show_sample)
        self._probe = ResourceProbe(
            meters={
                "player": self._player.decode_meter,
                "preview": self._preview.prefetch_meter,
                "detector": self._filter_tab.detector_meter,
            },
            mode=self._session_mode,
            parent=self,
        )
        self._probe.sample.connect(self._filter_tab.hud.show_resources)
        self._document.undo_stack.cleanChanged.connect(self._on_clean_changed)
        self._document.undo_stack.indexChanged.connect(self._on_undo_index_changed)

    @Slot()
    def move_window_to_playhead(self) -> None:
        self._document.move_window_to(self._player.current_index)

    @Slot()
    def end_window_at_playhead(self) -> None:
        self._document.end_window_at(self._player.current_index)

    @Slot(int)
    def _on_replicate_accepted(self, row: int) -> None:
        self._tabs.setCurrentWidget(self._filter_tab)
        self.statusBar().showMessage(f"Tuning {self._document.at(row).name}")

    @Slot()
    def show_preferences(self) -> None:
        if self._preferences_dialog is None:
            self._preferences_dialog = PreferencesDialog(self._preferences, self)
        self._preferences_dialog.show()
        self._preferences_dialog.raise_()
        self._preferences_dialog.activateWindow()

    @Slot()
    def open_video_dialog(self) -> None:
        start_directory = ""
        remembered = self._preferences.last_video
        if remembered is not None and remembered.parent.is_dir():
            start_directory = str(remembered.parent)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", start_directory, VIDEO_FILTER
        )
        if path:
            self.open_video(Path(path))

    @Slot()
    def open_project_dialog(self) -> None:
        start = self._project_path.parent if self._project_path is not None else None
        if start is None:
            remembered = self._preferences.last_video
            start = remembered.parent if remembered is not None else None
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(start) if start is not None else "",
            PROJECT_FILTER,
        )
        if path:
            self.open_project(Path(path))

    def open_project(self, path: Path) -> None:
        project = self._read_project(path)
        if project is None:
            return
        video = project.source_path(path)
        if not video.is_file():
            self._warn(f"{path.name} names a video that is not there:\n{video}")
            return
        metadata = self._player.metadata
        if metadata is not None and metadata.path.resolve() == video:
            self._adopt_project(project, path)
            return
        self._pending_project = (project, path)
        self.open_video(video)

    @Slot()
    def save_project(self) -> bool:
        if self._project_path is None:
            return self.save_project_as()
        return self._write_project(self._project_path)

    @Slot()
    def save_project_as(self) -> bool:
        metadata = self._player.metadata
        if metadata is None:
            return False
        default = self._project_path or project_path_for(metadata.path)
        chosen, _ = QFileDialog.getSaveFileName(
            self, "Save Project", str(default), PROJECT_FILTER
        )
        if not chosen:
            return False
        return self._write_project(_with_project_suffix(Path(chosen)))

    def _read_project(self, path: Path) -> Project | None:
        try:
            return Project.load(path)
        except (OSError, YAMLError, ValidationError) as error:
            self._warn(f"Cannot open {path.name}:\n{error}")
            return None

    def _adopt_project(self, project: Project, path: Path) -> None:
        self._document.load_project(project)
        self._project = project
        self._project_path = path
        self._declare_source_home()
        self._preview.set_crops(project.crops, path.parent)
        self._document.undo_stack.setClean()
        self._update_title()
        self._retarget_history()

    def _write_project(self, path: Path) -> bool:
        metadata = self._player.metadata
        if metadata is None:
            return False
        base = self._project
        home = self._document.source_home
        if base is None:
            base = Project.for_video(
                metadata.path, home.project_dir if home else path.parent
            )
        try:
            project = self._document.apply_to(base)
            if home is not None and home.project_dir != path.parent:
                project = project.relocated(home.project_dir, path.parent)
            project.save(path)
        except (OSError, ValidationError) as error:
            self._warn(f"Cannot save {path.name}:\n{error}")
            return False
        self._project = project
        self._project_path = path
        self._declare_source_home()
        self._document.set_crops(project.crops)
        self._preview.set_crops(project.crops, path.parent)
        self._document.undo_stack.setClean()
        self._update_title()
        self._retarget_history()
        self.statusBar().showMessage(f"Saved {path.name}")
        return True

    def _declare_source_home(self) -> None:
        metadata = self._player.metadata
        if metadata is None:
            self._document.set_source_home(None)
            return
        anchor = self._project_path or project_path_for(metadata.path)
        try:
            identity = source_identity(metadata.path)
        except OSError:
            self._document.set_source_home(None)
            return
        self._document.set_source_home(
            SourceHome(
                video=metadata.path, project_dir=anchor.parent, identity=identity
            )
        )

    @Slot()
    def _on_crops_changed(self) -> None:
        home = self._document.source_home
        if home is None:
            return
        self._preview.set_crops(self._document.crops, home.project_dir)
        self._update_title()

    def _open_neighbour_project(self, video: Path) -> None:
        path = project_path_for(video)
        if not path.is_file():
            return
        self.open_project(path)
        if self._project_path == path:
            self.statusBar().showMessage(f"Restored {path.name}  ·  {path.parent}")

    def _retarget_history(self) -> None:
        metadata = self._player.metadata
        if metadata is None:
            self._history = None
            return
        anchor = self._project_path or project_path_for(metadata.path)
        directory = history_directory(anchor)
        if self._history is not None and self._history.directory == directory:
            return
        self._history = SnapshotStore(directory)

    @Slot(int)
    def _on_undo_index_changed(self, index: int) -> None:
        del index
        if self._history is not None and self._document.undo_stack.count() > 0:
            self._history_timer.start()

    @Slot()
    def _write_snapshot(self) -> None:
        store = self._history
        metadata = self._player.metadata
        if store is None or metadata is None:
            return
        stack = self._document.undo_stack
        if stack.count() == 0:
            return
        base = self._project
        if base is None or self._project_path is None:
            base = Project.for_video(metadata.path, store.directory)
        else:
            base = base.relocated(self._project_path.parent, store.directory)
        try:
            store.record(self._document.apply_to(base), stack.text(stack.index() - 1))
        except (OSError, ValidationError) as error:
            self._history = None
            self.statusBar().showMessage(HISTORY_FAILED.format(error=error))

    @Slot()
    def show_history(self) -> None:
        store = self._history
        if store is None:
            self.statusBar().showMessage(
                HISTORY_FAILED.format(error="no project is open")
            )
            return
        dialog = HistoryDialog(store.entries(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        snapshot = dialog.chosen()
        if snapshot is None:
            return
        project = self._read_project(snapshot.path)
        if project is None:
            return
        self._document.restore(
            self._document.state_from_project(project), snapshot.text
        )
        self.statusBar().showMessage(RESTORED.format(text=snapshot.text))

    def _update_title(self) -> None:
        metadata = self._player.metadata
        if metadata is None:
            self.setWindowTitle("SIEVE")
            return
        subject = metadata.path.name
        if self._project_path is not None:
            subject = f"{subject}  ·  {self._project_path.name}"
        self.setWindowTitle(f"SIEVE — {subject}[*]")

    def _warn(self, message: str) -> None:
        self.statusBar().showMessage(message.replace("\n", "  "))
        QMessageBox.warning(self, "SIEVE", message)

    def restore_last_video(self) -> bool:
        path = self._preferences.last_video
        if path is None or not path.is_file():
            return False
        self.open_video(path)
        return True

    def open_video(self, path: Path) -> None:
        self.statusBar().showMessage(f"Opening {path.name}…")
        self._player.open(str(path))

    @Slot()
    def close_video(self) -> None:
        if self._history_timer.isActive():
            self._history_timer.stop()
            self._write_snapshot()
        self._player.close()
        self._preview.close()
        self._document.unbind_source()
        self._document.set_source_home(None)
        self._replicate_tab.video_closed()
        self._timeline.video_closed()
        self._set_video_actions_enabled(False)
        self._project = None
        self._project_path = None
        self._pending_project = None
        self._history_timer.stop()
        self._history = None
        self._update_title()
        self.statusBar().showMessage("Open a video to begin  ·  Ctrl+O")

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._preferences.last_video = metadata.path
        self._preview.open(metadata.path)
        self._document.bind_source(
            metadata.width, metadata.height, metadata.frame_count, metadata.fps
        )
        self._declare_source_home()
        self._set_video_actions_enabled(True)
        self.statusBar().showMessage(
            f"{metadata.path.name}  ·  {metadata.width}x{metadata.height}  ·  "
            f"{metadata.fps:.2f} fps  ·  {metadata.frame_count:,} frames"
        )
        pending = self._pending_project
        self._pending_project = None
        if pending is not None:
            self._adopt_project(*pending)
        else:
            self._project = None
            self._project_path = None
            self._update_title()
            self._open_neighbour_project(metadata.path)
        self._retarget_history()
        if self._play_action.isEnabled():
            self._player.play()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._pending_project = None
        self._warn(message)

    @Slot(object)
    def _on_render_finished(self, render: PreviewRender) -> None:
        self.statusBar().showMessage(
            f"Graph: {render.frames} frames {render.span.start}:{render.span.end}  ·  "
            f"{render.computed} computed, {render.from_cache} cached "
            f"({render.reuse:.0%} reuse)"
        )

    @Slot(str)
    def _on_render_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Graph cannot run: {message}")

    @Slot(str)
    def _on_preview_unavailable(self, message: str) -> None:
        self.statusBar().showMessage(f"No preview: {message}")

    @Slot()
    def _on_scrub_degraded(self) -> None:
        self._toast.show_message(COARSE_SCRUB_NOTICE)

    @Slot()
    def _on_preferences_changed(self) -> None:
        self._player.apply_preferences(self._preferences)

    @Slot()
    def _on_clip_changed(self) -> None:
        self._clear_clip_action.setEnabled(self._document.clip is not None)

    @Slot(bool)
    def _on_clean_changed(self, clean: bool) -> None:
        self.setWindowModified(not clean)

    @Slot(bool)
    def _on_editing_changed(self, editing: bool) -> None:
        has_video = self._player.metadata is not None
        self._play_action.setEnabled(has_video and not editing)
        self._delete_action.setEnabled(not editing)
        self._mark_in_action.setEnabled(has_video and not editing)
        self._mark_out_action.setEnabled(has_video and not editing)

    def _set_video_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self._save_action,
            self._save_as_action,
            self._history_action,
            self._close_action,
            self._play_action,
            self._next_frame_action,
            self._previous_frame_action,
            self._start_action,
            self._mark_in_action,
            self._mark_out_action,
        ):
            action.setEnabled(enabled)

    def _session_mode(self) -> str:
        if self._player.is_playing:
            if self._player.render_fed and self._preview.window_render_active:
                return MODE_RENDER_FED_PLAYBACK
            return MODE_PLAYBACK
        if self._preview.window_render_active:
            return MODE_RENDER
        return MODE_IDLE

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._history_timer.isActive():
            self._history_timer.stop()
            self._write_snapshot()
        self._probe.shutdown()
        self._player.shutdown()
        self._metrics.close()
        self._preview.shutdown()
        self._filter_tab.shutdown()
        super().closeEvent(event)


def _with_project_suffix(path: Path) -> Path:
    if path.name.endswith(PROJECT_SUFFIX):
        return path
    return path.with_name(path.stem + PROJECT_SUFFIX)
