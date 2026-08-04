"""The GUI sitting, per docs/AGENTS.md: not a chunk, no cheap proof.

PySide6. The central widget (built exactly once, by ``layout.compose``) is
a canvas/control split: ``layout.CanvasSlot`` on the left, swapped in place
with no animation, and ``control.Control`` on the right, a three-position
sliding track (project info, Pipeline, Step) plus the current-step rail —
built once and never rebuilt, so its own state (which position is current)
survives every navigation. With no project chosen, the canvas holds a bare
"select a project" label (not a real canvas implementation — nothing
designed yet, see ``gui/canvas/__init__.py``) and ``Control`` sits at
project info; once one's picked (``session.app_state.select``), the canvas
becomes ``VideoPlayer`` on the project's source and ``Control`` is told to
show the workspace. A freshly-chosen project always starts empty — nothing
loads a saved pipeline automatically.

``menu.py`` calls back into three public methods (``load_project``,
``save_pipeline``, ``open_history``) rather than reaching into ``AppState``
itself — this file owns what those verbs mean, ``menu.py`` only owns that
they're reachable. All three states that can replace the current
``Pipeline`` (fresh project select, a loaded save, a timeline jump) funnel
through ``_render_workspace``, which re-renders the canvas and tells
``Control`` to show the (possibly changed) workspace — there is no
incremental update path yet, so all three reopen the video.

Left/Right (``go_back``/``go_forward``, bound once by
``hotkeys.bind_navigation_hotkeys``) walk the same three-position chain
``Control`` tracks, read via ``Control.current_position()`` rather than
inferred from a widget's type. Moving between the two workspace positions
calls ``Control``'s own tab methods directly (no rebuild, video keeps
playing); moving to or from project info still goes through the full
``show_project_info``/``show_workspace`` path.
"""

from __future__ import annotations

import sys
from pathlib import Path

def _find_repo_root(start: Path) -> Path:
    # Walks up to the marker (pyproject.toml) instead of counting parents —
    # a fixed index breaks the moment this file moves to a different depth.
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"no pyproject.toml found above {start}")


_REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(_REPO_ROOT) not in sys.path:
    # Makes `python app.py` work the same as `python -m ...gui.app` — the
    # package-style imports below need the repo root on sys.path, which a
    # direct script launch (VSCode's "Run Python File", etc.) doesn't add.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from proto_sieve.src.sieve.gui.hotkeys import bind_hotkeys, bind_navigation_hotkeys
from proto_sieve.src.sieve.gui.layout import CanvasSlot, compose, size_window
from proto_sieve.src.sieve.gui.menu import build_menu_bar
from proto_sieve.src.sieve.gui.control import Control
from proto_sieve.src.sieve.gui import style
from proto_sieve.src.sieve.gui.style import apply as apply_style
from proto_sieve.src.sieve.gui.style import apply_title_bar
from proto_sieve.src.sieve.gui.canvas.video_player import VideoPlayer
from proto_sieve.src.sieve.gui.windows import ProjectHistoryWindow
from proto_sieve.src.sieve.pipeline import load as load_pipeline, save as save_pipeline
from proto_sieve.src.sieve.projects import Project, list_projects
from proto_sieve.src.sieve.session import app_state
from proto_sieve.src.sieve.preferences import appearance as appearance_prefs


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("proto_sieve")

        self._state: app_state.AppState = app_state.NoProject()

        self._top_bar = QLabel("top")
        self._top_bar.setFixedHeight(0)  # unused for now, zeroed rather than removed
        style.tag(self._top_bar, style.ROLE_BAR)
        self._bottom_bar = QLabel("bottom")
        self._bottom_bar.setFixedHeight(style.bar_height() * 2)
        style.tag(self._bottom_bar, style.ROLE_BAR)

        self._canvas_slot = CanvasSlot(QLabel("Select a project"))
        self._control = Control(list_projects())
        self._control.project_selected.connect(self._on_project_selected)
        self.setCentralWidget(compose(self._top_bar, self._canvas_slot, self._control, self._bottom_bar))

        build_menu_bar(self)
        bind_navigation_hotkeys(self)

        size_window(self)

    def show_project_info(self) -> None:
        """Left, and the initial screen: the project-select screen. Never
        touches ``self._state`` itself — an already-active session survives
        underneath it untouched (``show_workspace``/Right returns to exactly
        where it was); picking a project from the list here still starts a
        fresh one, same as it always has."""
        self._canvas_slot.set_content(QLabel("Select a project"))
        self._control.show_project_info(list_projects())

    def show_workspace(self) -> None:
        """Right (from project info): back to the pipeline workspace for the
        active session, landing on the Pipeline tab. A no-op with no active
        session — nothing to return to."""
        if not isinstance(self._state, app_state.ProjectActive):
            return
        self._render_workspace()

    def go_back(self) -> None:
        """Left: Step -> Pipeline tab (no rebuild) -> project info. A no-op
        already at project info — nothing further back."""
        position = self._control.current_position()
        if position == "step":
            self._control.show_pipeline_tab()
        elif position == "pipeline":
            self.show_project_info()

    def go_forward(self) -> None:
        """Right: project info -> workspace (Pipeline tab) -> Step tab."""
        position = self._control.current_position()
        if position == "project":
            self.show_workspace()
        elif position == "pipeline":
            self._control.show_step_tab()

    def _on_project_selected(self, project: Project) -> None:
        self._state = app_state.select(project)
        self._render_workspace()

    def _render_workspace(self) -> None:
        """Re-render the canvas and tell ``Control`` to show the workspace
        for ``self._state``'s current pipeline. Reused after picking a
        project, loading a saved pipeline, and jumping the undo/redo
        timeline — all three replace which ``Pipeline`` is current, and
        none of them have an incremental update path yet, so all three pay
        the same full-rebuild (video reopened) cost. Cheaper live updates
        are future work, not this slice's problem."""
        assert isinstance(self._state, app_state.ProjectActive)

        canvas = VideoPlayer()
        self._canvas_slot.set_content(canvas)
        self._control.show_workspace(self._state.session.pipeline, self._state.session.current_index)

        bind_hotkeys(self, canvas)
        canvas.open(self._state.project.source_path)

    def load_project(self) -> None:
        """File > Load Project: back to the project-select screen, whatever
        the current state was. Does not save first — nothing here asks.
        Unlike Left/Right, this discards the active session — it's the
        "start over" path, not the "peek back" one."""
        self._state = app_state.NoProject()
        self.show_project_info()

    def save_pipeline(self) -> None:
        """File > Save Pipeline: one save per project, overwrite, keyed by
        the project's own name (see docs/DECISIONS.md)."""
        if not isinstance(self._state, app_state.ProjectActive):
            return
        save_pipeline(self._state.project.name, self._state.session.pipeline)

    def open_history(self) -> None:
        if not isinstance(self._state, app_state.ProjectActive):
            return
        dialog = ProjectHistoryWindow(self._state.project, self._state.session, self)
        dialog.saved_pipeline_load_requested.connect(self._on_saved_pipeline_load)
        dialog.timeline_jump_requested.connect(self._on_timeline_jump)
        dialog.exec()

    def _on_saved_pipeline_load(self, name: str) -> None:
        assert isinstance(self._state, app_state.ProjectActive)
        self._state.session.load(load_pipeline(name))
        self._render_workspace()

    def _on_timeline_jump(self, index: int) -> None:
        assert isinstance(self._state, app_state.ProjectActive)
        self._state.session.jump_to(index)
        self._render_workspace()


def main() -> None:
    app = QApplication(sys.argv)
    apply_style(app)
    window = MainWindow()
    window.show()
    apply_title_bar(window)
    appearance_prefs.subscribe(lambda: apply_style(app))
    appearance_prefs.subscribe(lambda: apply_title_bar(window))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
