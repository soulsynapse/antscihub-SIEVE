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
showing an empty one — but keeps its width reserved, so no navigation ever
changes the track's width while the track is sliding.

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

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from proto_sieve.src.sieve.gui.control.pipeline.pipeline import build_step_list
from proto_sieve.src.sieve.gui.control.pipeline.rail import StepRail
from proto_sieve.src.sieve.gui.control.project_select import ProjectSelect
from proto_sieve.src.sieve.pipeline import Pipeline
from proto_sieve.src.sieve.projects import Project

_SLIDE_DURATION_MS = 260

_POS_PROJECT, _POS_PIPELINE, _POS_STEP = range(3)
_POSITION_NAMES = ("project", "pipeline", "step")


class _SlidingPanes(QWidget):
    """A fixed-count, ordered set of panes side by side in a track N-times
    this widget's width; switching slides the whole track by one pane's
    width instead of cutting instantly. ``replace_pane`` swaps a position's
    widget in place, with no animation, whether or not it's current — used
    when a position's content changes (a fresh project list, a newly
    rendered step list) as opposed to when only which position is current
    changes (``set_current``, the only thing that animates).

    What animates is ``offset``, a float in *pane units* (1.5 = halfway
    between panes 1 and 2), not the track's pixel position. That indirection
    is the whole reason a slide survives a resize: pixels computed against
    one width are stale the instant the width changes, so the earlier
    pixel-animating version had to stop the animation from ``resizeEvent``
    and jump to the destination — and every transition in or out of the
    workspace resizes this widget (``Control`` shows or hides the rail
    beside it), so in practice the only transitions that ever animated were
    Pipeline <-> Step. An offset in pane units stays correct across a width
    change; a resize just re-lays out at whatever fraction the slide has
    reached, and the slide keeps running.
    """

    def __init__(self, panes: list[QWidget], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._panes = list(panes)
        self._current = 0
        self._offset = 0.0

        self._track = QWidget(self)
        for pane in self._panes:
            pane.setParent(self._track)

        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(_SLIDE_DURATION_MS)
        # Out-only easing reads as the track being flicked and coasting to
        # rest; an InOut curve on a distance this short just looks sluggish.
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._relayout()

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self._track.move(-round(self._offset * self.width()), 0)

    offset = Property(float, _get_offset, _set_offset)

    def current_index(self) -> int:
        return self._current

    def replace_pane(self, index: int, widget: QWidget) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        old = self._panes[index]
        widget.setParent(self._track)
        self._panes[index] = widget

        # Every pane stays visible, side by side in the track — it's the
        # track's own position (moved as offset animates) that decides
        # what's in frame, with the parent clipping the ones off-screen.
        # Unlike BreadcrumbStack's overlaid panes, hiding a pane here would
        # hide the very thing the next slide is about to reveal.
        widget.show()
        self._relayout()

        old.hide()
        old.setParent(None)
        old.deleteLater()

    def set_current(self, index: int) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        running = self._animation.state() == QAbstractAnimation.State.Running
        if index == self._current and not running:
            return
        self._current = index
        # Restarting from the live offset rather than from the pane it was
        # heading to keeps a fast Left-Right-Left from jumping backwards
        # before it slides.
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(float(index))
        self._animation.start()

    def resizeEvent(self, event) -> None:  # noqa: ARG002 - Qt event signature
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        width, height = self.width(), self.height()
        self._track.resize(width * len(self._panes), height)
        for i, pane in enumerate(self._panes):
            pane.setGeometry(i * width, 0, width, height)
        self._set_offset(self._offset)


class Control(QWidget):
    project_selected = Signal(object)  # emits the chosen Project

    def __init__(self, projects: list[Project], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._rail = self._build_rail(step_count=0, current_index=0)
        self._rail.setVisible(False)

        self._panes = _SlidingPanes([self._build_project_select(projects), QWidget(), QWidget()])

        self._layout = QHBoxLayout(self)
        # The rail is a left gutter, so zero margins are not symmetric: the
        # panes would sit rail-width plus the layout's default spacing in
        # from the left edge and flush against the right one. Spacing goes
        # to 0 and the right margin to the rail's own width, which leaves
        # equal whitespace either side of the panes — the left gutter being
        # the one with ticks drawn in it. Read off the rail rather than
        # restated as a constant here; how wide the strip is is rail.py's.
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, self._rail.maximumWidth(), 0)
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
        self._rail = self._build_rail(len(pipeline.steps), current_index)
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

    def _build_rail(self, step_count: int, current_index: int) -> StepRail:
        rail = StepRail(step_count=step_count, current_index=current_index)
        # Hiding the rail at project info must not take its width back:
        # that would resize the track beside it in the same event loop turn
        # as the slide it's part of. The slide itself now survives a resize
        # (see _SlidingPanes), but the panes would still visibly jog
        # sideways mid-flight. The rail is one tick wide, so the reserved
        # strip costs nothing to look at.
        policy = rail.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        rail.setSizePolicy(policy)
        return rail

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
