"""Which of the four positions is showing, and the track that slides between.

Project, pipeline, step, save — VISION's walk and what it ends in, in that
order, as one track four panes wide that moves by one pane-width. Nothing cuts
instantly and nothing grows a tab bar: the slide is what tells the user the four
are a line they are somewhere on rather than four unrelated screens.

**Why save is a fourth position and not a dialog** (07.11). VISION puts it after
the pipeline — the user "checks off the outputs they want persisted, and selects
'process'" — and a modal over the workspace would make the last thing the user
does the one thing that is not on the line they have been walking. It goes past
`step` rather than between `pipeline` and `step` because the middle two are the
node walk: Up and Down mean something at both of them and nothing here, and a
position wedged between them would break the one gesture that ties them
together. So the track reads as a zoom in and then a step out — which node,
this node, and then what the whole run keeps.

The rail is hidden here for the same reason it is hidden at the project
position: it says where the walk is, and the save screen is not on the walk.

Not what any of them contains — `project_select.py`, `chain_stack.py`,
`step_pane.py`, `save_screen.py` own those.
Not the canvas: `app.py` swaps that separately and this module never mentions
it. Not which node is current: that is the window's, passed in on every rebuild
rather than tracked here, so there is exactly one answer to "where is the walk"
and it is not in a widget. Which *position* is showing has no such owner below
— the session layer is Qt-free and has no idea a track exists — so it is this
module's own.

The rail sits outside the track, never inside it: switching panes must not hide
it. At the project position it is hidden but keeps its width, because giving
the width back would resize the track in the same turn as the slide it is part
of.

**Where this departs from the spike it is adopted from**
(`adr/superseded/gui-base-is-the-v25-spike.md`): the spike put its step list at the step
position and left the pipeline position empty, having designed nothing for it.
VISION reads the other way round — "at a pipeline view level ... you can press
up and down to go between them" — so the list of nodes is the pipeline position
and the step position shows the one node the walk is on.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
)
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QWidget

from sieve.core.pipeline_model import Node
from sieve.gui.rail import NodeRail
from sieve.gui.step_pane import StepPane

_SLIDE_DURATION_MS = 260

_POS_PROJECT, _POS_PIPELINE, _POS_STEP, _POS_SAVE = range(4)
POSITION_NAMES = ("project", "pipeline", "step", "save")


class _SlidingPanes(QWidget):
    """Panes side by side in a track N times this widget's width.

    What animates is `offset`, a float in *pane units* — 1.5 is halfway between
    panes 1 and 2 — rather than the track's pixel position. Pixels computed
    against one width are stale the instant the width changes, and showing or
    hiding the rail beside this widget changes it on every transition into or
    out of the workspace, so a pixel animation would have to be stopped and
    jumped to its destination by `resizeEvent`. An offset in pane units stays
    correct across a resize: the slide simply re-lays out at whatever fraction
    it has reached and keeps running.
    """

    def __init__(self, panes: Sequence[QWidget], parent: QWidget | None = None) -> None:
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
        # Out-only easing reads as the track being flicked and coasting to rest;
        # an InOut curve over a distance this short just looks sluggish.
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

    def pane(self, index: int) -> QWidget:
        return self._panes[index]

    def replace_pane(self, index: int, widget: QWidget) -> None:
        old = self._panes[index]
        widget.setParent(self._track)
        self._panes[index] = widget

        # Every pane stays visible, side by side; it is the track's position
        # that decides what is in frame, and this widget's own bounds hide the
        # rest.
        # Hiding a pane here would hide the thing the next slide reveals.
        widget.show()
        self._relayout()

        old.hide()
        old.setParent(None)
        old.deleteLater()

    def set_current(self, index: int) -> None:
        running = self._animation.state() == QAbstractAnimation.State.Running
        if index == self._current and not running:
            return
        self._current = index
        # Restarting from the live offset rather than from the pane it was
        # heading to keeps a fast Left-Right-Left from jumping backwards before
        # it slides.
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(float(index))
        self._animation.start()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        width, height = self.width(), self.height()
        self._track.resize(width * len(self._panes), height)
        for index, pane in enumerate(self._panes):
            pane.setGeometry(index * width, 0, width, height)
        self._set_offset(self._offset)


class Control(QWidget):
    def __init__(self, project_select: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._rail = self._build_rail(node_count=0, current=0)
        self._rail.setVisible(False)

        self._panes = _SlidingPanes([project_select, QWidget(), QWidget(), QWidget()])

        self._layout = QHBoxLayout(self)
        # The rail is a left gutter, so equal margins are not symmetric: the
        # panes would sit a rail-width in from the left edge and flush against
        # the right one. The right margin takes the rail's own width — read off
        # the rail rather than restated here, because how wide the strip is is
        # `rail.py`'s answer.
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, self._rail.maximumWidth(), 0)
        self._layout.addWidget(self._rail)
        self._layout.addWidget(self._panes)

    @property
    def rail(self) -> NodeRail:
        return self._rail

    @property
    def project_select(self) -> QWidget:
        """The project position's content: a `ProjectSelect` over the library."""
        return self._panes.pane(_POS_PROJECT)

    @property
    def pipeline_pane(self) -> QWidget:
        """The pipeline position's content: a `PipelinePane` once a graph is showing."""
        return self._panes.pane(_POS_PIPELINE)

    @property
    def step_pane(self) -> StepPane | QWidget:
        """The step position's content: a `StepPane` once a graph is showing.

        A bare `QWidget` before that, and on an empty graph — a window with no
        project open has a step position, because the track has four panes
        whether or not three of them have anything to say yet.
        """
        return self._panes.pane(_POS_STEP)

    @property
    def save_pane(self) -> QWidget:
        """The save position's content: a `SaveScreen` once a project is open."""
        return self._panes.pane(_POS_SAVE)

    def current_position(self) -> str:
        return POSITION_NAMES[self._panes.current_index()]

    def set_project_select(self, select: QWidget) -> None:
        """Put `select` on the project position. Built by the caller, for `show_graph`'s reason.

        Separate from the slide because the two happen apart: moving the
        selection redraws the pane without going anywhere, and Left arrives at
        a pane that has just been redrawn for the state it is arriving in.
        """
        self._panes.replace_pane(_POS_PROJECT, select)

    def show_project_select(self) -> None:
        self._rail.setVisible(False)
        self._panes.set_current(_POS_PROJECT)

    def show_graph(
        self, nodes: Sequence[Node], current: int, stack: QWidget, step: QWidget
    ) -> None:
        """Redraw both walk positions for `nodes` with `current` selected.

        Called on every move of the walk as well as on open, because a whole
        rebuild is what the skeleton has: there is no incremental path yet and
        inventing one before the panes hold anything expensive would be
        optimizing a rebuild of two labels. It is also what a generated form
        runs on — `param_form.py` reads the document once and never reads it
        back, so a rebuild is how a new value arrives.

        `stack` and `step` are built by the caller and handed in, because what
        goes on either position needs the session and the nodes' specs and this
        module has neither: it owns which position is showing and nothing about
        the graph. `nodes` and `current` stay in the signature for the rail,
        which is this module's own and needs only how many and which one.
        """
        old_rail = self._rail
        self._rail = self._build_rail(len(nodes), current)
        self._layout.replaceWidget(old_rail, self._rail)
        # Whether the rail is showing is a fact about which position is current,
        # so a redraw carries it rather than deciding it: adding a widget to a
        # visible layout otherwise shows it, and a walk moved from the project
        # position would put a rail on a screen that has no graph on it.
        self._rail.setVisible(old_rail.isVisible())
        old_rail.setParent(None)
        old_rail.deleteLater()

        self._panes.replace_pane(_POS_PIPELINE, stack)
        self._panes.replace_pane(_POS_STEP, step)

    def set_save_screen(self, screen: QWidget) -> None:
        """Put `screen` on the save position. Built by the caller, for `show_graph`'s reason."""
        self._panes.replace_pane(_POS_SAVE, screen)

    def show_pipeline(self) -> None:
        self._rail.setVisible(True)
        self._panes.set_current(_POS_PIPELINE)

    def show_step(self) -> None:
        self._rail.setVisible(True)
        self._panes.set_current(_POS_STEP)

    def show_save(self) -> None:
        self._rail.setVisible(False)
        self._panes.set_current(_POS_SAVE)

    def _build_rail(self, node_count: int, current: int) -> NodeRail:
        rail = NodeRail(node_count=node_count, current=current)
        # Hiding the rail must not take its width back: that would resize the
        # track beside it in the same turn as the slide it is part of. The slide
        # survives a resize (see `_SlidingPanes`), but the panes would still jog
        # sideways mid-flight. One tick wide costs nothing to look at.
        policy = rail.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        rail.setSizePolicy(policy)
        return rail
