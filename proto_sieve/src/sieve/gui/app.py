"""The GUI sitting, per docs/AGENTS.md: not a chunk, no cheap proof.

PySide6. Two screens, both built from ``layout.compose``'s canvas/control
split: with no project chosen, the left is a bare "select a project" label
(not a real canvas implementation — nothing designed yet, see
``gui/canvas/__init__.py``) and the right is ``ProjectSelect`` reading the
projects registry; once one's picked (``session.app_state.select``), the
left becomes ``VideoPlayer`` on the project's source and the right becomes
``PipelinePanel`` on a fresh empty pipeline for it. Nothing here saves or
loads a pipeline yet — a freshly-chosen project always starts empty.
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

from proto_sieve.src.sieve.gui.hotkeys import bind_hotkeys
from proto_sieve.src.sieve.gui.layout import compose, size_window
from proto_sieve.src.sieve.gui.menu import build_menu_bar
from proto_sieve.src.sieve.gui.control.pipeline import PipelinePanel
from proto_sieve.src.sieve.gui.control.project_select import ProjectSelect
from proto_sieve.src.sieve.gui import style
from proto_sieve.src.sieve.gui.style import apply as apply_style
from proto_sieve.src.sieve.gui.style import apply_title_bar
from proto_sieve.src.sieve.gui.canvas.video_player import VideoPlayer
from proto_sieve.src.sieve.projects import Project, list_projects
from proto_sieve.src.sieve.session import app_state
from proto_sieve.src.sieve.preferences import appearance as appearance_prefs


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("proto_sieve")

        self._state: app_state.AppState = app_state.NoProject()

        self._top_bar = QLabel("top")
        self._top_bar.setFixedHeight(style.bar_height())
        style.tag(self._top_bar, style.ROLE_BAR)
        self._bottom_bar = QLabel("bottom")
        self._bottom_bar.setFixedHeight(style.bar_height())
        style.tag(self._bottom_bar, style.ROLE_BAR)

        build_menu_bar(self)
        self._show_project_select()

        size_window(self)

    def _show_project_select(self) -> None:
        canvas = QLabel("Select a project")
        control = ProjectSelect(list_projects())
        control.project_selected.connect(self._on_project_selected)
        self.setCentralWidget(compose(self._top_bar, canvas, control, self._bottom_bar))

    def _on_project_selected(self, project: Project) -> None:
        self._state = app_state.select(project)

        canvas = VideoPlayer()
        control = PipelinePanel(self._state.session.pipeline)
        self.setCentralWidget(compose(self._top_bar, canvas, control, self._bottom_bar))

        bind_hotkeys(self, canvas)
        canvas.open(self._state.project.source_path)


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
