"""Picking one of the project files that already exist.

The first cut opens a project; it does not build one from a folder of videos
(`PLAN.md`, Phase 7), so there is no "new project" path here and no file
dialog. What this widget emits is a path, never a `Project` — reading the
document is the session layer's, and a widget that had already parsed one would
be holding a value it is not the owner of by the time anything asked it for one.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from sieve.core.pipeline_model import PROJECT_SUFFIX


def projects_in(directory: Path) -> tuple[Path, ...]:
    """Every project file directly in `directory`, in a stable order.

    Not recursive: a scan that descended would put the same list in front of a
    user whichever folder they picked, and the folder they picked is the answer
    they gave. Sorted, because the order a filesystem returns entries in is not
    a property anyone chose, and a list that reshuffled between launches would
    make the same keystrokes open different projects.
    """
    return tuple(sorted(directory.glob(f"*{PROJECT_SUFFIX}")))


class ProjectSelect(QWidget):
    project_chosen = Signal(object)  # emits the chosen Path

    def __init__(self, projects: Sequence[Path], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._projects = tuple(projects)

        self.list_widget = QListWidget(self)
        for project in self._projects:
            # The suffix is the same on every row, so showing it would spend the
            # width that tells two projects apart on the part that never differs.
            self.list_widget.addItem(project.name.removesuffix(PROJECT_SUFFIX))
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_widget)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        self.project_chosen.emit(self._projects[self.list_widget.row(item)])
