"""Top-level window: menus, tabs, the timeline, and the wiring between them.

Tabs follow the workflow order from VISION.md. Replicate and Filter exist;
the rest are added as they are built rather than stubbed, so the tab bar is
never a promise the application cannot keep.

The timeline is *below* the tab widget and outside it, which is the point of it:
it spans the whole asset and says the same thing whichever tab is showing, so
"where am I, and what span am I working on" has one answer instead of one per
tab. That is also why the central widget is a container rather than the tabs
themselves — the tabs are a page, and the timeline is the window's floor.

The window is also where a project becomes a file. It holds the two things the
document deliberately does not — which file the document was read from, and the
parts of the artifact the GUI cannot edit (`source`, `checkpoints`, `outputs`) —
because both are answers about *this session*, and a document that carried them
would be back to keeping GUI state in the pipeline artifact.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QUndoStack
from PySide6.QtWidgets import (
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
from sieve.gui.document import ReplicateDocument
from sieve.gui.executor_adapter import ExecutorAdapter
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer
from sieve.gui.preferences import Preferences
from sieve.gui.preferences_dialog import PreferencesDialog
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.timeline_bar import TimelineBar
from sieve.gui.toast import Toast
from sieve.pipeline.preview import PreviewRender

VIDEO_FILTER = (
    "Video files (*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI *.mkv *.MKV *.m4v *.mpg *.mpeg *.wmv);;"
    "All files (*)"
)

PROJECT_FILTER = f"SIEVE projects (*{PROJECT_SUFFIX});;All files (*)"

#: Asked before anything that discards the document. Names the file rather than
#: the concept where there is one, because "this project" is ambiguous the
#: moment a user has two open in two windows.
UNSAVED_PROMPT = "There are unsaved changes to {name}."

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
        self._timeline = TimelineBar(self._player, self._document, self)

        # The graph side of the window. The filter tab below is now what draws
        # the runner — it submits its live chain on open, window moves, and
        # every knob edit — and the whole-render summary still reaches the
        # user as one status line here.
        self._preview = PreviewRunner(self)
        self._metrics = ExecutorAdapter(parent=self)
        self._filter_tab = FilterTab(
            self._player, self._document, self._preview, self, preferences=self._preferences
        )

        # The project as last read or written, and where from. `_project`
        # carries the fields the document does not edit, so a save can put them
        # back rather than dropping them; `None` means the video was opened on
        # its own and no file has been chosen yet.
        self._project: Project | None = None
        self._project_path: Path | None = None
        # A project read from disk but not yet applied, because the video it
        # names is still opening. `open` is asynchronous and `bind_source`
        # clears the document when it lands, so there is no way to populate
        # first — the project has to wait for the clear it would otherwise be
        # erased by.
        self._pending_project: tuple[Project, Path] | None = None

        # Kept as an attribute because accepting a replicate navigates: the
        # click on a box in the replicate tab lands the user on the filter tab,
        # and a tab widget held only by a local variable can be told nothing.
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

        # The start of the *window*, not of the asset. Every position the
        # transport can reach is inside the window now, so "go to start" has
        # only one meaning it could still have — and `seek` clamps it there
        # regardless of what is passed.
        self._start_action = QAction("Go to &Start", self)
        self._start_action.setShortcut(QKeySequence.StandardKey.MoveToStartOfDocument)
        self._start_action.setEnabled(False)
        self._start_action.triggered.connect(lambda: self._player.seek(0))
        playback_menu.addAction(self._start_action)

        playback_menu.addSeparator()

        # I and O, which is what every editor binds them to. Bare letters are
        # safe here for the same reason period and comma are: they are window
        # shortcuts, and `_on_editing_changed` hands them back the moment a
        # table cell is being typed into.
        #
        # What they mean has changed with the model behind them: I *moves* the
        # window here keeping its length, and O sets where it ends. The labels
        # keep saying in and out because that is the gesture every editor has
        # taught the user, and the length being held is the surprise that stops
        # being one after the first press.
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

        # The filter tab owns render submission — it connects itself to the
        # runner's `opened` and the document's window — so what remains here
        # is reporting: the whole-render summary, the two failure lines, and
        # the tab's own narration.
        self._preview.open_failed.connect(self._on_preview_unavailable)
        self._preview.render_finished.connect(self._on_render_finished)
        self._preview.render_failed.connect(self._on_render_failed)
        self._filter_tab.status_message.connect(self.statusBar().showMessage)

        # The bus's whole-render verdicts reach the HUD here rather than in
        # the tab, because the adapter is the window's — the tab keeps not
        # knowing that the bus has a Qt side at all.
        self._metrics.sample.connect(self._filter_tab.hud.show_sample)

        # The stack is the dirty flag. Every user edit is a command on it by
        # construction (see `document.py`), so there is no second place a change
        # can come from and no bookkeeping to keep in step — which is also why
        # `load_project` and a save both end by declaring it clean.
        self._document.undo_stack.cleanChanged.connect(self._on_clean_changed)

    # ---- commands --------------------------------------------------------

    @Slot()
    def move_window_to_playhead(self) -> None:
        """Put the working window's start at the frame on screen.

        Here rather than on the timeline bar because the playhead belongs to the
        player and the window belongs to the document, and the bar is a view of
        both. A keystroke that needs one of each is the window's to route.
        """
        self._document.move_window_to(self._player.current_index)

    @Slot()
    def end_window_at_playhead(self) -> None:
        """End the working window after the frame on screen, including it."""
        self._document.end_window_at(self._player.current_index)

    @Slot(int)
    def _on_replicate_accepted(self, row: int) -> None:
        """Accepting a replicate is a submit and a change of tab, not a job.

        The selection has already reached the document — the filter tab's
        re-render is on its way through the runner — so all that is left is
        the navigation the vision's sentence ends with. See
        `docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md` for why
        there is no progress bar here.
        """
        self._tabs.setCurrentWidget(self._filter_tab)
        self.statusBar().showMessage(f"Tuning {self._document.at(row).name}")

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
        if not self.confirm_discard():
            return
        start_directory = ""
        remembered = self._preferences.last_video
        if remembered is not None and remembered.parent.is_dir():
            start_directory = str(remembered.parent)
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", start_directory, VIDEO_FILTER)
        if path:
            self.open_video(Path(path))

    @Slot()
    def open_project_dialog(self) -> None:
        """Prompt for a project file and load it, video and all."""
        if not self.confirm_discard():
            return
        start = self._project_path.parent if self._project_path is not None else None
        if start is None:
            remembered = self._preferences.last_video
            start = remembered.parent if remembered is not None else None
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", str(start) if start is not None else "", PROJECT_FILTER
        )
        if path:
            self.open_project(Path(path))

    def open_project(self, path: Path) -> None:
        """Read the project at `path` and put the application in its state.

        The video comes first and the document is populated afterwards, which is
        forced rather than chosen: `bind_source` clears replicates, clip, and
        graph, so anything written before the source landed would be erased by
        the source landing. `_pending_project` is what carries the document
        across that gap.

        A project whose video is already the one on screen skips the reopen
        entirely — this is the path the neighbour offer below takes, and
        re-decoding a file that is already open to arrive at the same frame is
        several seconds of nothing.
        """
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
        """Write to the file this project came from, choosing one if there is none.

        Returns whether anything was written — `confirm_discard` needs the
        answer, because a Save the user backed out of at the file dialog must
        not be treated as consent to discard.
        """
        if self._project_path is None:
            return self.save_project_as()
        return self._write_project(self._project_path)

    @Slot()
    def save_project_as(self) -> bool:
        """Prompt for a location and write there, adopting it as the project's home."""
        metadata = self._player.metadata
        if metadata is None:
            return False
        default = self._project_path or project_path_for(metadata.path)
        chosen, _ = QFileDialog.getSaveFileName(self, "Save Project", str(default), PROJECT_FILTER)
        if not chosen:
            return False
        return self._write_project(_with_project_suffix(Path(chosen)))

    def confirm_discard(self) -> bool:
        """Ask about unsaved edits before something throws them away.

        Returns whether to proceed. Guards every path that replaces or drops the
        document — opening a video, opening a project, closing the video, and
        closing the window — because each of them silently destroyed a session's
        work before this existed.
        """
        if self._document.undo_stack.isClean():
            return True
        name = self._project_path.name if self._project_path is not None else "this project"
        answer = QMessageBox.warning(
            self,
            "SIEVE",
            UNSAVED_PROMPT.format(name=name),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return True

    # ---- project plumbing ------------------------------------------------

    def _read_project(self, path: Path) -> Project | None:
        """Parse the project at `path`, reporting why not rather than raising.

        The three failures are distinct and all ordinary: the file is gone, it
        is not YAML, or it is YAML that does not describe a project. None of
        them is a bug, and all of them arrive at the same place — a user who
        picked the wrong file, or a good file this build is too old to read.
        """
        try:
            return Project.load(path)
        except (OSError, YAMLError, ValidationError) as error:
            self._warn(f"Cannot open {path.name}:\n{error}")
            return None

    def _adopt_project(self, project: Project, path: Path) -> None:
        """Take `project` as the document, with `path` as its home."""
        self._document.load_project(project)
        self._project = project
        self._project_path = path
        self._document.undo_stack.setClean()
        self._update_title()

    def _write_project(self, path: Path) -> bool:
        """Assemble the document into a project file at `path`."""
        metadata = self._player.metadata
        if metadata is None:
            return False

        base = self._project
        if base is None:
            base = Project.for_video(metadata.path, path.parent)
        elif self._project_path is not None:
            # Unconditionally, without comparing the directories: rebasing onto
            # the directory a project is already anchored to is a no-op, and the
            # comparison that would skip it is a path-equality test — the kind
            # that is wrong across a symlink and right in every test.
            base = base.relocated(self._project_path.parent, path.parent)

        try:
            project = self._document.apply_to(base)
            project.save(path)
        except (OSError, ValidationError) as error:
            self._warn(f"Cannot save {path.name}:\n{error}")
            return False

        self._project = project
        self._project_path = path
        self._document.undo_stack.setClean()
        self._update_title()
        self.statusBar().showMessage(f"Saved {path.name}")
        return True

    def _open_neighbour_project(self, video: Path) -> None:
        """Open the project filed beside a video the user opened directly.

        VISION step 1 puts the project at the root of the source's own folder,
        so this file existing is the normal case for footage that has been
        worked on before. This used to ask, on the argument that silently
        restoring twelve replicates the user cannot see the provenance of is a
        worse surprise than one question. The argument survives in the
        announcement rather than in the question: the status bar says which
        project was restored and from where, so the provenance is still there
        without a modal in front of a video the user already asked for.
        """
        path = project_path_for(video)
        if not path.is_file():
            return
        self.open_project(path)
        # `open_project` reports its own failures and leaves the path unadopted;
        # announcing unconditionally would claim a restore that did not happen.
        if self._project_path == path:
            self.statusBar().showMessage(f"Restored {path.name}  ·  {path.parent}")

    def _update_title(self) -> None:
        """Restate what is open and whether it is saved.

        `[*]` is Qt's modified placeholder, expanded by `setWindowModified` into
        whatever the platform's convention is. With nothing open the title has
        no placeholder and nothing can be dirty, because a document with no
        source has no commands on its stack.
        """
        metadata = self._player.metadata
        if metadata is None:
            self.setWindowTitle("SIEVE")
            return
        subject = metadata.path.name
        if self._project_path is not None:
            subject = f"{subject}  ·  {self._project_path.name}"
        self.setWindowTitle(f"SIEVE — {subject}[*]")

    def _warn(self, message: str) -> None:
        """Say it in the status bar and in a dialog the user has to dismiss."""
        self.statusBar().showMessage(message.replace("\n", "  "))
        QMessageBox.warning(self, "SIEVE", message)

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
        """Unload the current video, its replicates, and the project they were in."""
        if not self.confirm_discard():
            return
        self._player.close()
        self._preview.close()
        self._document.unbind_source()
        self._replicate_tab.video_closed()
        self._timeline.video_closed()
        self._set_video_actions_enabled(False)
        self._project = None
        self._project_path = None
        self._pending_project = None
        self._update_title()
        self.statusBar().showMessage("Open a video to begin  ·  Ctrl+O")

    # ---- player feedback -------------------------------------------------

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        # Recorded on success rather than on the open attempt: a path that
        # failed to decode is not one to hand back at the next launch.
        self._preferences.last_video = metadata.path
        # Before the document is bound, so the reader is already opening while
        # the project below is applied. `open` is asynchronous and the graph
        # arrives synchronously; the runner's `opened` is what closes the gap.
        self._preview.open(metadata.path)
        self._document.bind_source(
            metadata.width, metadata.height, metadata.frame_count, metadata.fps
        )
        self._set_video_actions_enabled(True)
        self.statusBar().showMessage(
            f"{metadata.path.name}  ·  {metadata.width}x{metadata.height}  ·  "
            f"{metadata.fps:.2f} fps  ·  {metadata.frame_count:,} frames"
        )

        # Read and cleared before either branch runs: the neighbour open can
        # load a project of its own, and a pending entry still sitting here
        # would be applied to the wrong video by the next open.
        pending = self._pending_project
        self._pending_project = None
        if pending is not None:
            self._adopt_project(*pending)
        else:
            self._project = None
            self._project_path = None
            self._update_title()
            self._open_neighbour_project(metadata.path)

        # Last, and on both branches, because the document has to be bound
        # before the transport starts moving through it. The neighbour path no
        # longer raises a modal, but it can still adopt a project, and playing
        # under a document that is about to be replaced advances the transport
        # through a state the user never sees. Gated on the
        # action rather than on a fresh `metadata is not None`, because the
        # action already carries that condition *and* the editing one — if
        # play is not being offered, it should not happen by itself either.
        if self._play_action.isEnabled():
            self._player.play()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        # The pending project goes with it. Its video did not open, so there is
        # nothing for it to be a project *of*, and holding it would apply it to
        # whatever the user opened next.
        self._pending_project = None
        self._warn(message)

    # ---- the graph -------------------------------------------------------

    @Slot(object)
    def _on_render_finished(self, render: PreviewRender) -> None:
        """Say what the render covered and how much of it the store already had.

        The reuse share rather than a duration, because the duration is on the
        bus and the share is the number that says whether the session is doing
        what `pipeline/preview.py` claims: a second render after an edit
        reporting 0% is the failure that module is written against, and it is
        invisible in the frames.
        """
        self.statusBar().showMessage(
            f"Graph: {render.frames} frames {render.span.start}:{render.span.end}  ·  "
            f"{render.computed} computed, {render.from_cache} cached "
            f"({render.reuse:.0%} reuse)"
        )

    @Slot(str)
    def _on_render_failed(self, message: str) -> None:
        """A graph that will not run says so in the status bar and nowhere else.

        Not a dialog. The graph arrives from a project file rather than from
        anything the user just did, so a modal here would interrupt them over a
        decision they did not make — and the preview failing does not stop them
        scrubbing, cutting, or drawing arenas.
        """
        self.statusBar().showMessage(f"Graph cannot run: {message}")

    @Slot(str)
    def _on_preview_unavailable(self, message: str) -> None:
        self.statusBar().showMessage(f"No preview: {message}")

    @Slot()
    def _on_scrub_degraded(self) -> None:
        """Tell the user the drag just started meaning something slightly different."""
        self._toast.show_message(COARSE_SCRUB_NOTICE)

    @Slot()
    def _on_preferences_changed(self) -> None:
        self._player.apply_preferences(self._preferences)

    @Slot()
    def _on_clip_changed(self) -> None:
        """There is only something to clear once something has been marked."""
        self._clear_clip_action.setEnabled(self._document.clip is not None)

    @Slot(bool)
    def _on_clean_changed(self, clean: bool) -> None:
        self.setWindowModified(not clean)

    @Slot(bool)
    def _on_editing_changed(self, editing: bool) -> None:
        """Yield the typing keys while something is actually being typed into.

        Space and delete, and now I and O — a rename typed into the table
        would otherwise mark a clip once per vowel.

        A plain `bool` again, and it can be: the tab arrives here having already
        aggregated its named sources (`gui/editing_sources.py`), so this is one
        answer from one sender rather than the latch two senders used to fight
        over. `editing` is *being typed into*, not *has focus* — a spin box
        holding the keyboard without a keystroke in it does not stop playback.
        """
        has_video = self._player.metadata is not None
        self._play_action.setEnabled(has_video and not editing)
        self._delete_action.setEnabled(not editing)
        self._mark_in_action.setEnabled(has_video and not editing)
        self._mark_out_action.setEnabled(has_video and not editing)

    def _set_video_actions_enabled(self, enabled: bool) -> None:
        for action in (
            self._save_action,
            self._save_as_action,
            self._close_action,
            self._play_action,
            self._next_frame_action,
            self._previous_frame_action,
            self._start_action,
            self._mark_in_action,
            self._mark_out_action,
        ):
            action.setEnabled(enabled)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Offer to save, then stop the decode thread before the window goes away.

        The prompt comes first and can refuse the close outright. Shutting the
        player down before asking would leave a window the user chose to keep
        with a dead decoder in it.
        """
        if not self.confirm_discard():
            event.ignore()
            return
        self._player.shutdown()
        # The adapter before the runner: the runner's last act is to abandon a
        # render, and a subscription still live on a QObject Qt is about to
        # delete is the one way a shutdown can crash rather than merely wait.
        self._metrics.close()
        self._preview.shutdown()
        # After the preview: the detector is fed by the render thread's frames,
        # so stopping it first would leave the runner delivering to a tab whose
        # worker thread has already gone.
        self._filter_tab.shutdown()
        super().closeEvent(event)


def _with_project_suffix(path: Path) -> Path:
    """`path` renamed to end in `.sieve.yaml`.

    A file dialog hands back whatever was typed, and `project_path_for` is a
    convention other code reads: a project saved as `arena.yaml` would never be
    found beside its video again. The double suffix is why `with_suffix` cannot
    do this.
    """
    if path.name.endswith(PROJECT_SUFFIX):
        return path
    return path.with_name(path.stem + PROJECT_SUFFIX)
