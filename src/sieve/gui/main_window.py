"""Top-level window: menus, tabs, and the wiring between them.

Tabs follow the workflow order from VISION.md. Only Replicate exists so far;
the rest are added as they are built rather than stubbed, so the tab bar is
never a promise the application cannot keep.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QWidget,
)

from sieve.core.types import VideoMetadata
from sieve.gui.document import ReplicateDocument
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preferences_dialog import PreferencesDialog
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.toast import Toast

VIDEO_FILTER = (
    "Video files (*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI *.mkv *.MKV *.m4v *.mpg *.mpeg *.wmv);;"
    "All files (*)"
)

#: Shown once, when the player gives up on decoding every drag position. Says
#: what changed, why, and where to refuse it — in that order, because the user
#: is mid-drag and will read the first clause and nothing else.
COARSE_SCRUB_NOTICE = (
    "Switching to coarse seek to keep scrubbing snappy. You'll land on the "
    "exact frame when you release. If you never want SIEVE to do this, you "
    "can turn it off under Preferences."
)


class MainWindow(QMainWindow):
    """The SIEVE desktop window."""

    def __init__(
        self, preferences: Preferences | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("SIEVE")
        # Both, in this order: `resize` is what the window restores down *to*
        # once maximized, so dropping it would leave the restored size to
        # whatever Qt picks from the layout's size hint. The state is set
        # rather than `showMaximized()` called, because a constructor that
        # puts a window on screen takes that decision away from its caller.
        self.resize(1280, 900)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        # An injected store is what lets a test drive the window without
        # reading or writing the developer's real settings — which now matters,
        # because opening a video writes to it.
        self._preferences = preferences if preferences is not None else Preferences(parent=self)
        self._preferences_dialog: PreferencesDialog | None = None

        self._player = VideoPlayer(self)
        self._document = ReplicateDocument(self)
        self._replicate_tab = ReplicateTab(self._player, self._document, self)

        tabs = QTabWidget()
        tabs.addTab(self._replicate_tab, "Replicate")
        self.setCentralWidget(tabs)

        # Constructed after the central widget so it stacks above it, and
        # parented to the window rather than the tab so it survives a tab
        # change and sits in the window's corner rather than the tab's.
        self._toast = Toast(self)

        self._build_menus()
        self._connect()
        self._player.apply_preferences(self._preferences)
        self.statusBar().showMessage("Open a video to begin  ·  Ctrl+O")

    @property
    def preferences(self) -> Preferences:
        """The application's preference store."""
        return self._preferences

    # ---- menus -----------------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self._open_action = QAction("&Open Video…", self)
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)
        self._open_action.triggered.connect(self.open_video_dialog)
        file_menu.addAction(self._open_action)

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

        # Built by the stack itself: these carry the enabled state and the
        # command text ("Undo Add Replicate 1") without any bookkeeping here.
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
        # Qt moves this to the application menu on platforms that have one,
        # which is why it is safe to put it under Edit unconditionally.
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

        # Period and comma rather than the arrow keys, which the replicate
        # table needs for row navigation — a window shortcut would take them
        # before the table ever saw them.
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

    def _connect(self) -> None:
        self._player.opened.connect(self._on_opened)
        self._player.failed.connect(self._on_failed)
        self._player.scrub_degraded.connect(self._on_scrub_degraded)
        self._replicate_tab.editor_open_changed.connect(self._on_editor_open_changed)
        self._preferences.changed.connect(self._on_preferences_changed)

    # ---- commands --------------------------------------------------------

    @Slot()
    def show_preferences(self) -> None:
        """Open the preferences pane, reusing it if it is already up.

        Modeless and kept alive between openings: the settings in it change
        how the video behaves, so the user needs the window and the pane on
        screen at the same time to judge what they did.
        """
        if self._preferences_dialog is None:
            self._preferences_dialog = PreferencesDialog(self._preferences, self)
        self._preferences_dialog.show()
        self._preferences_dialog.raise_()
        self._preferences_dialog.activateWindow()

    @Slot()
    def open_video_dialog(self) -> None:
        """Prompt for a video file and load it."""
        start_directory = ""
        remembered = self._preferences.last_video
        if remembered is not None and remembered.parent.is_dir():
            start_directory = str(remembered.parent)
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", start_directory, VIDEO_FILTER)
        if path:
            self.open_video(Path(path))

    def restore_last_video(self) -> bool:
        """Reopen the video from the previous session, if it is still there.

        Returns whether anything was opened. A remembered file that has been
        moved or deleted is not an error the user needs told about — they have
        not asked for anything yet — so the window is left in exactly the state
        it would have had with nothing remembered at all, hint included.
        """
        path = self._preferences.last_video
        if path is None or not path.is_file():
            return False
        self.open_video(path)
        return True

    def open_video(self, path: Path) -> None:
        """Load a video by path."""
        self.statusBar().showMessage(f"Opening {path.name}…")
        self._player.open(str(path))

    @Slot()
    def close_video(self) -> None:
        """Unload the current video and its replicates."""
        self._player.close()
        self._document.unbind_source()
        self._replicate_tab.video_closed()
        self._set_video_actions_enabled(False)
        self.setWindowTitle("SIEVE")
        self.statusBar().showMessage("Open a video to begin  ·  Ctrl+O")

    # ---- player feedback -------------------------------------------------

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        # Recorded on success rather than on the open attempt: a path that
        # failed to decode is not one to hand back at the next launch.
        self._preferences.last_video = metadata.path
        self._document.bind_source(metadata.width, metadata.height)
        self._set_video_actions_enabled(True)
        self.setWindowTitle(f"SIEVE — {metadata.path.name}")
        self.statusBar().showMessage(
            f"{metadata.path.name}  ·  {metadata.width}x{metadata.height}  ·  "
            f"{metadata.fps:.2f} fps  ·  {metadata.frame_count:,} frames"
        )

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, "SIEVE", message)

    @Slot()
    def _on_scrub_degraded(self) -> None:
        """Tell the user the drag just started meaning something slightly different."""
        self._toast.show_message(COARSE_SCRUB_NOTICE)

    @Slot()
    def _on_preferences_changed(self) -> None:
        self._player.apply_preferences(self._preferences)

    @Slot(bool)
    def _on_editor_open_changed(self, editing: bool) -> None:
        """Yield the space and delete keys to a cell editor while one is open."""
        has_video = self._player.metadata is not None
        self._play_action.setEnabled(has_video and not editing)
        self._delete_action.setEnabled(not editing)

    def _set_video_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self._close_action,
            self._play_action,
            self._next_frame_action,
            self._previous_frame_action,
            self._start_action,
        ):
            action.setEnabled(enabled)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop the decode thread before the window goes away."""
        self._player.shutdown()
        super().closeEvent(event)
