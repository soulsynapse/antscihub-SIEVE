"""Secret: how the user picks a project when the session has none open yet —
a list of what's in the registry, plus the only way a new one gets added.
Not when this screen shows instead of the pipeline view — that's ``app.py``,
branching on ``session.app_state.AppState``. This module never touches
``AppState`` itself; it only ever emits which ``Project`` was picked.
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
    # Same reasoning as app.py: makes running this file directly work the
    # same as running it via -m.
    sys.path.insert(0, str(_REPO_ROOT))

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from proto_sieve.src.sieve.projects import Project, add_project

_VIDEO_FILTER = "Video files (*.mp4 *.mov *.mkv *.avi)"


class ProjectSelect(QWidget):
    project_selected = Signal(object)  # emits the chosen Project

    def __init__(self, projects: list[Project], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._projects = list(projects)

        self._list = QListWidget(self)
        for project in self._projects:
            self._list.addItem(project.name)
        self._list.itemClicked.connect(self._on_item_clicked)

        add_button = QPushButton("Add project…", self)
        add_button.clicked.connect(self._on_add_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list, 1)
        layout.addWidget(add_button)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.project_selected.emit(self._projects[self._list.row(item)])

    def _on_add_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Add project", "", _VIDEO_FILTER)
        if not path:
            return
        project = Project(Path(path).stem, Path(path))
        try:
            add_project(project)
        except ValueError:
            return  # a project with this name already exists; not this pass's problem
        self._projects.append(project)
        self._list.addItem(project.name)


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no session in the loop.
    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.projects import list_projects

    app = QApplication(sys.argv)
    select = ProjectSelect(list_projects())
    select.project_selected.connect(lambda p: print(f"selected: {p.name}"))
    select.resize(300, 400)
    select.show()
    sys.exit(app.exec())
