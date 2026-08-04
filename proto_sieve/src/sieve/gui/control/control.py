"""Secret: which of the three top-level screens is showing — project
selection, the pipeline view, and the step list — and the mechanic that
switches between them (the Obsidian sliding-panes look: the whole track of
three panes slides by one pane-width; nothing cuts instantly, nothing grows
a tab bar). Not the canvas — ``app.py`` swaps that separately, this module
never mentions it. Not what a project-select screen or a step list look
like — ``project_select/`` and ``pipeline/`` own those; this module only
ever owns the three-pane track, the rail that rides alongside positions 1
and 2, and which position is current.

The rail sits outside the sliding track, never inside it — "switching
panes must never hide it" (``rail.py``'s own docstring) still holds, just
one level up from where it used to live (``PipelinePanel``, since
dissolved into this module). It's rebuilt fresh (new step count) on every
``show_workspace`` call; project info (position 0) hides it rather than
showing an empty one.

``project_selected`` forwards straight from whichever ``ProjectSelect``
instance currently sits at position 0 — this module never touches
``AppState`` or decides whether a selection is allowed to proceed to the
workspace; that's still ``app.py``, via ``show_workspace``.

The rail's current tick is not this module's fact either — ``current_index``
is ``session.Session``'s (which step is current), passed in on every
``show_workspace`` call rather than hardcoded, so this module never invents
a value the domain layer already owns. Which *pane* is showing (Pipeline vs
Step) has no such domain equivalent — ``Session`` is headless, no Qt — so
that choice stays this module's own secret.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from proto_sieve.src.sieve.gui.control.pipeline.pipeline import build_step_list
from proto_sieve.src.sieve.gui.control.pipeline.rail import StepRail
from proto_sieve.src.sieve.gui.control.project_select import ProjectSelect
from proto_sieve.src.sieve.pipeline import Pipeline
from proto_sieve.src.sieve.projects import Project

_SLIDE_DURATION_MS = 220

_POS_PROJECT, _POS_PIPELINE, _POS_STEP = range(3)
_POSITION_NAMES = ("project", "pipeline", "step")


class _SlidingPanes(QWidget):
    """A fixed-count, ordered set of panes side by side in a track N-times
    this widget's width; switching slides the whole track by one pane's
    width instead of cutting instantly. ``replace_pane`` swaps a position's
    widget in place, with no animation, whether or not it's current — used
    when a position's content changes (a fresh project list, a newly
    rendered step list) as opposed to when only which position is current
    changes (``set_current``, the only thing that animates)."""

    def __init__(self, panes: list[QWidget], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._panes = list(panes)
        self._current = 0

        self._track = QWidget(self)
        for pane in self._panes:
            pane.setParent(self._track)

        self._animation = QPropertyAnimation(self._track, b"pos", self)
        self._animation.setDuration(_SLIDE_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def current_index(self) -> int:
        return self._current

    def replace_pane(self, index: int, widget: QWidget) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        old = self._panes[index]
        widget.setParent(self._track)
        self._panes[index] = widget

        width, height = self.width(), self.height()
        if width:
            widget.setGeometry(index * width, 0, width, height)
        # Every pane stays visible, side by side in the track — it's the
        # track's own position (moved by set_current) that decides what's
        # in frame, same as the parent clipping the ones off-screen. Unlike
        # BreadcrumbStack's overlaid panes, hiding a pane here would hide
        # the very thing set_current is about to slide to.
        widget.show()

        old.hide()
        old.setParent(None)
        old.deleteLater()

    def set_current(self, index: int) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        self._current = index
        target = QPoint(-index * self.width(), 0)
        self._animation.stop()
        self._animation.setStartValue(self._track.pos())
        self._animation.setEndValue(target)
        self._animation.start()

    def resizeEvent(self, event) -> None:  # noqa: ARG002 - Qt event signature
        super().resizeEvent(event)
        width, height = self.width(), self.height()
        self._track.setFixedSize(width * len(self._panes), height)
        for i, pane in enumerate(self._panes):
            pane.setGeometry(i * width, 0, width, height)
        # A resize mid-animation would otherwise leave the track at a
        # now-stale pixel offset computed against the old width.
        self._animation.stop()
        self._track.move(-self._current * width, 0)


class Control(QWidget):
    project_selected = Signal(object)  # emits the chosen Project

    def __init__(self, projects: list[Project], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._rail = StepRail(step_count=0, current_index=0)
        self._rail.setVisible(False)

        self._panes = _SlidingPanes([self._build_project_select(projects), QWidget(), QWidget()])

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._rail)
        self._layout.addWidget(self._panes)

    def current_position(self) -> str:
        return _POSITION_NAMES[self._panes.current_index()]

    def show_project_info(self, projects: list[Project]) -> None:
        self._panes.replace_pane(_POS_PROJECT, self._build_project_select(projects))
        self._rail.setVisible(False)
        self._panes.set_current(_POS_PROJECT)

    def show_workspace(self, pipeline: Pipeline, current_index: int) -> None:
        old_rail = self._rail
        self._rail = StepRail(step_count=len(pipeline.steps), current_index=current_index)
        self._layout.replaceWidget(old_rail, self._rail)
        old_rail.setParent(None)
        old_rail.deleteLater()
        self._rail.show()

        self._panes.replace_pane(_POS_PIPELINE, QWidget())
        self._panes.replace_pane(_POS_STEP, build_step_list(pipeline))
        self._panes.set_current(_POS_PIPELINE)

    def show_pipeline_tab(self) -> None:
        self._panes.set_current(_POS_PIPELINE)

    def show_step_tab(self) -> None:
        self._panes.set_current(_POS_STEP)

    def _build_project_select(self, projects: list[Project]) -> ProjectSelect:
        select = ProjectSelect(projects)
        select.project_selected.connect(self.project_selected)
        return select


if __name__ == "__main__":
    # Standalone smoke test: this widget must show something on its own,
    # with no app.py, no layout.py, no video in the loop.
    import sys
    from pathlib import Path

    def _find_repo_root(start: Path) -> Path:
        # Walks up to the marker (pyproject.toml) instead of counting
        # parents — a fixed index breaks the moment this file moves depth.
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        raise RuntimeError(f"no pyproject.toml found above {start}")

    _repo_root = _find_repo_root(Path(__file__).resolve())
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

    from PySide6.QtWidgets import QApplication

    from proto_sieve.src.sieve.pipeline import Step

    pipeline = Pipeline(
        source="rep3_intermittent_crop",
        steps=(Step(tool="crop", params={"y0": 0, "y1": 200, "x0": 0, "x1": 200}),),
    )

    app = QApplication(sys.argv)
    control = Control(projects=[])
    control.show_workspace(pipeline, current_index=0)
    control.resize(300, 400)
    control.show()
    sys.exit(app.exec())
