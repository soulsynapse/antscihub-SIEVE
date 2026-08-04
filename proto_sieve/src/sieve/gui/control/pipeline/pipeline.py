"""Two panes, Pipeline and Step, and the current-step rail down the left
edge outside both — switching panes must never hide it, since it tracks
which step is active regardless of which view the user is looking at.
"Step" holds the step list (``StepBox`` per step) that used to sit here
directly. "Pipeline" has nothing in it yet — not designed, so it doesn't
exist yet, not stubbed to look designed. What a step's box or the rail
look like are ``step/`` and ``rail/``'s secrets, not this module's.
"Current" is a placeholder, index 0, until something real (a selection,
the executor) decides it.

No tab bar — the two panes sit side by side in a track twice this widget's
width, and switching slides the track instead of cutting instantly (the
Obsidian sliding-panes look). ``_SlidingPanes`` is this module's own
plumbing, not a shared GUI primitive yet; nothing else needs the sliding
behavior today, so it isn't factored out until something else does.

``show_pipeline_tab``/``show_step_tab``/``current_tab`` exist so a caller
(``app.py``'s Left/Right navigation) can drive which pane is showing
without reaching into ``_SlidingPanes`` itself — index 0 is "Pipeline",
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

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QWidget,
)

from proto_sieve.src.sieve.gui.control.pipeline.rail import StepRail
from proto_sieve.src.sieve.gui.control.pipeline.step import StepBox
from proto_sieve.src.sieve.pipeline import Pipeline

_SLIDE_DURATION_MS = 220


class _SlidingPanes(QWidget):
    """A fixed set of panes, laid out side by side in a track N-times this
    widget's width; showing one is animating the track so exactly one pane
    sits in the visible frame. Not a ``QTabWidget`` (no tab bar wanted) or a
    plain ``QStackedWidget`` (cuts instantly instead of sliding). Panes are
    fixed at construction — nothing here supports adding one later, this
    spike only ever needs two."""

    def __init__(self, panes: list[QWidget], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._panes = panes
        self._current = 0

        self._track = QWidget(self)
        for pane in panes:
            pane.setParent(self._track)

        self._animation = QPropertyAnimation(self._track, b"pos", self)
        self._animation.setDuration(_SLIDE_DURATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def current_index(self) -> int:
        return self._current

    def set_current(self, index: int) -> None:
        if not 0 <= index < len(self._panes):
            raise IndexError(index)
        self._current = index
        target = QPoint(-index * self.width(), 0)
        self._animation.stop()
        self._animation.setStartValue(self._track.pos())
        self._animation.setEndValue(target)
        self._animation.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width, height = self.width(), self.height()
        self._track.setFixedSize(width * len(self._panes), height)
        for i, pane in enumerate(self._panes):
            pane.setGeometry(i * width, 0, width, height)
        # A resize mid-animation would otherwise leave the track at a
        # now-stale pixel offset computed against the old width.
        self._animation.stop()
        self._track.move(-self._current * width, 0)


class PipelinePanel(QWidget):
    def __init__(self, pipeline: Pipeline, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._rail = StepRail(step_count=len(pipeline.steps), current_index=0)
        self._panes = _SlidingPanes([QWidget(), self._build_step_list(pipeline)])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._rail)
        layout.addWidget(self._panes)

    def show_pipeline_tab(self) -> None:
        self._panes.set_current(0)

    def show_step_tab(self) -> None:
        self._panes.set_current(1)

    def current_tab(self) -> str:
        return "pipeline" if self._panes.current_index() == 0 else "step"

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
