"""Secret: how the user reviews and revisits a past state for the active
project — two different kinds of "past", shown side by side but never
conflated. A saved pipeline (``pipeline/store.py``, one name per project,
overwrite) is a deliberate save the user made; a timeline entry
(``session/history.py``) is this session's in-memory undo/redo stack, gone
the moment the app closes. This module never applies either choice itself —
it only ever emits which one was picked (a name, or a timeline index) and
lets the caller decide what loading or jumping means for the live session.
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
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from proto_sieve.src.sieve.pipeline import list_pipelines
from proto_sieve.src.sieve.projects import Project
from proto_sieve.src.sieve.session.session import Session


class ProjectHistoryWindow(QDialog):
    saved_pipeline_load_requested = Signal(str)  # emits the chosen saved name
    timeline_jump_requested = Signal(int)  # emits the chosen timeline index

    def __init__(self, project: Project, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"History — {project.name}")

        # One save per project, overwrite (see docs/DECISIONS.md) — so this
        # is at most a single entry, never a name browser.
        saved_names = [name for name in list_pipelines() if name == project.name]
        saved_list = QListWidget(self)
        for name in saved_names:
            saved_list.addItem(name)
        saved_list.itemDoubleClicked.connect(lambda item: self._on_saved_chosen(item.text()))

        timeline = session.history_timeline()
        current = session.history_index()
        timeline_list = QListWidget(self)
        for i, pipeline in enumerate(timeline):
            label = f"{i}: {len(pipeline.steps)} step(s)"
            if i == current:
                label += "  (current)"
            item = QListWidgetItem(label)
            timeline_list.addItem(item)
        timeline_list.setCurrentRow(current)
        timeline_list.itemDoubleClicked.connect(
            lambda item: self._on_timeline_chosen(timeline_list.row(item))
        )

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Saved pipeline (double-click to load)"))
        layout.addWidget(saved_list)
        layout.addWidget(QLabel("Undo/redo timeline (double-click to jump)"))
        layout.addWidget(timeline_list, 1)

        self.resize(420, 360)

    def _on_saved_chosen(self, name: str) -> None:
        self.saved_pipeline_load_requested.emit(name)
        self.accept()

    def _on_timeline_chosen(self, index: int) -> None:
        self.timeline_jump_requested.emit(index)
        self.accept()


if __name__ == "__main__":
    # Standalone smoke test: this window must show something on its own,
    # with no app.py, no menu.py in the loop.
    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.pipeline import Pipeline
    from proto_sieve.src.sieve.session.session import Session as _Session

    app = QApplication(sys.argv)
    demo_project = Project("demo", Path("demo.mp4"))
    demo_session = _Session(Pipeline(source="demo", steps=()))
    window = ProjectHistoryWindow(demo_project, demo_session)
    window.saved_pipeline_load_requested.connect(lambda name: print(f"load saved: {name}"))
    window.timeline_jump_requested.connect(lambda i: print(f"jump to: {i}"))
    window.show()
    sys.exit(app.exec())
