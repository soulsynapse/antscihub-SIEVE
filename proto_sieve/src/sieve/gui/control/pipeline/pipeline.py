"""Two panes, Pipeline and Step, and the current-step rail down the left
edge outside both — switching panes must never hide it, since it tracks
which step is active regardless of which view the user is looking at.
"Step" holds the step list (``StepBox`` per step) that used to sit here
directly. "Pipeline" has nothing in it yet — not designed, so it doesn't
exist yet, not stubbed to look designed. What a step's box or the rail
look like are ``step/`` and ``rail/``'s secrets, not this module's.
"Current" is a placeholder, index 0, until something real (a selection,
the executor) decides it.

No tab bar — Step drills in over Pipeline (Obsidian sliding-panes / Andy's
mode: going to Step collapses Pipeline to a labeled bar rather than
sliding it off-screen; going back re-expands that same bar, nothing
rebuilds), via ``gui/breadcrumb_stack``'s ``BreadcrumbStack`` — shared with
``app.py``'s project-info/workspace transition, since both need the same
mechanic. This module owns which two widgets go in and what "Pipeline" vs
"Step" means (including the click-to-go-back path — the stack's own
``activated`` signal is wired straight back to this module's own
``show_pipeline_tab``/``show_step_tab``, the same as Left/Right); the
stack itself owns how the switch looks.

``show_pipeline_tab``/``show_step_tab``/``current_tab`` exist so a caller
(``app.py``'s Left/Right navigation) can drive which pane is showing
without reaching into ``BreadcrumbStack`` itself — index 0 is "Pipeline",
index 1 is "Step", but that numbering is this module's own secret, not
exposed. The method names keep the word "tab" even though there's no tab
bar anymore — "pane" would be more honest, but renaming would touch
``app.py`` for no behavioral reason; see docs/DECISIONS.md."""

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

from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QWidget

from proto_sieve.src.sieve.gui.breadcrumb_stack import BreadcrumbStack
from proto_sieve.src.sieve.gui.control.pipeline.rail import StepRail
from proto_sieve.src.sieve.gui.control.pipeline.step import StepBox
from proto_sieve.src.sieve.pipeline import Pipeline


class PipelinePanel(QWidget):
    def __init__(self, pipeline: Pipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._rail = StepRail(step_count=len(pipeline.steps), current_index=0)
        self._stack = BreadcrumbStack([("Pipeline", QWidget()), ("Step", self._build_step_list(pipeline))])
        self._stack.activated.connect(self._on_breadcrumb_clicked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._rail)
        layout.addWidget(self._stack)

    def show_pipeline_tab(self) -> None:
        self._stack.set_current(0)

    def show_step_tab(self) -> None:
        self._stack.set_current(1)

    def current_tab(self) -> str:
        return "pipeline" if self._stack.current_index() == 0 else "step"

    def _on_breadcrumb_clicked(self, index: int) -> None:
        self.show_pipeline_tab() if index == 0 else self.show_step_tab()

    def _build_step_list(self, pipeline: Pipeline) -> QWidget:
        step_list = QListWidget()
        for i, step in enumerate(pipeline.steps, start=1):
            box = StepBox(i, step)
            item = QListWidgetItem(step_list)
            item.setSizeHint(box.sizeHint())
            step_list.addItem(item)
            step_list.setItemWidget(item, box)
        return step_list


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no video in the loop.
    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.pipeline import Step

    pipeline = Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )

    app = QApplication(sys.argv)
    panel = PipelinePanel(pipeline)
    panel.resize(300, 400)
    panel.show()
    sys.exit(app.exec())
